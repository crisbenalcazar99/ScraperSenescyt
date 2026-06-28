import sys
from scraper_senescyt.Scrapper.navegador_scraper import NavegadorScraper
from scraper_senescyt.Scrapper.scraper_senescyt import ScraperSenescyt


def main():
    print("Python:", sys.executable)

    url = "https://www.senescyt.gob.ec/web/guest/consultas"   # <-- pon tu URL real

    scraper = ScraperSenescyt()
    try:
        # 1. Cargar la página
        scraper.get_page(url)
        scraper.guardar_estado("1")

        # 2. Cerrar el diálogo/popup inicial si aparece
        scraper.cerrar_dialogo()
        scraper.guardar_estado("2")

        captcha = scraper.decodificar_captcha()
        scraper.llenar_formulario('0604370270', captcha)
        scraper.guardar_estado("3")

        # 3. (aquí van los pasos de tu flujo: escribir cédula, buscar, etc.)
        # scraper.buscar(cedula="...")

        # 4. Obtener el HTML / resultados
        contenedor = scraper.esperar_resultados_consulta()
        returns = scraper.obtener_persona_con_titulos(contenedor)
        scraper.guardar_estado(4)
        print(returns)


    finally:
        # Cerrar siempre el navegador, pase lo que pase
        scraper.driver.quit()


if __name__ == "__main__":
    main()