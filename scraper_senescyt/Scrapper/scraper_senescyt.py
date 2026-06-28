import os
from selenium.webdriver.support import expected_conditions as EC

from scraper_senescyt.Scrapper.navegador_scraper import NavegadorScraper
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time
from selenium.common.exceptions import WebDriverException

from scraper_senescyt.utils.general_functions import decodificar_captcha


class ScraperSenescyt(NavegadorScraper):
    def __init__(self):
        super().__init__()

    def cerrar_dialogo(self):
        botones = self.driver.find_elements(
            By.XPATH, '//a[contains(@class,"ui-dialog-titlebar-close")]'
        )
        for boton in botones:
            if boton.is_displayed():
                self.driver.execute_script("arguments[0].click();", boton)
                return True
        return False

    def obtener_persona_con_titulos(self, contenedor):
        return {
            'persona': self._extraer_persona(contenedor),
            'titulos': self._extraer_todos_los_titulos(contenedor),
        }

    def _extraer_persona(self, contenedor):
        panel = contenedor.find_element(By.CSS_SELECTOR, "div[id$='pnlInfoPersonal']")
        info = {}
        for fila in self._leer_filas(panel, By.TAG_NAME, 'tr'):
            celdas = self._leer_celdas(fila)
            if len(celdas) != 2:
                continue
            clave = celdas[0].text.strip().replace(':', '')
            info[clave] = celdas[1].text.strip()
        return info

    def _extraer_todos_los_titulos(self, contenedor):
        titulos = []
        for panel in contenedor.find_elements(By.CSS_SELECTOR, "div[id$='pnlListaTitulos']"):
            nivel = self._leer_texto(panel, By.CLASS_NAME, 'panel-title')
            titulos.extend(self._extraer_tabla(panel, nivel))
        return titulos

    def _extraer_tabla(self, panel, tipo_titulo):
        tabla = panel.find_element(By.CSS_SELECTOR, "table[role='grid']")
        encabezados = [th.text.strip() for th in tabla.find_elements(By.CSS_SELECTOR, 'thead th')]

        registros = []
        for fila in tabla.find_elements(By.CSS_SELECTOR, 'tbody tr'):
            valores = [self._texto_celda(td) for td in self._leer_celdas(fila)]
            if not any(valores):
                continue
            registro = dict(zip(encabezados, valores))
            registro['tipo_titulo'] = tipo_titulo
            registros.append(registro)
        return registros

    def _texto_celda(self, celda):
        etiqueta = ''
        spans = celda.find_elements(By.CSS_SELECTOR, 'span.ui-column-title')
        if spans:
            etiqueta = spans[0].text.strip()
        texto = celda.text.strip()
        if etiqueta and texto.startswith(etiqueta):
            texto = texto[len(etiqueta):].strip()
        return texto

    def llenar_formulario(self, cedula, captcha):
        self._escribir_cedula(cedula)
        self._escribir_captcha(captcha)

    def _escribir_cedula(self, cedula):
        campo = self.wait.until(
            EC.presence_of_element_located(
                (By.XPATH, '//*[@id="formPrincipal:identificacion"]')
            )
        )
        campo.clear()
        campo.send_keys(cedula)

    def _escribir_captcha(self, captcha):
        campo = self.driver.find_element(
            By.XPATH, '//*[@id="formPrincipal:captchaSellerInput"]'
        )
        campo.clear()
        campo.send_keys(captcha)
        print(f'📨 Enviando captcha: {captcha}')
        campo.send_keys(Keys.ENTER)
        time.sleep(2)

    def esperar_resultados_consulta(self, url=None):
        if url:
            self.driver.get(url)
        return self.wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "span[id$='groupDatos']")
            )
        )

    def decodificar_captcha(self):
        img_captcha = self.wait.until(
            EC.presence_of_element_located(
                (By.XPATH, '//*[@id="formPrincipal:capimg"]')
            )
        )

        path_img = 'captcha.png'
        with open(path_img, 'wb') as file:
            file.write(img_captcha.screenshot_as_png)
        st_decoded = decodificar_captcha(path_img)
        os.remove(path_img)
        return st_decoded

    def guardar_estado(self, nombre="debug"):
        self.driver.save_screenshot(f'/tmp/{nombre}.png')
        html = self.driver.page_source
        with open(f'/tmp/{nombre}.html', 'w', encoding='utf-8') as f:
            f.write(self.driver.page_source)
        print(f'📸 Estado guardado: /tmp/{nombre}.png y .html')