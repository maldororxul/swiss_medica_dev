""" Фоновые задачи: загрузка данных с источников, обновление pivot data и проч. """
__author__ = 'ke.mizonov'
import gc
import random
import time
from datetime import datetime, timedelta
from typing import Optional, List, Tuple

from flask import Flask
from flask_sqlalchemy.session import Session
from sqlalchemy import func

from app import db
from app.main.controllers import SYNC_CONTROLLER
from app.main.processors import DATA_PROCESSOR
from app.main.utils import DateTimeEncoder
from app.models.contact import SMContact, CDVContact
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
                print(model, query_result, datetime.fromtimestamp(query_result))
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
        empty_steps_limit = 10
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
                has_new = controller.run(date_from=date_from, date_to=date_to)
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
    def __update_pivot_data(app: Flask, branch: str, key: str):
        interval = 60
        empty_steps_limit = 0
        empty_steps = 0
        # starting_date = datetime(2023, 8, 3, 15, 0, 0)
        starting_date = datetime.now()
        date_from = starting_date - timedelta(minutes=interval)
        date_to = starting_date
        data_processor = DATA_PROCESSOR.get(branch)()
        with app.app_context():
            data_processor.log.add(
                text='updating pivot data :: iteration started',
                log_type=1
            )
            controller = SYNC_CONTROLLER.get(branch)()
            while True:
                not_updated = 0
                total = 0

                # todo tmp - образец работы с JSON-конвертацией для RawLeadData

                for line in data_processor.update(date_from=date_from, date_to=date_to):
                    item = {key.split('_(')[0]: value for key, value in line.items()}

                    # todo это надо переписать!

                    if not controller.sync_record(
                        record={
                            'id': line['id'],
                            'created_at': line['created_at_ts'],
                            'updated_at': line['updated_at_ts'],
                            'data': DateTimeEncoder.encode(item)
                        },
                        table_name='Data'
                    ):
                        not_updated += 1
                    total += 1
                if total == not_updated:
                    empty_steps += 1
                if empty_steps_limit > 0 and empty_steps_limit == empty_steps:
                    is_running.get(key)[branch] = False
                    data_processor.log.add(
                        text='updating pivot data :: iteration finished',
                        log_type=1
                    )
                    return
                df = date_from.strftime("%Y-%m-%d %H:%M:%S")
                dt = date_to.strftime("%H:%M:%S")
                data_processor.log.add(
                    text=f'updating pivot data :: {df} - {dt} :: R{empty_steps}',
                    log_type=1
                )
                date_from = date_from - timedelta(minutes=interval)
                date_to = date_to - timedelta(minutes=interval)
                time.sleep(random.uniform(0.01, 1.5))
