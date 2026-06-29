import time
from datetime import datetime, timedelta

from sqlalchemy import text

from scraper_senescyt.queue.redis_client import BUFFER_SIZE
from scraper_senescyt.utils.redis_keys import RedisKey, CedulaEstado
from zaly_toolkits.common.db import get_session_maker
from zaly_toolkits.common.redis_db import get_redis
from scraper_senescyt.config.settings import BASE_ORIGEN

QUEUE_MIN        = 50   # recarga cuando la cola baja de este umbral
BATCH_SIZE       = 200  # cédulas que carga por ciclo
LOOP_INTERVAL    = 30      # segundos entre ciclos
STALE_THRESHOLD  = 300     # segundos para considerar un worker caído (5 min)


def _cargar_cedulas(r, session, cursor: int) -> int:
    """Carga el siguiente batch desde la DB transaccional y retorna el nuevo cursor."""
    rows = session.execute(text("""
        SELECT id_user, cedula
        FROM users
        WHERE id_user > :cursor
        ORDER BY id_user
        LIMIT :limit
    """), {'cursor': cursor, 'limit': BATCH_SIZE}).fetchall()

    if not rows:
        return cursor

    pipe = r.pipeline()
    cargadas = 0
    for id_user, cedula in rows:
        if not r.hexists(RedisKey.HASH_ESTADO, cedula):
            pipe.rpush(RedisKey.QUEUE_PENDIENTES, cedula)
            pipe.hset(RedisKey.HASH_ESTADO, cedula, CedulaEstado.PENDIENTE)
            cargadas += 1

    nuevo_cursor = rows[-1][0]
    pipe.set(RedisKey.REFILLER_CURSOR, nuevo_cursor)
    pipe.execute()

    print(f"[Refiller] Cargadas {cargadas} cédulas nuevas | cursor: {cursor} → {nuevo_cursor}")
    return nuevo_cursor


def _reencolar_errores(r):
    """Re-encola cédulas que fallaron todos sus intentos."""
    estados = r.hgetall(RedisKey.HASH_ESTADO)
    errores = [c for c, e in estados.items() if e == CedulaEstado.ERROR]

    if not errores:
        return

    pipe = r.pipeline()
    for cedula in errores:
        pipe.rpush(RedisKey.QUEUE_PENDIENTES, cedula)
        pipe.hset(RedisKey.HASH_ESTADO, cedula, CedulaEstado.PENDIENTE)
    pipe.execute()
    print(f"[Refiller] Re-encoladas {len(errores)} cédulas en error")


def _recuperar_stale(r):
    """Devuelve a 'pendiente' cédulas que llevan demasiado tiempo en 'consultando'."""
    estados = r.hgetall(RedisKey.HASH_ESTADO)
    stale = [c for c, e in estados.items() if e == CedulaEstado.CONSULTANDO]

    if not stale:
        return

    pipe = r.pipeline()
    for cedula in stale:
        pipe.rpush(RedisKey.QUEUE_PENDIENTES, cedula)
        pipe.hset(RedisKey.HASH_ESTADO, cedula, CedulaEstado.PENDIENTE)
    pipe.execute()
    print(f"[Refiller] Recuperadas {len(stale)} cédulas stale (worker caído)")


def _limpiar_subidas(r):
    """Elimina del hash de estado las cédulas ya confirmadas en PostgreSQL."""
    estados = r.hgetall(RedisKey.HASH_ESTADO)
    subidas = [c for c, e in estados.items() if e == CedulaEstado.SUBIDA]

    if not subidas:
        return

    pipe = r.pipeline()
    for cedula in subidas:
        pipe.hdel(RedisKey.HASH_ESTADO, cedula)
    pipe.execute()
    print(f"[Refiller] Eliminadas {len(subidas)} cédulas subidas del estado Redis")


def run():
    r       = get_redis()
    session = get_session_maker(BASE_ORIGEN)()
    cursor  = int(r.get(RedisKey.REFILLER_CURSOR) or 0)

    print(f"[Refiller] Iniciando desde cursor={cursor}")

    while True:
        queue_len = r.llen(RedisKey.QUEUE_PENDIENTES)
        print(f"[Refiller] Cola actual: {queue_len} | cursor: {cursor}")

        if queue_len < QUEUE_MIN:
            cursor = _cargar_cedulas(r, session, cursor)

        _recuperar_stale(r)
        _reencolar_errores(r)
        _limpiar_subidas(r)

        time.sleep(LOOP_INTERVAL)