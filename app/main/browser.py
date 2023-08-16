""" Selenium и все, что связано с управлением браузером """
__author__ = 'ke.mizonov'
import json
import os
# import threading
from typing import Optional, List, Dict
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException
# from selenium.webdriver import DesiredCapabilities
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
# from webdriver_manager.chrome import ChromeDriverManager

WAIT_TIME = 60


class KmBrowser:
    """ Selenium и все, что связано с управлением браузером """
    # _instance = None
    # _lock = threading.Lock()  # This will be the lock to ensure one function at a time can use the browser

    def __init__(self, hidden: bool = True):
        self.browser = self.start_browser(hidden=hidden)

    # def __new__(cls, *args, **kwargs):
    #     with cls._lock:
    #         if not cls._instance:
    #             cls._instance = super().__new__(cls)
    #     return cls._instance

    def close(self):
        """ Закрывает браузер """
        # with self._lock:
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
        # with self._lock:
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

        # driver = webdriver.Chrome(
        #     # executable_path='chromedriver.exe',
        #     service=ChromeDriverManager().install(),
        #     options=options,
        #     # desired_capabilities=capabilities
        # )

        # инициализируем экземпляр браузера
        service = Service(executable_path=Config().chromedriver_path)
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(WAIT_TIME)
        return driver


"""
browser error: Message: session not created: This version of ChromeDriver only supports Chrome version 114 Current browser version is 116.0.5845.96 with binary path /app/.apt/opt/google/chrome/chrome Stacktrace: #0 0x5575aaaf84e3 #1 0x5575aa827c76 #2 0x5575aa85504a #3 0x5575aa8504a1 #4 0x5575aa84d029 #5 0x5575aa88bccc #6 0x5575aa88b47f #7 0x5575aa882de3 #8 0x5575aa8582dd #9 0x5575aa85934e #10 0x5575aaab83e4 #11 0x5575aaabc3d7 #12 0x5575aaac6b20 #13 0x5575aaabd023 #14 0x5575aaa8b1aa #15 0x5575aaae16b8 #16 0x5575aaae1847 #17 0x5575aaaf1243 #18 0x7fa9e6115b43
"""