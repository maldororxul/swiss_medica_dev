"""
Формат данных при смене статуса лида:
{
    'leads[status][0][id]': '23802129',
    'leads[status][0][status_id]': '47873533',
    'leads[status][0][pipeline_id]': '5389528',
    'leads[status][0][old_status_id]': '47888833',
    'leads[status][0][old_pipeline_id]': '5389528',
    'account[id]': '29013640',
    'account[subdomain]': 'drvorobjev'
}

"""
import time
from typing import Dict
from app.amo.api.client import SwissmedicaAPIClient, DrvorobjevAPIClient
from app.amo.processor.functions import clear_phone
from app.amo.processor.processor import SMDataProcessor, CDVDataProcessor
from app.main.browser import KmBrowser
from config import Config
from modules.external.sipuni.sipuni_api import Sipuni

API_CLIENT = {
    'swissmedica': SwissmedicaAPIClient,
    'drvorobjev': DrvorobjevAPIClient,
}

DATA_PROCESSOR = {
    'swissmedica': SMDataProcessor,
    'drvorobjev': CDVDataProcessor,
}


def start_autocall():
    browser = KmBrowser()
    browser.open(url='https://sipuni.com/ru_RU/login')
    login, password = Config.SUPUNI_LOGIN_CDV, Config.SUPUNI_PASSWORD_CDV
    login_line = browser.find_element_by_selector(selector='#login_username_email')
    login_line.send_keys(login)
    password_line = browser.find_element_by_selector(selector='#login_password')
    password_line.send_keys(password)
    submit_btn = browser.find_element_by_selector(selector='#login_button')
    submit_btn.click()
    browser.wait(
        selector='body > header > div.navigation.row-fluid > div.pull-left.menu-top > ul > li:nth-child(1) > a'
    )
    browser.open(url='https://sipuni.com/ru_RU/settings/autocall/restart/21774')
    time.sleep(10)
    browser.close()


def parse_webhook_data(data: Dict):
    branch = data.get('account[subdomain]')
    processor = DATA_PROCESSOR.get(branch)()
    # реагируем только на изменение статусов
    if 'leads[status][0][old_status_id]' not in data and 'leads[status][0][status_id]' not in data:
        processor.log.add(text=f'Wrong event')
        return
    client = API_CLIENT.get(branch)()
    try:
        # читаем данные лида и контакта с источника
        lead = client.get_lead_by_id(lead_id=data.get('leads[status][0][id]'))
        _embedded = lead.get('_embedded') or {}
        contacts = _embedded.get('contacts')
        if not contacts:
            return
        contact = client.get_contact_by_id(contact_id=contacts[0]['id'])
        # вытаскиваем из контакта телефоны
        phones = []
        for contact_field in contact.get('custom_fields_values') or []:
            if contact_field['field_code'] != 'PHONE':
                continue
            for phone in contact_field['values']:
                phones.append(clear_phone(phone['value']))
        processor.log.add(text=f'Phones: {phones}'[:999])
        if not phones:
            return
        client = Sipuni(Config.SUPUNI_ID_CDV, Config.SIPUNI_KEY_CDV)
        client.add_number_to_autocall(number=phones[0], autocall_id=Config.SIPUNI_AUTOCALL_ID_CDV)
        # запуск обзвона (временно!)
        start_autocall()

    except Exception as exc:
        processor.log.add(text=f'Error [parse_webhook_data]: {exc}'[:999])
