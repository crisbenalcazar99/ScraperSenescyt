import os

from playwright.sync_api import ElementHandle

from scraper_senescyt.Scrapper.navegador_scraper import NavegadorScraper
from scraper_senescyt.utils.general_functions import decodificar_captcha


class ScraperSenescyt(NavegadorScraper):
    def __init__(self):
        super().__init__()

    def cerrar_dialogo(self, timeout: int = 5_000) -> bool:
        try:
            boton = self.page.wait_for_selector(
                'xpath=//a[contains(@class,"ui-dialog-titlebar-close")]',
                state='visible',
                timeout=timeout,
            )
            boton.click()
            return True
        except Exception:
            return False

    def obtener_persona_con_titulos(self, contenedor: ElementHandle) -> dict:
        return {
            'persona': self._extraer_persona(contenedor),
            'titulos': self._extraer_todos_los_titulos(contenedor),
        }

    def _extraer_persona(self, contenedor: ElementHandle) -> dict:
        panel = contenedor.query_selector("div[id$='pnlInfoPersonal']")
        info = {}
        for fila in self._leer_filas(panel, 'tr'):
            celdas = self._leer_celdas(fila)
            if len(celdas) != 2:
                continue
            clave = celdas[0].text_content().strip().replace(':', '')
            info[clave] = celdas[1].text_content().strip()
        return info

    def _extraer_todos_los_titulos(self, contenedor: ElementHandle) -> list:
        titulos = []
        for panel in contenedor.query_selector_all("div[id$='pnlListaTitulos']"):
            nivel = self._leer_texto(panel, '.panel-title')
            titulos.extend(self._extraer_tabla(panel, nivel))
        return titulos

    def _extraer_tabla(self, panel: ElementHandle, tipo_titulo: str) -> list:
        tabla = panel.query_selector("table[role='grid']")
        encabezados = [th.text_content().strip() for th in tabla.query_selector_all('thead th')]

        registros = []
        for fila in tabla.query_selector_all('tbody tr'):
            valores = [self._texto_celda(td) for td in self._leer_celdas(fila)]
            if not any(valores):
                continue
            registro = dict(zip(encabezados, valores))
            registro['tipo_titulo'] = tipo_titulo
            registros.append(registro)
        return registros

    def _texto_celda(self, celda: ElementHandle) -> str:
        etiqueta = ''
        spans = celda.query_selector_all('span.ui-column-title')
        if spans:
            etiqueta = spans[0].text_content().strip()
        texto = celda.text_content().strip()
        if etiqueta and texto.startswith(etiqueta):
            texto = texto[len(etiqueta):].strip()
        return texto

    def llenar_formulario(self, cedula: str, captcha: str):
        self._escribir_cedula(cedula)
        self._escribir_captcha(captcha)

    def _escribir_cedula(self, cedula: str):
        campo = self.page.wait_for_selector('//*[@id="formPrincipal:identificacion"]')
        campo.fill('')
        campo.fill(cedula)

    def _escribir_captcha(self, captcha: str):
        campo = self.page.query_selector('//*[@id="formPrincipal:captchaSellerInput"]')
        campo.fill('')
        campo.fill(captcha)
        print(f'📨 Enviando captcha: {captcha}')
        campo.press('Enter')

    def esperar_resultados_consulta(self, cedula: str) -> ElementHandle:
        self.page.wait_for_function(
            """(cedula) => {
                const el = document.querySelector("span[id$='groupDatos']");
                return el && el.textContent.includes(cedula);
            }""",
            arg=cedula,
        )
        return self.page.query_selector("span[id$='groupDatos']")

    def consultar_cedula(self, cedula: str, max_intentos: int = 5) -> dict:
        for intento in range(1, max_intentos + 1):

            try:
                captcha = self.decodificar_captcha()
                self.llenar_formulario(cedula, captcha)
                contenedor = self.esperar_resultados_consulta(cedula)
                return self.obtener_persona_con_titulos(contenedor)
            except Exception as e:
                self.guardar_estado(f"{cedula}_{intento}")
                print(f'⚠️  Intento {intento}/{max_intentos} fallido (captcha incorrecto o timeout)')
                self.page.reload(wait_until='domcontentloaded')
                self.cerrar_dialogo()
                print(e)
        raise RuntimeError(f'No se pudo consultar la cédula {cedula} tras {max_intentos} intentos')

    def decodificar_captcha(self) -> str:
        img_captcha = self.page.wait_for_selector('//*[@id="formPrincipal:capimg"]')
        path_img = 'captcha.png'
        bbox = img_captcha.bounding_box()
        with open(path_img, 'wb') as f:
            f.write(self.page.screenshot(clip=bbox))
        st_decoded = decodificar_captcha(path_img)
        os.remove(path_img)
        return st_decoded

    def guardar_estado(self, nombre: str = "debug"):
        self.page.screenshot(path=f'/tmp/{nombre}.png')
        with open(f'/tmp/{nombre}.html', 'w', encoding='utf-8') as f:
            f.write(self.page.content())
        print(f'📸 Estado guardado: /tmp/{nombre}.png y .html')