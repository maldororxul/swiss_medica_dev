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
from flask import current_app
from app import db
from app.amo.api.client import SwissmedicaAPIClient, DrvorobjevAPIClient
from app.amo.processor.functions import clear_phone
from app.amo.processor.processor import SMDataProcessor, CDVDataProcessor
from app.main.browser import KmBrowser
from app.models.autocall import SMAutocallNumber, CDVAutocallNumber
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

AUTOCALL_NUMBER = {
    'swissmedica': SMAutocallNumber,
    'drvorobjev': CDVAutocallNumber,
}


def get_sipuni_browser() -> KmBrowser:
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
    return browser


def start_autocall():
    browser: KmBrowser = get_sipuni_browser()
    browser.open(url='https://sipuni.com/ru_RU/settings/autocall/start/21774')
    time.sleep(10)
    browser.close()


def handle_lead_status_changed(data: Dict):
    branch = data.get('account[subdomain]')
    processor = DATA_PROCESSOR.get(branch)()
    # реагируем только на изменение статусов
    if 'leads[status][0][old_status_id]' not in data and 'leads[status][0][status_id]' not in data:
        processor.log.add(text=f'Wrong event')
        return
    client = API_CLIENT.get(branch)()
    try:
        lead_id = data.get('leads[status][0][id]')
        # читаем данные лида и контакта с источника
        lead = client.get_lead_by_id(lead_id=lead_id)
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
        # processor.log.add(text=f'Phones: {phones}')
        if not phones:
            return
        # записываем номер и идентификатор лида в БД
        number = phones[0]
        app = current_app._get_current_object()
        with app.app_context():
            autocall_number = AUTOCALL_NUMBER.get(branch)
            number_entity = autocall_number.query.filter_by(number=number).first()
            if number_entity is None:
                number_entity = autocall_number(
                    lead_id=int(lead_id),
                    number=number,
                    success=0,
                )
                db.session.add(number_entity)
                db.session.commit()
        # добавляем номер в автообзвон Sipuni
        client = Sipuni(Config.SUPUNI_ID_CDV, Config.SIPUNI_KEY_CDV)
        client.add_number_to_autocall(number=number, autocall_id=Config.SIPUNI_AUTOCALL_ID_CDV)
        # запуск обзвона (временно!)
        start_autocall()
    except Exception as exc:
        processor.log.add(text=f'Error [parse_webhook_data]: {exc}')


def handle_new_lead(data: Dict) -> str:
    return '\n'.join([f'{key} :: {value}' for key, value in data.items()])


def handle_autocall_result(data: Dict, branch: str):
    status = data.get('status')
    number = data.get('number')
    processor = DATA_PROCESSOR.get(branch)()
    processor.log.add(text=f'{number} :: {status}')
    if status == 'Исходящий, неотвеченный':
        pass
        # # удаляем все номера и снова добавляем те, до которых не удалось дозвониться
        # sipuni_client = Sipuni(Config.SUPUNI_ID_CDV, Config.SIPUNI_KEY_CDV)
        # delete_response = sipuni_client.delete_number_from_autocall(
        #     number=number,
        #     autocall_id=Config.SIPUNI_AUTOCALL_ID_CDV
        # )
        # processor.log.add(text=str(delete_response))
        # sipuni_client.add_number_to_autocall(number=number, autocall_id=Config.SIPUNI_AUTOCALL_ID_CDV)
    elif status == 'Исходящие, отвеченные':

        # fixme delete_number через браузер?
        # browser: KmBrowser = get_sipuni_browser()
        # browser.open(url='https://sipuni.com/ru_RU/settings/autocall/start/21774')
        # time.sleep(10)
        # browser.close()

        # клиент ответил на звонок
        # удаляем номер из автообзвона Sipuni
        # fixme sipuni позволяет удалить только те номера, на которые не удалось дозвониться
        # sipuni_client = Sipuni(Config.SUPUNI_ID_CDV, Config.SIPUNI_KEY_CDV)
        # tmp = sipuni_client.delete_number_from_autocall(
        #     number=data.get('number'),
        #     autocall_id=Config.SIPUNI_AUTOCALL_ID_CDV
        # )
        # print(f'Number deleted: {tmp}')
        # изменяем запись об автообзвоне в БД, перемещаем лид
        app = current_app._get_current_object()
        with app.app_context():
            autocall_number = AUTOCALL_NUMBER.get(branch)
            number_entity = autocall_number.query.filter_by(number=data.get('number')).first()
            # autocall_record = autocall_number.query.where(autocall_number.number == data.get('number')).first()
            lead_id = number_entity.lead_id
            db.session.delete(number_entity)
            # number_entity.success = 1
            db.session.commit()
            all_numbers = autocall_number.query.all()
        amo_client = API_CLIENT.get(branch)()
        amo_client.update_lead(
            lead_id=lead_id,
            data={
                'pipeline_id': int(Config.AUTOCALL_SUCCESS_PIPELINE_ID_CDV),
                'status_id': int(Config.AUTOCALL_SUCCESS_STATUS_ID_CDV)
            }
        )
        # удаляем все номера из автообзвона (через браузер)
        browser: KmBrowser = get_sipuni_browser()
        browser.open(url='https://sipuni.com/ru_RU/settings/autocall/delete_numbers_all/21774')
        time.sleep(10)
        browser.close()
        # снова добавляем в автообзвон номера, записанные в БД
        sipuni_client = Sipuni(Config.SUPUNI_ID_CDV, Config.SIPUNI_KEY_CDV)
        for line in all_numbers:
            sipuni_client.add_number_to_autocall(number=line.number, autocall_id=Config.SIPUNI_AUTOCALL_ID_CDV)
