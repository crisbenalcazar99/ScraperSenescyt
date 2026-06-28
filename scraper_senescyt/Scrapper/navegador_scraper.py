from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import os

from webdriver_manager.chrome import ChromeDriverManager



class NavegadorScraper:
    def __init__(self):
        # Configuracion del Navegador de Scrapper
        self.options = webdriver.ChromeOptions()
        self.options.binary_location = '/usr/bin/chromium'
        self.options.add_argument('--headless=new')
        self.options.add_argument('--disable-gpu')
        self.options.add_argument('--disable-dev-shm-usage')
        self.options.add_argument('--no-sandbox')
        self.options.add_argument('--ignore-certificate-errors')
        self.options.add_argument('--ignore-ssl-errors')
        self.options.add_argument('--window-size=1920,1080')
        self.options.add_argument('--disable-extensions')
        self.options.add_argument('--remote-allow-origins=*')
        self.options.page_load_strategy = 'eager'
        os.environ['WDM_SSL_VERIFY'] = '0'

        # Atributos de la clase
        self.service = Service('/usr/bin/chromedriver')
        self.driver = webdriver.Chrome(service=self.service, options=self.options)
        self.driver.set_page_load_timeout(30)
        self.wait = WebDriverWait(self.driver, 15)

    def get_page(self, url):
        return self.driver.get(url)



    def refresh_page(self):
        try:
            self.driver.quit()
        except:
            pass
        # IMPORTANTE: recrear con service + options, igual que en __init__
        self.driver = webdriver.Chrome(service=self.service, options=self.options)
        print('✅ Navegador reiniciado')

    def _leer_celdas(self, fila):
        return fila.find_elements(By.TAG_NAME, 'td')

    def _leer_texto(self, elemento, by, selector):
        return elemento.find_element(by, selector).text.strip()

    def _leer_filas(self, seccion, by, selector):
        return seccion.find_elements(by, selector)

    def _textos_de_celdas(self, fila):
        return [c.text.strip() for c in self._leer_celdas(fila)]
