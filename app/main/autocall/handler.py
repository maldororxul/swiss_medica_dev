""" Управление автообзвоном

Notes:
    Ограничение! Один и тот же номер не может участвовать в нескольких автообзвонах!
"""
__author__ = 'ke.mizonov'

import gc
import time
from datetime import datetime
from typing import Dict, Optional
import requests
from flask import current_app, Flask
from config import Config
from modules.external.sipuni.sipuni_api import Sipuni


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
        from app import db
        from app.main.autocall.constants import API_CLIENT
        # print('handle autocall result', data)
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
            autocall_config = self.__sipuni_branch_config.get('autocall').get(str(number_entity.autocall_id))
            # if status == 'Исходящий, неотвеченный':
            #     db.session.commit()
            if status == 'Исходящие, отвеченные':
                # изменяем запись об автообзвоне в БД
                lead_id = number_entity.lead_id
                # удаляем номер из нашей базы
                db.session.delete(number_entity)
                # перемещаем лид (факт перемещения вручную игнорируются, ошибки игнорируются)
                # print(
                #     'moving lead...',
                #     lead_id,
                #     autocall_config.get('success_pipeline_id'),
                #     autocall_config.get('success_status_id')
                # )
                amo_client = API_CLIENT.get(self.__branch)()
                amo_client.update_lead(
                    lead_id=lead_id,
                    data={
                        'pipeline_id': int(autocall_config.get('success_pipeline_id')),
                        'status_id': int(autocall_config.get('success_status_id'))
                    }
                )
            db.session.commit()
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
        from app import db
        from app.amo.processor.functions import clear_phone
        from app.main.autocall.constants import API_CLIENT, AUTOCALL_NUMBER, DATA_PROCESSOR
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
        # # отправляем сообщение в WhatsApp
        # whatsapp_config = Config().whatsapp.get(self.__branch)
        # if not whatsapp_config:
        #     return
        # number_from = (whatsapp_config.get('numbers') or [None])[0] or {}
        # if not number_from:
        #     return
        # template = None
        # for item in whatsapp_config.get('templates') or []:
        #     # хардкод пока что, т.к. не ясно, как ассоциировать номер автообзвона с шаблоном
        #     if item['name'] in ("couldnt_reach_you_serbian", ):
        #         template = item
        #         break
        # send_wahtsapp_message(number_id_from=number_from['id'], template=template, number_to=number)

    def start_autocalls(self, app: Flask):
        """ Перезапускает все автообзвоны """
        from app.main.autocall.constants import DATA_PROCESSOR
        with app.app_context():
            processor = DATA_PROCESSOR.get(self.__branch)()
            self.__start_autocalls(processor=processor)

    def get_cookies(self):
        cookies = {
            "swissmedica": {
                "OutSipClientTable_state": "0",
                "TreeTable_out_state": "1",
                "OurSipClientTable_state": "1",
                "lastTree": "2008785",
                "InSipClientTable_state": "1",
                "_ym_uid": "1691126352735114426",
                "_ym_d": "1691126352",
                "hcode": "d8c63cadc70f02c3a477148030cdb62f",
                "tmr_lvid": "37366c4d3b0bcfea4849829b4b9953da",
                "tmr_lvidTS": "1693377866197",
                "carrotquest_device_guid": "d12c9a4d-93c6-4d53-9a0d-a6e0d8f8f9b4",
                "carrotquest_uid": "1520601854042443087",
                "carrotquest_auth_token": "user.1520601854042443087.55906-5369ff2e5cfd9d6a816c5160eb.7e4ce86aeb6af33d920f53f93e16c180c041fd2b1f04452e",
                "roistat_first_visit": "217903",
                "___dc": "c0d800a2-0274-4a93-9558-4686771f1980",
                "visitor_uid": "8ec3677a-79fa-4ede-894e-0928f629a6b9",
                "user": "ZGVmNTAyMDA0YzQwN2I1M2NmNmRlMzBmYjA1ZmE4ODNiNGI3ZmRhOWE2YmU3NDYzN2QzNjg3YzMyNmYwNTllNTk2ZmI3YmRkMjdmNjY5OTdmYTA2ZDcwOGNhZjIzMWM3ZGJlNzE0YTFjN2RjMmQ1NjdmYzFiMDFkODExM2ExYmJjOGJjMTYzMzM2MTEwNGFlZjlkYTg1NjExYzkxZWNmYWY0YmM5MmVkYzgwMmY1NTlhMjgyMDc2YjM0MWRjNzgx",
                "PHPSESSID": "5cq291r8tqkpc961uu03tpu0jn",
                "_ga": "GA1.1.1216748222.1691126352",
                "_ym_isad": "2",
                "roistat_visit": "240456",
                "roistat_is_need_listen_requests": "0",
                "roistat_is_save_data_in_cookie": "1",
                "carrotquest_realtime_services_transport": "wss",
                "tmr_detect": "0%7C1694773631585",
                "roistat_call_tracking": "1",
                "roistat_emailtracking_email": "null",
                "roistat_emailtracking_tracking_email": "null",
                "roistat_emailtracking_emails": "null",
                "carrotquest_closed_part_id": "1532310422571453465",
                "_ga_5Z0GQXKR5Q": "GS1.1.1694773629.6.1.1694773658.31.0.0",
                "roistat_cookies_to_resave": "roistat_ab%2Croistat_ab_submit%2Croistat_visit%2Croistat_call_tracking%2Croistat_emailtracking_email%2Croistat_emailtracking_tracking_email%2Croistat_emailtracking_emails%2Cvisitor_uid",
                "carrotquest_hide_all_unread_popups": "true",
                "_ym_visorc": "w",
                "carrotquest_session": "8weig5rbkihlig66jm7vfisdfimytqte",
                "carrotquest_session_started": "1"
            },
            "drvorobjev": {
                "QueueTable_state": "0",
                "DtmfListTable_state": "0",
                "DirectionTable_state": "0",
                "HotDeskTable_state": "1",
                "CallOutListTable_state": "0",
                "TreeTable_out_state": "1",
                "lastTree": "2079255",
                "OutSipClientTable_state": "0",
                "OurSipClientTable_state": "0",
                "TreeTable_in_state": "1",
                "InSipClientTable_state": "0",
                "_ym_uid": "1683784624150200334",
                "_ym_d": "1683784624",
                "hcode": "6d62c926bd64a47956d081a7c7cd73b1",
                "paddos_3MUXg": "1",
                "tmr_lvid": "893b1c01cf41d59f10b751b521563919",
                "tmr_lvidTS": "1686289487442",
                "roistat_first_visit": "135141",
                "carrotquest_device_guid": "5ebe8c89-2f52-4609-969a-5dca24327d26",
                "carrotquest_uid": "1461140221205679482",
                "carrotquest_auth_token": "user.1461140221205679482.55906-5369ff2e5cfd9d6a816c5160eb.4bd313f331ce8f373b76005386c0a058bbf912bd342298a0",
                "___dc": "ad624182-88e7-407c-a78e-e65e678af8db",
                "_ga_5Z0GQXKR5Q": "GS1.1.1690803833.4.1.1690805989.14.0.0",
                "_ga": "GA1.2.1801676173.1683784624",
                "user": "ZGVmNTAyMDBiZTU1YmNjMDg5MmQ0YjMzNzU2OWEwOWVkZjU5NDk1YmIzM2EyYmRkZTQ2NDk2NWY5OGM2ZjA0MmU3OGIwZWNmMmFlNjBiYTcxMzlmNjEwMmNjNzUyNjA0OGVjMTMwZmIxY2M1MGUzMGI4ODVlYTU2ZmE3Njc2ZWY2YWJiOWRhYWVlYzYyMGIyZGJkYzAyZGJjMDRkMjFiODAwMWVhZmViZjU4NmU5OWUzNWQ2MTQwNmQ4ZjUxY2Zm",
                "PHPSESSID": "9fr4o382vli7kqgnm7vfclujd1",
                "_ym_isad": "2",
                "_ym_visorc": "w"
            }
        }
        return Config().sipuni_cookies.get(self.__branch)
        # return cookies.get(self.__branch)

    def get_headers(self, autocall_id):
        return {
            'authority': 'sipuni.com',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'en-US,en;q=0.9',
            'referer': f'https://sipuni.com/ru_RU/settings/autocall/numbers/{autocall_id}',
            'sec-ch-ua': '"Chromium";v="116", "Not)A;Brand";v="24", "Google Chrome";v="116"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
        }

    def __start_autocalls(self, processor):
        from app import db
        from app.main.autocall.constants import API_CLIENT, AUTOCALL_NUMBER
        branch_config = self.__sipuni_branch_config
        if not branch_config:
            processor.log.add(text=f'no config for {self.__branch}')
            return
        autocall_ids = list(branch_config.get('autocall').keys())
        amo_client = API_CLIENT.get(self.__branch)()
        # читаем номера из БД и добавляем в автообзвон те, которые удовлетворяют условию
        autocall_model = AUTOCALL_NUMBER.get(self.__branch)
        all_numbers = autocall_model.query.all()
        branch_config = self.__sipuni_branch_config
        sipuni_client = Sipuni(sipuni_config=branch_config)
        numbers_added = []
        for line in all_numbers:
            db.session.add(line)
            db.session.refresh(line)
            # с момента last_call_timestamp должно пройти не менее 23 часов (если звонок не первый)
            if line.last_call_timestamp + 23 * 3600 > time.time() and line.calls > 0:
                continue
            # конфиг SIPUNI существует
            autocall_config = (branch_config.get('autocall') or {}).get(str(line.autocall_id))
            if not autocall_config:
                processor.log.add(text=f'config not found {line.autocall_id} number {line.number}')
                continue
            # лимит звонков еще не достигнут
            if line.calls >= int(autocall_config.get('calls_limit')):
                db.session.delete(line)
                continue
            schedule = autocall_config.get('schedule')
            # существует расписание для данного автообзвона
            if not schedule:
                continue
            # лид все еще находится в воронке автообзвона
            lead = amo_client.get_lead_by_id(lead_id=line.lead_id)
            pipeline_id, status_id = lead.get('pipeline_id'), lead.get('status_id')
            if not pipeline_id or not status_id:
                db.session.delete(line)
                db.session.commit()
                time.sleep(0.25)
                continue
            if autocall_config.get('pipeline_id') != str(pipeline_id) \
                    or autocall_config.get('status_id') != str(status_id):
                # лид был перемещен, удаляем номер из БД автообзвона
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
            for period in weekday_schedule:
                _from, _to = period.split(' - ')
                _from = self.__build_datetime_from_timestring(timestring=_from)
                _to = self.__build_datetime_from_timestring(timestring=_to)
                if _from <= curr_dt <= _to:
                    break
            else:
                continue
            numbers_added.append({'number': line.number, 'autocall_id': line.autocall_id})
        # запускаем все автообзвоны Sipuni
        if not numbers_added:
            return
        # удаляем все номера из всех автообзвонов Sipuni (через браузер)
        for autocall_id in autocall_ids:
            response = requests.get(
                url=f'https://sipuni.com/ru_RU/settings/autocall/delete_numbers_all/{autocall_id}',
                cookies=self.get_cookies(),
                headers=self.get_headers(autocall_id=autocall_id)
            )
            time.sleep(1)
        for item in numbers_added:
            sipuni_client.add_number_to_autocall(number=item['number'], autocall_id=item['autocall_id'])
            time.sleep(0.25)
        for autocall_id in autocall_ids:
            try:
                response = requests.get(
                    url=f'https://sipuni.com/ru_RU/settings/autocall/start/{autocall_id}',
                    cookies=self.get_cookies(),
                    headers=self.get_headers(autocall_id=autocall_id)
                )
                print('autocall start response', response.status_code)
            except Exception as exc:
                processor.log.add(text=f'autocall error: {exc}')
            time.sleep(1)
        db.session.close()

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

    def __get_autocall_number_entity(self, number: str):
        """ Перебирает таблицы БД в поисках экземпляра номера автодозвона

        Args:
            number: номер, который следует найти в БД

        Returns:
            экземпляр номера автодозвона из БД
        """
        from app.main.autocall.constants import AUTOCALL_NUMBER
        for autocall_model in AUTOCALL_NUMBER.values():
            number_entity = autocall_model.query.filter_by(number=number).first()
            if number_entity:
                # по найденному номеру определяем филиал
                self.__branch = number_entity.branch
                return number_entity
        else:
            return None

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
