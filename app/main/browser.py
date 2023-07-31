""" Selenium и все, что связано с управлением браузером """
__author__ = 'ke.mizonov'
import json
import os
from typing import Optional, List, Dict
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException
from selenium.webdriver import DesiredCapabilities
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from config import Config

WAIT_TIME = 60


class KmBrowser:
    """ Selenium и все, что связано с управлением браузером """

    def __init__(self, hidden: bool = True):
        self.browser = self.start_browser(hidden=hidden)

    def close(self):
        """ Закрывает браузер """
        self.browser.close()

    def find_element_by_selector(self, selector: str, timeout: int = WAIT_TIME) -> Optional[WebElement]:
        """ Пытается найти элемент по CSS-селектору

        Args:
            selector: строка, описывающая селектор
            timeout: время ожидания элемента в секундах

        Returns:
            элемент страницы
        """
        element_exists = self.wait(selector=selector, timeout=timeout)
        if not element_exists:
            return None
        return self.browser.find_element(by=By.CSS_SELECTOR, value=selector)

    def find_elements_by_selector(self, selector: str, timeout: int = WAIT_TIME) -> Optional[List[WebElement]]:
        """ Пытается найти элементы по CSS-селектору

        Args:
            selector: строка, описывающая селектор
            timeout: время ожидания элемента в секундах

        Returns:
            элементы страницы
        """
        element_exists = self.wait(selector=selector, timeout=timeout)
        if not element_exists:
            return None
        return self.browser.find_elements(by=By.CSS_SELECTOR, value=selector)

    def try_to_click(self, xpath: str, timeout: int = WAIT_TIME) -> bool:
        WebDriverWait(self.browser, timeout).until(ec.element_to_be_clickable((By.XPATH, xpath)))
        try:
            self.browser.find_element(by=By.XPATH, value=xpath).click()
            return True
        except ElementClickInterceptedException:
            return False

    def get_browser_logs(self) -> List[Dict]:
        """ Получает все ответы JSON из логов браузера

        Returns:
            список логов браузера
        """
        logs_raw = self.browser.get_log('performance')
        logs = []
        for log in logs_raw:
            msg = json.loads(log['message'])['message']
            if not (msg['method'] == 'Network.responseReceived' and 'json' in msg['params']['response']['mimeType']):
                continue
            logs.append(msg)
        return logs

    def get_html(self, selector: str, timeout: int = WAIT_TIME) -> Optional[str]:
        """ Получает содержимое HTML-страницы

        Args:
            selector: строка, описывающая селектор для ожидания
            timeout: время ожидания элемента в секундах

        Returns:
            html
        """
        element_exists = self.wait(selector=selector, timeout=timeout)
        if not element_exists:
            return None
        return self.browser.page_source

    def get_soup(self, selector: str, timeout: int = WAIT_TIME) -> Optional[BeautifulSoup]:
        """ Получает содержимое HTML-страницы в виде "супа" bs4

        Args:
            selector: строка, описывающая селектор для ожидания
            timeout: время ожидания элемента в секундах

        Returns:
            "суп"
        """
        element_exists = self.wait(selector=selector, timeout=timeout)
        if not element_exists:
            return None
        return BeautifulSoup(self.browser.page_source, 'html.parser')

    def open(self, url: str):
        """ Открывает указанный сайт

        Args:
            url: адрес сайта
        """
        self.browser.get(url=url)

    def wait(self, selector: str, timeout: int = WAIT_TIME) -> bool:
        """ Ждем прогрузки всех элментов, удовлетворяющих селектору

        Args:
            selector: строка, описывающая селектор
            timeout: время ожидания элемента в секундах

        Returns:
            True - если элемент загрузился за требуемое время
        """
        try:
            WebDriverWait(self.browser, timeout).until(
                ec.visibility_of_all_elements_located((By.CSS_SELECTOR, selector))
            )
            return True
        except TimeoutException:
            return False

    @staticmethod
    def start_browser(proxy: Optional[str] = None, hidden: bool = True) -> webdriver.Chrome:
        """ Запускает экземпляр браузера

        Args:
            proxy: адрес прокси-сервера
            hidden: запускать без интерфейса

        Returns:
            экземпляр браузера
        """
        options = webdriver.ChromeOptions()
        options.binary_location = os.environ.get("GOOGLE_CHROME_BIN")
        options.add_argument("--no-sandbox")
        if proxy:
            options.add_argument(f'--proxy-server={proxy}')
        if hidden:
            options.add_argument('headless')  # закомментируй, если хочется видеть браузер
        options.add_argument('--verbose')
        options.add_argument("--disable-dev-shm-usage")
        # пропускаем всякие предупреждения о сертификатах и безопасности
        options.add_argument('--ignore-ssl-errors=yes')
        options.add_argument('--ignore-certificate-errors')
        # тут мы говорим браузеру писать логи
        # capabilities = DesiredCapabilities.CHROME
        # capabilities['goog:loggingPrefs'] = {'performance': 'ALL'}

        # options.set_capability("loggingPrefs", {'performance': 'ALL'})

        # инициализируем экземпляр браузера
        service = Service(executable_path=Config().chromedriver_path)
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(WAIT_TIME)
        return driver
