import multiprocessing
import os
import signal
import sys

from scraper_senescyt.queue.worker import run


def _worker_proceso(worker_num: int):
    print(f"[Worker-{worker_num}] PID={os.getpid()} iniciado")
    run(worker_num)


def main():
    n = int(os.environ.get('N_WORKERS', 5))
    print(f"Lanzando {n} workers...")

    procesos = [
        multiprocessing.Process(target=_worker_proceso, args=(i,), name=f"worker-{i}")
        for i in range(1, n + 1)
    ]

    def _apagar(sig, frame):
        print("\nSeñal de apagado recibida. Terminando workers...")
        for p in procesos:
            p.terminate()
        sys.exit(0)

    signal.signal(signal.SIGINT, _apagar)
    signal.signal(signal.SIGTERM, _apagar)

    for p in procesos:
        p.start()

    # Monitoreo: si un worker muere, lo reinicia
    while True:
        for i, p in enumerate(procesos):
            if not p.is_alive():
                print(f"[Monitor] Worker-{p.name} muerto (exit={p.exitcode}). Reiniciando...")
                nuevo = multiprocessing.Process(
                    target=_worker_proceso,
                    args=(i + 1,),
                    name=p.name
                )
                nuevo.start()
                procesos[i] = nuevo
        import time; time.sleep(10)


if __name__ == '__main__':
    multiprocessing.set_start_method('spawn')
    main()
