"""
Prueba de fuerza bruta con 5 workers en paralelo sobre la misma cédula.
Detecta falsos negativos bajo carga concurrente.
"""
import multiprocessing
import os

from scraper_senescyt.Scrapper.scraper_senescyt import ScraperSenescyt

CEDULA      = "0904358256"
URL         = "https://www.senescyt.gob.ec/web/guest/consultas"
ITERACIONES = 30   # por worker → 100 consultas totales
N_WORKERS   = 5


def _worker(worker_num: int, resultado_queue: multiprocessing.Queue):
    wid = f"W{worker_num}|PID{os.getpid()}"
    con_titulo = sin_titulo = errores = 0

    scraper = ScraperSenescyt()
    scraper.get_page(URL)
    scraper.cerrar_dialogo()

    for i in range(1, ITERACIONES + 1):
        try:
            resultado = scraper.consultar_cedula(CEDULA, max_intentos=1)
            tiene = bool(resultado.get("persona"))
            if tiene:
                con_titulo += 1
                print(f"[{wid}] [{i:>2}/{ITERACIONES}] ✅ CON TÍTULO")
            else:
                sin_titulo += 1
                scraper.guardar_estado(f"falso_negativo_{CEDULA}_{wid}_{i}")
                print(f"[{wid}] [{i:>2}/{ITERACIONES}] ❌ SIN TÍTULO — html guardado")
        except Exception as e:
            errores += 1
            print(f"[{wid}] [{i:>2}/{ITERACIONES}] ⚠️  ERROR: {e}")

    scraper.close()
    resultado_queue.put((worker_num, con_titulo, sin_titulo, errores))


def main():
    queue    = multiprocessing.Queue()
    procesos = [
        multiprocessing.Process(target=_worker, args=(n, queue), name=f"W{n}")
        for n in range(1, N_WORKERS + 1)
    ]

    for p in procesos:
        p.start()
    for p in procesos:
        p.join()

    totales = {"con_titulo": 0, "sin_titulo": 0, "errores": 0}
    print("\n── Resultado por worker ─────────────────")
    while not queue.empty():
        wnum, con, sin, err = queue.get()
        print(f"  Worker {wnum}: ✅ {con}  ❌ {sin}  ⚠️  {err}")
        totales["con_titulo"] += con
        totales["sin_titulo"] += sin
        totales["errores"]    += err

    print("\n── Resumen total ────────────────────────")
    print(f"  Con título     : {totales['con_titulo']}")
    print(f"  Sin título     : {totales['sin_titulo']}  ← falsos negativos")
    print(f"  Errores        : {totales['errores']}")
    print(f"  Total intentos : {N_WORKERS * ITERACIONES}")


if __name__ == "__main__":
    multiprocessing.set_start_method("spawn")
    main()