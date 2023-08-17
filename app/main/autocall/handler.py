""" Управление автообзвоном

Notes:
    Ограничение! Один и тот же номер не может участвовать в нескольких автообзвонах!
"""
__author__ = 'ke.mizonov'

import gc
import json
import time
import uuid
from datetime import datetime
from typing import Dict, Optional
from flask import current_app, Flask
from app import db
from app.amo.processor.functions import clear_phone
from app.main.autocall.error import SipuniConfigError
from app.main.browser import KmBrowser
from app.main.routes.whatsapp import send_wahtsapp_message
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


def start_autocall_iteration(app: Flask, branch: str):
    """ Перезапускает все автообзвоны """
    autocall_controller = Autocall(branch=branch)
    autocall_controller.start_autocalls(app=app)
    del autocall_controller
    gc.collect()


class Autocall:
    """ Класс, управляющий автообзвоном """
    def __init__(self, branch: Optional[str] = None):
        self.__branch = branch

    @property
    def __sipuni_branch_config(self) -> Dict:
        return self.__sipuni_config.get(self.__branch)

    @property
    def __sipuni_config(self) -> Dict:
        return Config().sipuni

    def handle_autocall_result(self, data: Dict):
        """ Обработка результата звонка (Sipuni)

        Args:
            data: данные, пришедшие через webhook в формате
                {
                    "call_id": "1429019739.49501",
                    "event": "2",
                    "dst_type": "2",
                    "dst_num": "012345261","src_type": "1",
                    "src_num": "89104846817",
                    "timestamp": "1429019790", "status": "ANSWER",
                    "call_start_timestamp": "1429019739",
                    "call_answer_timestamp": "1429019750",
                    "call_record_link": "<a href="https://sipuni.com/api/crm/record">https://sipuni.com/api/crm/record</a>;?
                    id=1429019739.49501&hash=abcdefghijklmnopqrstuvwxyzabcdef&user=012345", "channel": "Local/261@transfer_vats-000001e9;2",
                    "treeName": "Тестирование CRM", "treeNumber": "000960393"
                }
        """
        status = data.get('status')
        # получаем экземпляр номера автообзвона из нашей БД
        app = current_app._get_current_object()
        with app.app_context():
            number_entity = self.__get_autocall_number_entity(number=data.get('number'))
            if not number_entity:
                return
            number_entity.calls += 1
            number_entity.last_call_timestamp = int(time.time())
            # получаем идентификаторы обзвона и лида, связанные с этим номером
            autocall_id = number_entity.autocall_id
            autocall_config = self.__sipuni_branch_config.get('autocall').get(str(autocall_id))
            if status == 'Исходящий, неотвеченный':
                db.session.commit()
            elif status == 'Исходящие, отвеченные':
                # изменяем запись об автообзвоне в БД, перемещаем лид
                lead_id = number_entity.lead_id
                # удаляем номер из нашей базы
                db.session.delete(number_entity)
                db.session.commit()
                # перемещаем лид (факт перемещения вручную игнорируются, ошибки игнорируются)
                amo_client = API_CLIENT.get(self.__branch)()
                amo_client.update_lead(
                    lead_id=lead_id,
                    data={
                        'pipeline_id': int(autocall_config.get('success_pipeline_id')),
                        'status_id': int(autocall_config.get('success_status_id'))
                    }
                )
                # spl = (data.get('"call_record_link"') or '').split('href="')
                # link = spl[1].split('">')[0] if len(spl) > 1 else ''
                # duration = int(data.get('timestamp') or 0) - int(data.get('call_answer_timestamp') or 0)
                # try:
                #     note_data = [{
                #         "entity_id": lead_id,
                #         "note_type": "call_out",
                #         "params": {
                #             "uniq": str(uuid.uuid4()),
                #             "duration": duration,
                #             "source": "Autocall",
                #             "link": link,
                #             "phone": number_entity.number
                #         }
                #     }]
                #     amo_client.add_note(entity_id=lead_id, data=note_data)
                # except Exception as exc:
                #     print(exc)

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
        # Проверяем, что для данной стадии и воронки настроен автообзвон (см. глобальную переменную SIPUNI)
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
            app = current_app._get_current_object()
            with app.app_context():
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
            return
        # отправляем сообщение в WhatsApp
        whatsapp_config = Config().whatsapp.get(self.__branch)
        if not whatsapp_config:
            return
        number_from = (whatsapp_config.get('numbers') or [None])[0] or {}
        if not number_from:
            return
        template = None
        for item in whatsapp_config.get('templates') or []:
            # хардкод пока что, т.к. не ясно, как ассоциировать номер автообзвона с шаблоном
            if item['name'] in ("couldnt_reach_you_serbian", ):
                template = item
                break
        send_wahtsapp_message(number_id_from=number_from['id'], template=template, number_to=number)

    def start_autocall(self, autocall_id: int):
        """ Начинает автообзвон

        Args:
            autocall_id: идентификатор автообзвона в Sipuni
        """
        processor = DATA_PROCESSOR.get(self.__branch)()
        processor.log.add(text='starting autocall')
        try:
            self.__start_autocall(autocall_id=autocall_id)
        except Exception as exc:
            processor.log.add(str(exc))

    def __start_autocall(self, autocall_id: int):
        try:
            browser: KmBrowser = self.__get_sipuni_browser()
        except SipuniConfigError:
            try:
                browser.close()
            except:
                pass
            return
        browser.open(url=f'https://sipuni.com/ru_RU/settings/autocall/start/{autocall_id}')
        time.sleep(10)
        browser.close()

    def start_autocalls(self, app: Flask):
        """ Перезапускает все автообзвоны """
        with app.app_context():
            processor = DATA_PROCESSOR.get(self.__branch)()
            processor.log.add(text=f'starting autocalls')
            # try:
            self.__start_autocalls(processor=processor)
            # except Exception as exc:
            #     processor.log.add(str(exc))

    def __start_autocalls(self, processor):
        branch_config = self.__sipuni_branch_config
        if not branch_config:
            processor.log.add(text=f'no config for {self.__branch}')
            return
        autocall_ids = list(branch_config.get('autocall').keys())
        amo_client = API_CLIENT.get(self.__branch)()
        # app = current_app._get_current_object()
        # with app.app_context():
        # читаем номера из БД и добавляем в автообзвон те, которые удовлетворяют условию
        # for branch in self.__sipuni_config.keys():
        autocall_model = AUTOCALL_NUMBER.get(self.__branch)
        all_numbers = autocall_model.query.all()
        branch_config = self.__sipuni_branch_config
        sipuni_client = Sipuni(sipuni_config=branch_config)
        numbers_added = []
        for line in all_numbers:
            # с момента last_call_timestamp должно пройти не менее 23 часов (если звонок не первый)
            if line.last_call_timestamp + 23 * 3600 > time.time() and line.calls > 0:
                waiting_for = f"waiting for {line.last_call_timestamp + 23 * 3600}, now {time.time()}"
                processor.log.add(text=f'out of schedule (0) {line.autocall_id} number {line.number} ({waiting_for})')
                continue
            # конфиг SIPUNI существует
            autocall_config = (branch_config.get('autocall') or {}).get(str(line.autocall_id))
            if not autocall_config:
                processor.log.add(text=f'config not found {line.autocall_id} number {line.number}')
                continue
            # лимит звонков еще не достигнут
            if line.calls >= int(autocall_config.get('calls_limit')):
                processor.log.add(text=f'calls limit reached {line.autocall_id} number {line.number}')
                db.session.delete(line)
                continue
            schedule = autocall_config.get('schedule')
            # существует расписание для данного автообзвона
            if not schedule:
                processor.log.add(text=f'schedule not found (0) {line.autocall_id} number {line.number}')
                continue
            # лид все еще находится в воронке автообзвона
            lead = amo_client.get_lead_by_id(lead_id=line.lead_id)
            pipeline_id, status_id = lead.get('pipeline_id'), lead.get('status_id')
            if not pipeline_id or not status_id:
                processor.log.add(text=f'lead pipeline or status not found {line.autocall_id} number {line.number}')
                continue
            if autocall_config.get('pipeline_id') != str(pipeline_id) \
                    or autocall_config.get('status_id') != str(status_id):
                # лид был перемещен, удаляем номер из БД автообзвона
                processor.log.add(text=f"removing number {line.number} from database")
                db.session.delete(line)
                db.session.commit()
                time.sleep(0.25)
                continue
            # сегодня день, подходящий под расписание
            curr_dt = datetime.now()
            weekday_schedule = schedule.get(
                WEEKDAY.get(curr_dt.weekday())
            )
            if not weekday_schedule:
                processor.log.add(text=f'schedule not found {line.autocall_id} number {line.number}')
                continue
            # сейчас время, подходящее для звонка
            # processor.log.add(text=f'schedule: {weekday_schedule}, current {curr_dt}')
            for period in weekday_schedule:
                _from, _to = period.split(' - ')
                _from = self.__build_datetime_from_timestring(timestring=_from)
                _to = self.__build_datetime_from_timestring(timestring=_to)
                if _from <= curr_dt <= _to:
                    break
            else:
                # processor.log.add(text=f'out of schedule {line.autocall_id} number {line.number}')
                continue
            # processor.log.add(text=f'added to autocall {line.autocall_id} number {line.number}')
            numbers_added.append({'number': line.number, 'autocall_id': line.autocall_id})
        # запускаем все автообзвоны Sipuni
        if not numbers_added:
            processor.log.add(text=f'no numbers for autocall')
            return
        processor.log.add(text=f'got {len(numbers_added)} numbers for autocall')
        try:
            browser: KmBrowser = self.__get_sipuni_browser()
        except SipuniConfigError:
            processor.log.add(text=f'SipuniConfigError')
            try:
                browser.close()
            except:
                pass
            return
        except Exception as exc:
            processor.log.add(text=f'browser error: {exc}')
            try:
                browser.close()
            except:
                pass
            return
        # удаляем все номера из всех автообзвонов Sipuni (через браузер)
        for autocall_id in autocall_ids:
            browser.open(url=f'https://sipuni.com/ru_RU/settings/autocall/delete_numbers_all/{autocall_id}')
            time.sleep(10)
        for item in numbers_added:
            sipuni_client.add_number_to_autocall(number=item['number'], autocall_id=item['autocall_id'])
            time.sleep(0.25)
        for autocall_id in autocall_ids:
            try:
                browser.open(url=f'https://sipuni.com/ru_RU/settings/autocall/start/{autocall_id}')
            except Exception as exc:
                try:
                    browser.close()
                except:
                    pass
                processor.log.add(text=f'browser error: {exc}')
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
        if not sipuni_config:
            raise SipuniConfigError(f'Sipuni Config for branch {self.__branch} is absent')
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
