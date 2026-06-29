from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext, ElementHandle, Playwright


class NavegadorScraper:
    def __init__(self):
        self._playwright: Playwright = sync_playwright().start()
        self.browser: Browser = self._playwright.chromium.launch(
            headless=True,
            args=[
                '--disable-gpu',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-extensions',
            ],
        )
        self.context: BrowserContext = self._new_context()
        self.page: Page = self.context.new_page()
        self._apply_timeouts()

    def _new_context(self) -> BrowserContext:
        return self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            ignore_https_errors=True,
        )

    def _apply_timeouts(self):
        self.page.set_default_timeout(15_000)
        self.page.set_default_navigation_timeout(30_000)

    def get_page(self, url: str):
        self.page.goto(url, wait_until='domcontentloaded')

    def refresh_page(self):
        try:
            self.page.close()
            self.context.close()
        except Exception:
            pass
        self.context = self._new_context()
        self.page = self.context.new_page()
        self._apply_timeouts()
        print('✅ Navegador reiniciado')

    def close(self):
        try:
            self.browser.close()
        except Exception:
            pass
        try:
            self._playwright.stop()
        except Exception:
            pass

    def _leer_celdas(self, fila: ElementHandle) -> list[ElementHandle]:
        return fila.query_selector_all('td')

    def _leer_texto(self, elemento: ElementHandle, selector: str) -> str:
        return elemento.query_selector(selector).text_content().strip()

    def _leer_filas(self, seccion: ElementHandle, selector: str) -> list[ElementHandle]:
        return seccion.query_selector_all(selector)

    def _textos_de_celdas(self, fila: ElementHandle) -> list[str]:
        return [c.text_content().strip() for c in self._leer_celdas(fila)]