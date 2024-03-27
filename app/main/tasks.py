""" Фоновые задачи: загрузка данных с источников, обновление pivot data и проч. """
__author__ = 'ke.mizonov'
import gc
import random
import time
from datetime import datetime, timedelta
from typing import Optional, List, Tuple, Dict
from pympler import asizeof
from memory_profiler import memory_usage
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
from config import Config

is_running = {
    'get_data_from_amo': {'sm': False, 'cdv': False},
    'update_pivot_data': {'sm': False, 'cdv': False},
}


class SchedulerTask:

    def get_data_from_amo(self, app: Flask, branch: str, starting_date: Optional[datetime] = None):
        key = 'get_data_from_amo'
        if self.__is_running(key=key, branch=branch):
            return
        if not starting_date:
            date_str = Config().worker.get(key).get('starting_date')
            starting_date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S') if date_str else None
        self.__get_data_from_amo(
            app=app,
            branch=branch,
            starting_date=starting_date,
            key=key,
            time_started=time.time()
        )
        gc.collect()

    def update_pivot_data(self, app: Flask, branch: str):
        key = 'update_pivot_data'
        if self.__is_running(key=key, branch=branch):
            return
        self.__update_pivot_data(app=app, branch=branch, key=key, time_started=time.time())
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

        # Возвращаем самый поздний timestamp из всех самых ранних (!)
        earliest_timestamp: int = max(earliest_dates) if earliest_dates else None

        # Если нужно, конвертируем timestamp в datetime объект для удобства
        if earliest_timestamp is not None:
            return datetime.fromtimestamp(earliest_timestamp) + timedelta(minutes=1)
        else:
            return datetime.now()

    def __get_data_from_amo(
        self,
        app: Flask,
        branch: str,
        key: str,
        time_started: float,
        starting_date: Optional[datetime] = None
    ):
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
        # задаем предельную длительность итерации в секундах и фиксируем время начала процесса
        iteration_duration = 3600
        processor = DATA_PROCESSOR.get(branch)()
        with app.app_context():
            session = db.session
            starting_date = starting_date or self.__get_earliest_date(
                session=session,
                models_with_columns=models_with_columns
            )
            config = Config().worker.get('get_data_from_amo')
            interval = config['interval']
            date_from = starting_date - timedelta(minutes=interval)
            date_to = starting_date
            df = date_from.strftime("%Y-%m-%d %H:%M:%S")
            dt = date_to.strftime("%H:%M:%S")
            processor.log.add(
                text=f'reading Amo data :: {df} - {dt} :: iteration started',
                log_type=1
            )
            controller = SYNC_CONTROLLER.get(branch)()
            while True:
                # если достигнуто предельное время выполнения операции, завершаем процесс
                if time.time() - time_started >= iteration_duration:
                    is_running.get(key)[branch] = False
                    return
                config = Config().worker.get('get_data_from_amo')
                interval = config['interval']
                empty_steps_limit = config['empty_steps_limit']
                has_new = False
                print('get_data_from_amo', date_from, date_to)
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
        self.__get_data_from_amo(
            app=app,
            branch=branch,
            starting_date=datetime.now(),
            key=key,
            time_started=time_started
        )

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

    def __update_pivot_data(
        self,
        app: Flask,
        branch: str,
        key: str,
        time_started: float,
        starting_date: Optional[datetime] = None
    ):
        if branch == 'sm':
            models_with_columns = [(SMData, 'updated_at')]
        elif branch == 'cdv':
            models_with_columns = [(CDVData, 'updated_at')]
        else:
            is_running.get(key)[branch] = False
            return
        data_processor = DATA_PROCESSOR.get(branch)()
        empty_steps = 0
        # задаем предельную длительность итерации в секундах и фиксируем время начала процесса
        iteration_duration = 3600
        with app.app_context():
            session = db.session
            starting_date = starting_date or self.__get_earliest_date(
                session=session,
                models_with_columns=models_with_columns
            )
            config = Config().worker.get('update_pivot_data')
            interval = config['interval']
            date_from = starting_date - timedelta(minutes=interval)
            date_to = starting_date
            df = date_from.strftime("%Y-%m-%d %H:%M:%S")
            dt = date_to.strftime("%H:%M:%S")
            data_processor.log.add(
                text=f'updating pivot data :: {df} - {dt} :: iteration started',
                log_type=1
            )
            controller = SYNC_CONTROLLER.get(branch)()
            pre_data = data_processor._pre_build()
            while True:

                # !! профилирование !!
                # mem_usage_before = memory_usage(-1, interval=0.1, timeout=1)

                # если достигнуто предельное время выполнения операции, завершаем процесс
                if time.time() - time_started >= iteration_duration:
                    is_running.get(key)[branch] = False
                    return
                config = Config().worker.get('update_pivot_data')
                interval = config['interval']
                empty_steps_limit = config['empty_steps_limit']
                batch_size = config['batch_size']
                batch_data = []
                has_new = False
                # используем генератор для получения обновленных данных
                for line in data_processor.update(date_from=date_from, date_to=date_to, pre_data=pre_data):
                    batch_data.append(self.__build_pivot_data_item(line=line))
                    if len(batch_data) >= batch_size:
                        # пакетная синхронизация
                        if controller.sync_records(records=batch_data, table_name='Data'):
                            has_new = True
                            empty_steps = 0
                        batch_data.clear()
                # убеждаемся, что "хвост" данных тоже будет синхронизирован
                if batch_data:
                    if controller.sync_records(records=batch_data, table_name='Data'):
                        has_new = True
                        empty_steps = 0
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

                # !! профилирование !!
                # mem_usage_after = memory_usage(-1, interval=0.1, timeout=1)
                # data_processor.log.add(
                #     text=f'updating pivot data\n'
                #          f'batch_data: {round(asizeof.asizeof(batch_data) / 1024 / 1024, 2)} Mb\n'
                #          f'total: {round(mem_usage_after[-1] - mem_usage_before[-1], 2)} Mb',
                #     log_type=1
                # )

        del batch_data
        self.__update_pivot_data(
            app=app,
            branch=branch,
            key=key,
            starting_date=datetime.now(),
            time_started=time_started
        )
