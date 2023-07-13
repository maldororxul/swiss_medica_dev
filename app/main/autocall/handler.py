""" Управление автообзвоном

Notes:
    Ограничение! Один и тот же номер не может участвовать в нескольких автообзвонах!
"""
__author__ = 'ke.mizonov'
import json
import time
from datetime import datetime
from typing import Dict, Optional
from flask import current_app
from app import db
from app.amo.processor.functions import clear_phone
from app.main.browser import KmBrowser
from config import Config
from app.amo.api.client import SwissmedicaAPIClient, DrvorobjevAPIClient
from app.amo.processor.processor import SMDataProcessor, CDVDataProcessor
from app.models.autocall import SMAutocallNumber, CDVAutocallNumber
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

WEEKDAY = {
    1: "Monday",
    2: "Tuesday",
    3: "Wednesday",
    4: "Thursday",
    5: "Friday",
    6: "Saturday",
    0: "Sunday"
}


class Autocall:
    """ Класс, управляющий автообзвоном """
    def __init__(self, branch: Optional[str] = None):
        self.__branch = branch

    @property
    def __app(self):
        return current_app._get_current_object()

    @property
    def __sipuni_branch_config(self) -> Dict:
        return self.__sipuni_config.get(self.__branch)

    @property
    def __sipuni_config(self) -> Dict:
        return json.loads(Config.SIPUNI)

    def handle_autocall_result(self, data: Dict):
        status = data.get('status')
        # получаем экземпляр номера автообзвона из нашей БД
        with self.__app.app_context():
            number_entity = self.__get_autocall_number_entity(number=data.get('number'))
            number_entity.calls += 1
            number_entity.last_call_timestamp = int(time.time())
            if not number_entity:
                return
            # получаем идентификаторы обзвона и лида, связанные с этим номером
            autocall_id = number_entity.autocall_id
            autocall_config = self.__sipuni_branch_config.get(autocall_id)
        if status == 'Исходящий, неотвеченный':
            with self.__app.app_context():
                db.session.commit()
        elif status == 'Исходящие, отвеченные':
            # изменяем запись об автообзвоне в БД, перемещаем лид
            with self.__app.app_context():
                lead_id = number_entity.lead_id
                # удаляем номер из нашей базы
                db.session.delete(number_entity)
                db.session.commit()
            amo_client = API_CLIENT.get(self.__branch)()
            amo_client.update_lead(
                lead_id=lead_id,
                data={
                    'pipeline_id': int(autocall_config.get('success_pipeline_id')),
                    'status_id': int(autocall_config.get('success_status_id'))
                }
            )
        # # получаем список автообзвона из БД
        # with self.__app.app_context():
        #     all_numbers = number_entity.query.all() or []
        # # удаляем все номера из автообзвона (через браузер)
        # browser: KmBrowser = self.__get_sipuni_browser()
        # browser.open(url=f'https://sipuni.com/ru_RU/settings/autocall/delete_numbers_all/{autocall_id}')
        # time.sleep(10)
        # browser.close()
        # # снова добавляем в автообзвон номера, записанные в БД
        # sipuni_client = Sipuni(sipuni_config=self.__sipuni_branch_config)
        # for line in all_numbers:
        #     sipuni_client.add_number_to_autocall(number=line.number, autocall_id=autocall_id)

    def handle_lead_status_changed(self, data: Dict) -> None:
        """ Обработка смены статуса лида

        Args:
            data: данные, пришедшие через вебхук с Amo

        Notes:
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
        self.__branch = data.get('account[subdomain]')
        processor = DATA_PROCESSOR.get(self.__branch)()
        # реагируем только на изменение статусов
        if 'leads[status][0][old_status_id]' not in data and 'leads[status][0][status_id]' not in data:
            processor.log.add(text=f'Wrong event')
            return
        # проверяем, что для данной стадии и воронки настроен автообзвон (см. глоабльную переменную SIPUNI)
        autocall_id = self.__get_autocall_id(
            pipeline_id=data.get('leads[status][0][pipeline_id]'),
            status_id=data.get('leads[status][0][status_id]'),
        )
        if not autocall_id:
            return
        amo_client = API_CLIENT.get(self.__branch)()
        try:
            lead_id = data.get('leads[status][0][id]')
            # читаем данные лида и контакта с источника
            lead = amo_client.get_lead_by_id(lead_id=lead_id)
            _embedded = lead.get('_embedded') or {}
            contacts = _embedded.get('contacts')
            if not contacts:
                return
            contact = amo_client.get_contact_by_id(contact_id=contacts[0]['id'])
            # вытаскиваем из контакта телефоны
            phones = []
            for contact_field in contact.get('custom_fields_values') or []:
                if contact_field['field_code'] != 'PHONE':
                    continue
                for phone in contact_field['values']:
                    phones.append(clear_phone(phone['value']))
            if not phones:
                return
            # записываем номер и идентификатор лида в БД
            number = phones[0]
            with self.__app.app_context():
                autocall_number = AUTOCALL_NUMBER.get(self.__branch)
                number_entity = autocall_number.query.filter_by(number=number).first()
                if number_entity is None:
                    number_entity = autocall_number(
                        autocall_id=autocall_id,
                        lead_id=int(lead_id),
                        number=number,
                        calls=0,
                        branch=self.__branch,
                        last_call_timestamp=int(time.time())
                    )
                    db.session.add(number_entity)
                    db.session.commit()
        except Exception as exc:
            processor.log.add(text=f'Error [parse_webhook_data]: {exc}')

    def start_autocall(self, autocall_id: int):
        """ Начинает автообзвон

        Args:
            autocall_id: идентификатор автообзвона в Sipuni
        """
        browser: KmBrowser = self.__get_sipuni_browser()
        browser.open(url=f'https://sipuni.com/ru_RU/settings/autocall/start/{autocall_id}')
        time.sleep(10)
        browser.close()

    def start_autocalls(self):
        """ Перезапускает все автообзвоны """
        browser: KmBrowser = self.__get_sipuni_browser()
        # удаляем все номера из всех автообзвонов Sipuni (через браузер)
        for data in self.__sipuni_config.values():
            for autocall_id in (data.get('autocall') or {}).keys():
                browser.open(url=f'https://sipuni.com/ru_RU/settings/autocall/delete_numbers_all/{autocall_id}')
                time.sleep(10)
        with self.__app.app_context():
            # читаем номера из БД и добавляем в автообзвон те, которые удовлетворяют условию
            for branch in self.__sipuni_config.keys():
                autocall_model = AUTOCALL_NUMBER.get(branch)
                all_numbers = autocall_model.query.all()
                branch_config = self.__sipuni_config.get(branch)
                sipuni_client = Sipuni(sipuni_config=branch_config)
                for line in all_numbers:
                    # fixme с момента last_call_timestamp должно пройти не менее 24 часов
                    # if line.last_call_timestamp + 24 * 3600 > time.time():
                    #     continue
                    # конфиг SIPUNI существует
                    autocall_config = (branch_config.get('autocall') or {}).get(str(line.autocall_id))
                    if not autocall_config:
                        continue
                    # лимит звонков еще не достигнут
                    if line.calls >= int(autocall_config.get('calls_limit')):
                        continue
                    schedule = autocall_config.get('schedule')
                    # существует расписание для данного автообзвона
                    if not schedule:
                        continue
                    # сегодня день, подходящий под расписание
                    curr_dt = datetime.now()
                    weekday_schedule = schedule.get(
                        WEEKDAY.get(curr_dt.weekday())
                    )
                    if not weekday_schedule:
                        continue
                    # сейчас время, подходящее для звонка
                    for period in weekday_schedule:
                        _from, _to = period.split(' - ')
                        _from = self.__build_datetime_from_timestring(timestring=_from)
                        _to = self.__build_datetime_from_timestring(timestring=_to)
                        if _from <= curr_dt <= _to:
                            break
                    else:
                        continue
                    sipuni_client.add_number_to_autocall(number=line.number, autocall_id=line.autocall_id)
        # запускаем все автообзвоны Sipuni
        for data in self.__sipuni_config.values():
            for autocall_id in (data.get('autocall') or {}).keys():
                browser.open(url=f'https://sipuni.com/ru_RU/settings/autocall/start/{autocall_id}')
                time.sleep(10)
        browser.close()

    def __get_autocall_id(self, pipeline_id: str, status_id: str) -> Optional[int]:
        """ Получает идентификатор автообзвона в Sipuni на основе идентификаторов воронки и статуса

        Args:
            pipeline_id: идентификатор воронки автообзвона в Amo
            status_id: идентификатор статуса (стадии) внутри воронки автообзвона в Amo

        Returns:
            идентификатор автообзвона в Sipuni
        """
        for autocall_id, data in (self.__sipuni_branch_config.get('autocall') or {}).items():
            if str(data.get('pipeline_id')) == pipeline_id and str(data.get('status_id')) == status_id:
                return int(autocall_id)
        return None

    def __get_autocall_number_entity(self, number: str) -> Optional[db.Model]:
        """ Перебирает таблицы БД в поисках экземпляра номера автодозвона

        Args:
            number: номер, который следует найти в БД

        Returns:
            экземпляр номера автодозвона из БД
        """
        for autocall_model in AUTOCALL_NUMBER.values():
            number_entity = autocall_model.query.filter_by(number=number).first()
            if number_entity:
                # по найденному номеру определяем филиал
                self.__branch = number_entity.branch
                return number_entity
        else:
            return None

    def __get_sipuni_browser(self) -> KmBrowser:
        """ Получить экземпляр браузера с авторизацией в личном кабинете Sipuni """
        browser = KmBrowser()
        browser.open(url='https://sipuni.com/ru_RU/login')
        sipuni_config = self.__sipuni_branch_config
        login_line = browser.find_element_by_selector(selector='#login_username_email')
        login_line.send_keys(sipuni_config.get('login'))
        password_line = browser.find_element_by_selector(selector='#login_password')
        password_line.send_keys(sipuni_config.get('password'))
        submit_btn = browser.find_element_by_selector(selector='#login_button')
        submit_btn.click()
        browser.wait(
            selector='body > header > div.navigation.row-fluid > div.pull-left.menu-top > ul > li:nth-child(1) > a'
        )
        return browser

    @staticmethod
    def __build_datetime_from_timestring(timestring: str) -> datetime:
        """ Строит дату-время на основе переданной строки в формате "%H:%M"

        Args:
            timestring: строка, содержащее время в формате "%H:%M"

        Returns:
            дата-время
        """
        return datetime.combine(
            datetime.today(),
            datetime.strptime(timestring, "%H:%M").time()
        )
