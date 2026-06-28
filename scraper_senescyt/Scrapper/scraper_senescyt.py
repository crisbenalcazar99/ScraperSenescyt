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

    # ── Extracción general ──────────────────────────────────────────────────

    def obtener_resultado(self) -> dict:
        return {
            'persona': self._extraer_persona(),
            'certificaciones': self._extraer_todas_las_tablas(),
        }

    def _extraer_persona(self) -> dict:
        panel = self.page.query_selector("div[id$='pnlInfoPersonal']")
        if not panel:
            # Fallback: info personal dentro del panel SETEC
            panel = self.page.query_selector("[id$='pnlSetec'] table.ui-panelgrid")
        if not panel:
            return {}
        info = {}
        for fila in self._leer_filas(panel, 'tr'):
            celdas = self._leer_celdas(fila)
            if len(celdas) != 2:
                continue
            clave = celdas[0].text_content().strip().replace(':', '')
            info[clave] = celdas[1].text_content().strip()
        return info

    def _extraer_todas_las_tablas(self) -> list[dict]:
        registros = []
        for tabla in self.page.query_selector_all("table[role='grid']"):
            panel_id = tabla.evaluate(
                "el => el.closest('[id]')?.id ?? ''"
            )
            panel_titulo = tabla.evaluate(
                """el => {
                    const panel = el.closest('.panel');
                    return panel?.querySelector('.panel-title')?.textContent?.trim() ?? '';
                }"""
            )
            encabezados = [
                th.text_content().strip()
                for th in tabla.query_selector_all('thead th')
            ]
            if not encabezados:
                continue
            for fila in tabla.query_selector_all('tbody tr'):
                valores = [self._texto_celda(td) for td in self._leer_celdas(fila)]
                if not any(valores):
                    continue
                registro = dict(zip(encabezados, valores))
                registro['fuente_panel_id'] = panel_id
                registro['fuente_panel_titulo'] = panel_titulo
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

    # ── Flujo de consulta ───────────────────────────────────────────────────

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

    def esperar_resultados_consulta(self, cedula: str) -> bool:
        """Espera hasta que la página resuelva la consulta.
        Retorna True si hay resultados, False si la persona no tiene registros."""
        self.page.wait_for_function(
            """(cedula) => {
                if (document.querySelector('.msg-rojo')) return true;
                const titulos = document.querySelector("span[id$='groupDatos']");
                if (titulos && titulos.textContent.includes(cedula)) return true;
                const setec = document.querySelector("[id$='pnlSetec']");
                if (setec && setec.textContent.includes(cedula)) return true;
                return false;
            }""",
            arg=cedula,
        )
        return self.page.query_selector('.msg-rojo') is None

    def consultar_cedula(self, cedula: str, max_intentos: int = 5) -> dict:
        for intento in range(1, max_intentos + 1):
            try:
                captcha = self.decodificar_captcha()
                self.llenar_formulario(cedula, captcha)
                tiene_resultados = self.esperar_resultados_consulta(cedula)
                if not tiene_resultados:
                    print(f'ℹ️  {cedula}: sin registros en SENESCYT')
                    return {'persona': {}, 'certificaciones': []}
                return self.obtener_resultado()
            except Exception as e:
                self.guardar_estado(f"{cedula}_{intento}")
                print(f'⚠️  Intento {intento}/{max_intentos} fallido: {e}')
                self.page.reload(wait_until='domcontentloaded')
                self.cerrar_dialogo()
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