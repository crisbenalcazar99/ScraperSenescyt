"""
Coordinador de workers directos (sin Redis).

Carga todas las cédulas desde la DB origen, las divide en N chunks
y lanza un proceso por chunk. Los logs quedan en logs/worker_N.log.

Variables de entorno:
  N_WORKERS       — número de workers (default: 5)
  LIMIT_CEDULAS   — recorta la consulta a N cédulas (útil para pruebas)
"""
import multiprocessing
import os
import signal
import sys
from math import ceil

from sqlalchemy import text

from scraper_senescyt.config.settings import BASE_ORIGEN
from scraper_senescyt.queue.worker_directo import run
from zaly_toolkits.common.db import get_session_maker


def _cargar_cedulas(limit: int | None = None) -> list[str]:
    session = get_session_maker(BASE_ORIGEN)()
    try:
        sql = "SELECT cedula FROM users ORDER BY id_user"
        if limit:
            sql += f" LIMIT {limit}"
        rows = session.execute(text(sql)).fetchall()
        return [r[0] for r in rows]
    finally:
        session.close()


def _chunk(lst: list, n: int) -> list[list]:
    size = ceil(len(lst) / n)
    return [lst[i:i + size] for i in range(0, len(lst), size)]


def _worker_proceso(worker_num: int, cedulas: list[str]):
    print(f"[Worker-{worker_num}] PID={os.getpid()} — {len(cedulas)} cédulas asignadas")
    run(worker_num, cedulas)


def main():
    n     = int(os.environ.get('N_WORKERS', 5))
    limit = os.environ.get('LIMIT_CEDULAS')
    limit = int(limit) if limit else None

    print("Cargando cédulas desde DB origen...")
    cedulas = _cargar_cedulas(limit)
    print(f"Total: {len(cedulas)} cédulas — {n} workers")

    if not cedulas:
        print("No hay cédulas para procesar.")
        return

    chunks   = _chunk(cedulas, n)
    procesos = [
        multiprocessing.Process(
            target=_worker_proceso,
            args=(i + 1, chunks[i]),
            name=f"worker-{i + 1}",
        )
        for i in range(len(chunks))
    ]

    def _apagar(sig, frame):
        print("\nApagando workers...")
        for p in procesos:
            p.terminate()
        sys.exit(0)

    signal.signal(signal.SIGINT, _apagar)
    signal.signal(signal.SIGTERM, _apagar)

    for p in procesos:
        p.start()
    for p in procesos:
        p.join()

    print("Todos los workers finalizaron.")


if __name__ == '__main__':
    multiprocessing.set_start_method('spawn')
    main()