import csv
import time
from pathlib import Path

from scraper_senescyt.Scrapper.scraper_senescyt import ScraperSenescyt


def tick(label: str, t0: float) -> float:
    elapsed = time.perf_counter() - t0
    print(f"[{elapsed:6.2f}s] {label}")
    return time.perf_counter()


def leer_cedulas(path: str) -> list[str]:
    with open(path, newline='', encoding='utf-8') as f:
        return [row[0].strip() for row in csv.reader(f) if row and row[0].strip()]


def main():
    url = "https://www.senescyt.gob.ec/web/guest/consultas"
    cedulas = leer_cedulas(Path(__file__).parent / "cedula.csv")
    total_start = time.perf_counter()

    scraper = ScraperSenescyt()
    try:
        scraper.get_page(url)
        scraper.cerrar_dialogo()

        for i, cedula in enumerate(cedulas, 1):
            print(f"\n--- [{i}/{len(cedulas)}] Consultando: {cedula} ---")
            t = time.perf_counter()
            try:
                resultado = scraper.consultar_cedula(cedula)
                tick("consultar_cedula", t)
                print(resultado)
            except RuntimeError as e:
                print(f"❌ {e}")

    finally:
        scraper.close()

    print(f"\nTotal: {time.perf_counter() - total_start:.2f}s")


if __name__ == "__main__":
    main()