import os
import random
import socket
import time
from datetime import datetime

from sqlalchemy.dialects.postgresql import insert

from scraper_senescyt.Scrapper.scraper_senescyt import ScraperSenescyt
from scraper_senescyt.entities.senescyt_consulta import SenescytConsulta
from scraper_senescyt.config.settings import BASE_DESTINO
from zaly_toolkits.common.db import get_session_maker

URL_SENESCYT = 'https://www.senescyt.gob.ec/web/guest/consultas'


def _log(path: str, mensaje: str):
    linea = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {mensaje}\n"
    with open(path, 'a', encoding='utf-8') as f:
        f.write(linea)
    print(linea, end='')


def _insertar(session, cedula: str, resultado: dict, sin_resultados: bool):
    persona = resultado.get('persona', {})
    stmt = insert(SenescytConsulta).values([{
        'cedula':          cedula,
        'nombres':         persona.get('Nombres') or persona.get('Nombres Completos'),
        'genero':          persona.get('Género'),
        'nacionalidad':    persona.get('Nacionalidad'),
        'sin_resultados':  sin_resultados,
        'certificaciones': resultado.get('certificaciones', []),
    }])
    stmt = stmt.on_conflict_do_update(
        index_elements=['cedula'],
        set_={
            'nombres':             stmt.excluded.nombres,
            'genero':              stmt.excluded.genero,
            'nacionalidad':        stmt.excluded.nacionalidad,
            'sin_resultados':      stmt.excluded.sin_resultados,
            'certificaciones':     stmt.excluded.certificaciones,
            'fecha_actualizacion': stmt.excluded.fecha_actualizacion,
        }
    )
    session.execute(stmt)
    session.commit()


def run(worker_num: int, cedulas: list[str]):
    wid      = f"Worker-{worker_num}|{socket.gethostname()}:{os.getpid()}"
    log_dir  = os.path.join(os.path.dirname(__file__), '..', '..', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, f'worker_{worker_num}.log')

    session  = get_session_maker(BASE_DESTINO)()
    scraper  = ScraperSenescyt()
    total    = len(cedulas)
    exitosas = errores = 0

    _log(log_path, f"[{wid}] Iniciando — {total} cédulas asignadas")

    try:
        scraper.get_page(URL_SENESCYT)
        scraper.cerrar_dialogo()

        for i, cedula in enumerate(cedulas, 1):
            try:
                resultado    = scraper.consultar_cedula(cedula)
                sin_res      = not bool(resultado.get('persona'))
                _insertar(session, cedula, resultado, sin_res)

                detalle = "SIN REGISTROS" if sin_res else f"{len(resultado.get('certificaciones', []))} certif."
                _log(log_path, f"[{wid}] [{i}/{total}] ✅ {cedula} — {detalle}")
                exitosas += 1

            except Exception as e:
                _log(log_path, f"[{wid}] [{i}/{total}] ❌ {cedula} — {e}")
                errores += 1
                scraper.page.reload(wait_until='domcontentloaded')
                scraper.cerrar_dialogo()
                time.sleep(random.uniform(2, 5))

    finally:
        scraper.close()
        session.close()
        _log(log_path, f"[{wid}] Finalizado — ✅ {exitosas}  ❌ {errores}  total {total}")