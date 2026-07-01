"""
Carga masiva de cédulas desde archivos TXT hacia la tabla senescyt_schema.cedulas.

Uso:
    python cargar_cedulas.py

Los archivos deben estar en CEDULAS_DIR (ver constante abajo).
Inserta en lotes de BATCH_SIZE para eficiencia. Ignora duplicados.
"""
import glob
import os
import re

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert

import scraper_senescyt.entities.cedula_source  # noqa: F401 — registra el modelo en Base.metadata
from scraper_senescyt.entities.models.base import Base
from scraper_senescyt.entities.cedula_source import CedulaSource
from scraper_senescyt.config.settings import BASE_DESTINO
from zaly_toolkits.common.db import get_engine, get_session_maker

CEDULAS_DIR = "/Users/cbenalcazar/Downloads/carpeta sin titulo/SENES/cedulas"
BATCH_SIZE  = 5_000


def _crear_tabla():
    engine = get_engine(BASE_DESTINO)
    with engine.connect() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS senescyt_schema"))
        conn.commit()
    Base.metadata.create_all(engine, tables=[CedulaSource.__table__])
    print("Tabla senescyt_schema.cedulas lista.")


def _archivos_ordenados() -> list[str]:
    patron  = os.path.join(CEDULAS_DIR, "cedulas_ecu_*.txt")
    archivos = glob.glob(patron)
    # orden numérico: cedulas_ecu_1, cedulas_ecu_2, ..., cedulas_ecu_67
    archivos.sort(key=lambda p: int(re.search(r'_(\d+)\.txt$', p).group(1)))
    return archivos


def _cargar_archivo(session, archivo: str, num: int, total: int) -> tuple[int, int]:
    with open(archivo, encoding='utf-8') as f:
        cedulas = [linea.strip() for linea in f if linea.strip()]

    insertadas = omitidas = 0
    for i in range(0, len(cedulas), BATCH_SIZE):
        lote = [{'cedula': str(c)} for c in cedulas[i:i + BATCH_SIZE]]
        stmt = insert(CedulaSource).values(lote).on_conflict_do_nothing(index_elements=['cedula'])
        result = session.execute(stmt)
        session.commit()
        insertadas += result.rowcount
        omitidas   += len(lote) - result.rowcount

    nombre = os.path.basename(archivo)
    print(f"  [{num:>2}/{total}] {nombre} — {len(cedulas)} leídas | ✅ {insertadas} nuevas | ⏭ {omitidas} duplicadas")
    return insertadas, omitidas


def main():
    _crear_tabla()

    archivos      = _archivos_ordenados()
    session       = get_session_maker(BASE_DESTINO)()
    total_ins     = total_dup = total_cedulas = 0

    print(f"\nProcesando {len(archivos)} archivos...\n")

    try:
        for i, archivo in enumerate(archivos, 1):
            ins, dup = _cargar_archivo(session, archivo, i, len(archivos))
            total_ins     += ins
            total_dup     += dup
            total_cedulas += ins + dup
    finally:
        session.close()

    print(f"\n── Resumen ──────────────────────────────")
    print(f"  Archivos procesados : {len(archivos)}")
    print(f"  Cédulas leídas      : {total_cedulas:,}")
    print(f"  Insertadas (nuevas) : {total_ins:,}")
    print(f"  Duplicadas (skip)   : {total_dup:,}")


if __name__ == '__main__':
    main()