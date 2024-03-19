""" Фоновые задачи: загрузка данных с источников, обновление pivot data и проч. """
__author__ = 'ke.mizonov'
import gc
import random
import time
from datetime import datetime, timedelta
from typing import Optional, List, Tuple, Dict

from flask import Flask
from flask_sqlalchemy.session import Session
from sqlalchemy import func

from app import db
from app.main.controllers import SYNC_CONTROLLER
from app.main.processors import DATA_PROCESSOR
from app.main.utils import DateTimeEncoder
from app.models.contact import SMContact, CDVContact
from app.models.data import SMData, CDVData
from app.models.event import SMEvent, CDVEvent
from app.models.lead import SMLead, CDVLead
from app.models.note import SMNote, CDVNote
from app.models.task import SMTask, CDVTask

is_running = {
    'get_data_from_amo': {'sm': False, 'cdv': False},
    'update_pivot_data': {'sm': False, 'cdv': False},
}


class SchedulerTask:

    def get_data_from_amo(self, app: Flask, branch: str, starting_date: Optional[datetime] = None):
        key = 'get_data_from_amo'
        if self.__is_running(key=key, branch=branch):
            return
        self.__get_data_from_amo(app=app, branch=branch, starting_date=starting_date, key=key)
        gc.collect()

    def update_pivot_data(self, app: Flask, branch: str):
        key = 'update_pivot_data'
        if self.__is_running(key=key, branch=branch):
            return
        self.__update_pivot_data(app=app, branch=branch, key=key)
        gc.collect()

    @staticmethod
    def __is_running(key: str, branch: str) -> bool:
        _is_running = is_running.get(key).get(branch)
        if _is_running:
            return True
        is_running.get(key)[branch] = True
        return False

    @staticmethod
    def __get_earliest_date(session: Session, models_with_columns: List[Tuple[db.Model, str]]) -> datetime:
        earliest_dates = []

        for model, column_name in models_with_columns:
            # Получаем минимальное значение timestamp для каждой указанной колонки каждой модели
            query_result = session.query(func.min(getattr(model, column_name))).scalar()
            if query_result:
                earliest_dates.append(query_result)

        # Возвращаем самый ранний timestamp из всех найденных
        earliest_timestamp: int = min(earliest_dates) if earliest_dates else None

        # Если нужно, конвертируем timestamp в datetime объект для удобства
        if earliest_timestamp is not None:
            return datetime.fromtimestamp(earliest_timestamp)
        else:
            return datetime.now()

    def __get_data_from_amo(self, app: Flask, branch: str, key: str, starting_date: Optional[datetime] = None):
        interval = 60
        empty_steps_limit = 60
        empty_steps = 0
        if branch == 'sm':
            models_with_columns = [
                (SMContact, 'updated_at'),
                (SMEvent, 'created_at'),
                (SMNote, 'updated_at'),
                (SMTask, 'updated_at'),
                (SMLead, 'updated_at'),
            ]
        elif branch == 'cdv':
            models_with_columns = [
                (CDVContact, 'updated_at'),
                (CDVEvent, 'created_at'),
                (CDVNote, 'updated_at'),
                (CDVTask, 'updated_at'),
                (CDVLead, 'updated_at'),
            ]
        else:
            is_running.get(key)[branch] = False
            return
        processor = DATA_PROCESSOR.get(branch)()
        with app.app_context():
            session = db.session
            starting_date = starting_date or self.__get_earliest_date(
                session=session,
                models_with_columns=models_with_columns
            )
            date_from = starting_date - timedelta(minutes=interval)
            date_to = starting_date
            processor.log.add(
                text='reading Amo data :: iteration started',
                log_type=1
            )
            controller = SYNC_CONTROLLER.get(branch)()
            while True:
                has_new = False
                if controller.run(date_from=date_from, date_to=date_to):
                    has_new = True
                    empty_steps = 0  # Обнуляем счетчик, если были изменения
                if not has_new:
                    empty_steps += 1
                df = date_from.strftime("%Y-%m-%d %H:%M:%S")
                dt = date_to.strftime("%H:%M:%S")
                # запись лога в БД
                processor.log.add(text=f'reading Amo data :: {df} - {dt} :: R{empty_steps}', log_type=1)
                if empty_steps_limit > 0 and empty_steps_limit == empty_steps:
                    processor.log.add(
                        text='reading Amo data :: iteration finished',
                        log_type=1
                    )
                    break
                date_from = date_from - timedelta(minutes=interval)
                date_to = date_to - timedelta(minutes=interval)
                time.sleep(random.uniform(0.01, 1.5))
        self.__get_data_from_amo(app=app, branch=branch, starting_date=datetime.now(), key=key)

    @staticmethod
    def __build_pivot_data_item(line: Dict) -> Dict:
        item = {key.split('_(')[0]: value for key, value in line.items() if key not in ('contacts', 'phone')}
        return {
            'id': line['id'],
            'created_at': line['created_at_ts'],
            'updated_at': line['updated_at_ts'],
            'data': DateTimeEncoder.encode(item),
            'contacts': DateTimeEncoder.encode(line.pop('contacts')),
            'phone': DateTimeEncoder.encode(line.pop('phone'))
        }
    #
    # def _init_sipuni_processor(self):
    #     from modules.sipuni.sipuni_processsor.processor import SMSipuniProcessor
    #     return SMSipuniProcessor()
    #
    # def _build_calls_data(self, date_from: datetime, date_to: datetime = datetime.now()) -> Dict:
    #     """ Строит словарь с историей звонков Sipuni
    #
    #     Args:
    #         date_from: дата с
    #         date_to: дата по
    #
    #     Returns:
    #         словарь с историей звонков Sipuni вида {
    #             phone_number: {'calls': [], 'tag': ..., }
    #         }
    #     """
    #     sipuni_processor = self._init_sipuni_processor()
    #     # вытаскиваем "сырые" звонки из Sipuni
    #     raw_calls = sipuni_processor.get_calls(date_from=date_from, date_to=date_to)
    #     # строим карту тегов на основе онлайн-таблицы
    #     tags_map = sipuni_processor.build_tags_map()
    #     # строим словарь звонков - ВАЖНО! ключ - это урезанный по VALUABLE_NUMBER_LENGTH номер!
    #     # {phone_number: {'calls': [], 'tag': ..., }}
    #     calls_dict = {}
    #     for item in raw_calls:
    #         is_income = item['Тип'] == 'Входящий'
    #         customer_number = clear_phone(item['Откуда'] if is_income else item['Куда'])
    #         if not customer_number:
    #             continue
    #         our_internal_number = item['Куда'] if is_income else item['Откуда']
    #         call_dt = datetime.strptime(item['Время'], "%d.%m.%Y %H:%M:%S").replace(tzinfo=None) - \
    #                   timedelta(hours=sipuni_processor.minus_msk_delta)
    #         item['call_dt'] = call_dt
    #         item['our_internal_number'] = our_internal_number
    #         tag = sipuni_processor.get_tag_by_phone(
    #                 tags_map=tags_map,
    #                 phone=our_internal_number,
    #                 call_dt=call_dt
    #             )
    #         if len(customer_number) < VALUABLE_NUMBER_LENGTH:
    #             continue
    #         # customer_number = customer_number[-VALUABLE_NUMBER_LENGTH:]
    #         if customer_number not in calls_dict:
    #             calls_dict[customer_number] = {'calls': [], 'tag': tag}
    #         calls_dict[customer_number]['calls'].append(item)
    #     # print(get_size_of_object(calls_dict))
    #     return calls_dict
    #
    # def __get_sipuni_data(self, date_from: datetime, date_to: datetime):
    #     """ Подмешивает к лидам информацию о звонках https://app.clickup.com/t/8692zcw31
    #
    #     Args:
    #         leads: предварительно обработанный список сделок
    #         date_from: дата с
    #         date_to: дата по
    #     """
    #     calls_dict = self._build_calls_data(date_from=date_from, date_to=date_to)
    #     for lead in leads:
    #         calls, tags = [], []
    #         call_ids = []
    #         for phone in self._get_lead_phones(lead) or []:
    #             if not phone or len(phone) < VALUABLE_NUMBER_LENGTH:
    #                 continue
    #             # словарь вида {'calls': [], 'tag': ..., }
    #             call_dict = calls_dict.get(phone) or {}
    #             for _call in call_dict.get('calls') or []:
    #                 _id = _call['ID записи']
    #                 if _id in call_ids:
    #                     continue
    #                 call_ids.append(_id)
    #                 calls.append(_call)
    #             tag = call_dict.get('tag')
    #             if tag and tag not in tags:
    #                 tags.append(tag)
    #             # фиксируем, что для текущего лида и номера звонки были
    #             # if call_dict.get('calls') and phone not in numbers_we_called:
    #             #     numbers_we_called.append(phone)
    #         # звонков не было
    #         if not calls:
    #             lead[Lead.HasSipuniCalls.Key] = ''
    #             lead[Lead.FirstCallType.Key] = ''
    #             # lead[Lead.FirstCallStatus.Key] = ''
    #             lead[Lead.GoogleTableTag.Key] = ''
    #             lead[Lead.HasAnsweredSipuniCalls.Key] = ''
    #             lead[Lead.HasLongSipuniCalls.Key] = ''
    #             lead[Lead.SipuniCallsQuantity.Key] = ''
    #             lead[Lead.SipuniCallsQuantity7.Key] = ''
    #             continue
    #         # звонки были
    #         lead[Lead.HasSipuniCalls.Key] = 1
    #         # т.к. звонки могли поступать на разные номера, требуется сортировка
    #         calls = map(lambda _call: DateTimeUtils.sipuni_dt_from_str(
    #             item=_call,
    #             target_timezone=self.target_timezone
    #         ),
    #                     calls
    #                     )
    #         calls = sorted(calls, key=lambda _call: _call['Время'])
    #         lead[Lead.FirstCallType.Key] = calls[0]['Тип']
    #         # lead[Lead.FirstCallStatus.Key] = calls[0]['Статус']
    #         lead[Lead.GoogleTableTag.Key] = ', '.join(tags) if tags else ''
    #         for _call in calls:
    #             if _call['Статус'] == 'Отвечен':
    #                 lead[Lead.HasAnsweredSipuniCalls.Key] = 1
    #                 break
    #         for _call in calls:
    #             duration = _call['Длительность разговора']
    #             if not duration:
    #                 continue
    #             if int(duration) >= 5 * 60:
    #                 lead[Lead.HasLongSipuniCalls.Key] = 1
    #                 break
    #         lead[Lead.SipuniCallsQuantity.Key] = len(calls)
    #         quantity_7_days = 0
    #         for _call in calls:
    #             if _call['Время'].date() > lead['created_at'] + timedelta(days=7):
    #                 continue
    #             quantity_7_days += 1
    #         lead[Lead.SipuniCallsQuantity7.Key] = quantity_7_days if quantity_7_days > 0 else ''
    #     # создаем виртуальные лиды
    #     # еще раз вытаскиваем данные по звонкам, но только за последние 2 недели от date_to
    #     calls_dict = self._build_calls_data(date_from=date_to - timedelta(days=14), date_to=date_to)
    #     # вычитываем все лиды, т.к. в них содержатся контакты
    #     numbers_we_called = []
    #     all_leads = self._get_leads(
    #         date_from=datetime(2000, 1, 1),
    #         date_to=date_to,
    #         worker=worker,
    #         mixin_notes=False,
    #         forced=True
    #     )
    #     for lead in all_leads:
    #         # if lead['id'] == 24554389:
    #         #     print(lead)
    #         for phone in self._get_lead_phones(lead):
    #             if not phone:
    #                 continue
    #             if phone not in numbers_we_called:
    #                 numbers_we_called.append(phone)
    #     numbers_we_called_serbian = [f"381{x}" for x in numbers_we_called if len(x) <= 9]
    #     numbers_we_called_sw = [f"43{x}" for x in numbers_we_called if len(x) <= 9]
    #     numbers_we_called_serbian2 = [f"381{x.lstrip('70')}" for x in numbers_we_called]
    #     numbers_we_called_serbian3 = [x.lstrip('70') for x in numbers_we_called]
    #     numbers_we_called_serbian4 = [x.lstrip('7') for x in numbers_we_called]
    #     numbers_we_called_8 = [x[-VALUABLE_NUMBER_LENGTH:] for x in numbers_we_called]
    #     # лиды, зарегистрированные на этапе создания в RawLeadsData в Heroku
    #     raw_leads = [
    #         str(x['data'])
    #         for x in self.db_client().get_raw_leads(
    #             dt_from=datetime(2000, 1, 1),
    #             dt_to=date_to
    #         )
    #     ]
    #     # пробегаемся по звонкам - если номера нет в числе numbers_we_called - создаем заглушку
    #     sipuni_processor = self._init_sipuni_processor()
    #     calls_without_leads = []
    #     total = len(calls_dict.keys())
    #     for num, (phone, call_data) in enumerate(calls_dict.items(), 1):
    #         worker.emit({'msg': f'Processing calls without leads... {num} of {total}', 'num': num, 'total': total})
    #         if phone in numbers_we_called \
    #                 or phone.lstrip('222') in numbers_we_called \
    #                 or phone.lstrip('111') in numbers_we_called \
    #                 or phone.lstrip('333') in numbers_we_called \
    #                 or phone.lstrip('7').lstrip('0') in numbers_we_called \
    #                 or f"381{phone}" in numbers_we_called \
    #                 or f"43{phone}" in numbers_we_called \
    #                 or phone in numbers_we_called_sw \
    #                 or phone in numbers_we_called_serbian \
    #                 or phone in numbers_we_called_serbian2 \
    #                 or phone in numbers_we_called_serbian3 \
    #                 or phone in numbers_we_called_serbian4 \
    #                 or (len(phone) >= VALUABLE_NUMBER_LENGTH and phone[
    #                                                              -VALUABLE_NUMBER_LENGTH:] in numbers_we_called_8):
    #             continue
    #         long_calls = []
    #         for _call in call_data['calls']:
    #             duration = _call['Длительность разговора']
    #             if duration and int(duration) >= 5 * 60:
    #                 long_calls.append(_call)
    #                 sipuni_processor.get_record(id_=_call['ID записи'])

    def __update_pivot_data(self, app: Flask, branch: str, key: str, starting_date: Optional[datetime] = None):
        interval = 10
        empty_steps_limit = 400
        empty_steps = 0
        batch_size = 10
        data_processor = DATA_PROCESSOR.get(branch)()
        if branch == 'sm':
            models_with_columns = [(SMData, 'updated_at')]
        elif branch == 'cdv':
            models_with_columns = [(CDVData, 'updated_at')]
        else:
            is_running.get(key)[branch] = False
            return
        with app.app_context():
            session = db.session
            data_processor.log.add(
                text='updating pivot data :: iteration started',
                log_type=1
            )
            starting_date = starting_date or self.__get_earliest_date(
                session=session,
                models_with_columns=models_with_columns
            )
            date_from = starting_date - timedelta(minutes=interval)
            date_to = starting_date
            controller = SYNC_CONTROLLER.get(branch)()
            while True:
                batch_data = []
                has_new = False
                # используем генератор для получения обновленных данных
                for line in data_processor.update(date_from=date_from, date_to=date_to):
                    batch_data.append(self.__build_pivot_data_item(line=line))
                    if len(batch_data) >= batch_size:
                        # пакетная синхронизация
                        if controller.sync_records(records=batch_data, table_name='Data'):
                            has_new = True
                            empty_steps = 0  # Обнуляем счетчик, если были изменения
                        batch_data.clear()
                        del line
                # убеждаемся, что "хвост" данных тоже будет синхронизирован
                if batch_data:
                    if controller.sync_records(records=batch_data, table_name='Data'):
                        has_new = True
                        empty_steps = 0  # Обнуляем счетчик, если были изменения
                    batch_data.clear()
                # проверяем условие выхода из цикла
                if not has_new:
                    empty_steps += 1
                if empty_steps_limit > 0 and empty_steps_limit == empty_steps:
                    data_processor.log.add(
                        text='updating pivot data :: iteration finished',
                        log_type=1
                    )
                    break
                df = date_from.strftime("%Y-%m-%d %H:%M:%S")
                dt = date_to.strftime("%H:%M:%S")
                data_processor.log.add(
                    text=f'updating pivot data :: {df} - {dt} :: R{empty_steps}',
                    log_type=1
                )
                date_from = date_from - timedelta(minutes=interval)
                date_to = date_to - timedelta(minutes=interval)
                time.sleep(random.uniform(0.01, 1.5))
                gc.collect()
        del batch_data
        self.__update_pivot_data(app=app, branch=branch, key=key, starting_date=datetime.now())
