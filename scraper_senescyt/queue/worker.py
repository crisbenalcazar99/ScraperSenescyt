import json
import os
import random
import socket
import time

from sqlalchemy.dialects.postgresql import insert

from scraper_senescyt.Scrapper.scraper_senescyt import ScraperSenescyt
from scraper_senescyt.entities.senescyt_consulta import SenescytConsulta
from scraper_senescyt.queue.redis_client import BUFFER_SIZE, LUA_FLUSH_BUFFER
from scraper_senescyt.utils.redis_keys import RedisKey, CedulaEstado
from zaly_toolkits.common.db import get_session_maker
from zaly_toolkits.common.redis_db import get_redis
from scraper_senescyt.config.settings import BASE_DESTINO

URL_SENESCYT = 'https://www.senescyt.gob.ec/web/guest/consultas'


def _worker_id() -> str:
    return f"{socket.gethostname()}:{os.getpid()}"


def _flush_a_postgres(session, items_json: list[str]):
    """Escribe un batch de registros a PostgreSQL con upsert."""
    # dict por cédula para eliminar duplicados dentro del mismo batch
    records_map = {}
    for raw in items_json:
        entry = json.loads(raw)
        persona = entry.get('resultado', {}).get('persona', {})
        records_map[entry['cedula']] = {
            'cedula':          entry['cedula'],
            'nombres':         persona.get('Nombres') or persona.get('Nombres Completos'),
            'genero':          persona.get('Género'),
            'nacionalidad':    persona.get('Nacionalidad'),
            'sin_resultados':  entry.get('sin_resultados', False),
            'certificaciones': entry.get('resultado', {}).get('certificaciones', []),
        }
    records = list(records_map.values())

    stmt = insert(SenescytConsulta).values(records)
    stmt = stmt.on_conflict_do_update(
        index_elements=['cedula'],
        set_={
            'nombres':              stmt.excluded.nombres,
            'genero':               stmt.excluded.genero,
            'nacionalidad':         stmt.excluded.nacionalidad,
            'sin_resultados':       stmt.excluded.sin_resultados,
            'certificaciones':      stmt.excluded.certificaciones,
            'fecha_actualizacion':  stmt.excluded.fecha_actualizacion,
        }
    )
    session.execute(stmt)
    session.commit()


def run(worker_num: int = 0):
    wid     = f"{worker_num}|{_worker_id()}"
    r       = get_redis()
    session = get_session_maker(BASE_DESTINO)()
    flush   = r.register_script(LUA_FLUSH_BUFFER)
    scraper = ScraperSenescyt()

    print(f"[Worker {wid}] Iniciando...")

    try:
        scraper.get_page(URL_SENESCYT)
        scraper.cerrar_dialogo()

        while True:
            # ── Tomar cédula de la cola (bloquea hasta 30s) ─────────────────
            item = r.blpop(RedisKey.QUEUE_PENDIENTES, timeout=30)
            if item is None:
                print(f"[Worker {wid}] Cola vacía, esperando...")
                continue

            _, cedula = item
            r.hset(RedisKey.HASH_ESTADO, cedula, CedulaEstado.CONSULTANDO)

            try:
                resultado = scraper.consultar_cedula(cedula)
                r.hset(RedisKey.HASH_ESTADO, cedula, CedulaEstado.CONSULTADA)

                entry = json.dumps({
                    'cedula':          cedula,
                    'sin_resultados':  not resultado.get('persona'),
                    'resultado':       resultado,
                })
                r.rpush(RedisKey.BUFFER_RESULTADOS, entry)

            except Exception as e:
                print(f"[Worker {wid}] Error en {cedula}: {e}")
                r.hset(RedisKey.HASH_ESTADO, cedula, CedulaEstado.ERROR)
                # Backoff antes del siguiente intento
                time.sleep(random.uniform(2, 5))
                scraper.page.reload(wait_until='domcontentloaded')
                scraper.cerrar_dialogo()
                continue

            # ── Intentar flush del buffer (Lua atómico) ─────────────────────
            items = flush(keys=[RedisKey.BUFFER_RESULTADOS], args=[BUFFER_SIZE])
            if items:
                try:
                    cedulas_batch = [json.loads(i)['cedula'] for i in items]
                    _flush_a_postgres(session, items)
                    pipe = r.pipeline()
                    for c in cedulas_batch:
                        pipe.hset(RedisKey.HASH_ESTADO, c, CedulaEstado.SUBIDA)
                    pipe.execute()
                    print(f"[Worker {wid}] Batch de {len(items)} registros guardado en PostgreSQL")
                except Exception as e:
                    print(f"[Worker {wid}] Error escribiendo a PostgreSQL: {e}")
                    session.rollback()
                    # Devuelve los items al buffer para no perderlos
                    pipe = r.pipeline()
                    for i in reversed(items):
                        pipe.lpush(RedisKey.BUFFER_RESULTADOS, i)
                    pipe.execute()

            # Delay entre consultas para no saturar el servidor
            time.sleep(random.uniform(0.5, 1.5))

    finally:
        scraper.close()
        session.close()