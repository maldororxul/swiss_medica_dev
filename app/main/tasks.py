""" Фоновые задачи: загрузка данных с источников, обновление pivot data и проч. """
__author__ = 'ke.mizonov'
import gc
from datetime import datetime, timedelta
from flask import Flask
from app.main.controllers import SYNC_CONTROLLER
from app.main.processors import DATA_PROCESSOR
from app.main.utils import DateTimeEncoder

is_running = {
    'get_data_from_amo': {'sm': False, 'cdv': False},
    'update_pivot_data': {'sm': False, 'cdv': False},
}


class SchedulerTask:

    def get_data_from_amo(self, app: Flask, branch: str, starting_date: datetime):
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
    def __get_data_from_amo(app: Flask, branch: str, starting_date: datetime, key: str):
        interval = 60
        empty_steps_limit = 20
        empty_steps = 0
        date_from = starting_date - timedelta(minutes=interval)
        date_to = starting_date
        processor = DATA_PROCESSOR.get(branch)()
        with app.app_context():
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
                repeated_iteration = "" if has_new else f" :: R{empty_steps}"
                msg = f'reading Amo data :: {df} - {dt}{repeated_iteration}'
                # запись лога в БД
                processor.log.add(text=msg, log_type=1)
                if empty_steps_limit == empty_steps:
                    processor.log.add(
                        text='reading Amo data :: iteration finished',
                        log_type=1
                    )
                    is_running.get(key)[branch] = False
                    return
                date_from = date_from - timedelta(minutes=interval)
                date_to = date_to - timedelta(minutes=interval)

    @staticmethod
    def __update_pivot_data(app: Flask, branch: str, key: str):
        interval = 60
        empty_steps_limit = 20
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
                for line in data_processor.update(date_from=date_from, date_to=date_to):
                    item = {key.split('_(')[0]: value for key, value in line.items()}
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
                print(total, not_updated)
                if total == not_updated:
                    empty_steps += 1
                if empty_steps_limit == empty_steps:
                    is_running.get(key)[branch] = False
                    data_processor.log.add(
                        text='updating pivot data :: iteration finished',
                        log_type=1
                    )
                    return
                df = date_from.replace(microsecond=0)
                r = f' R{empty_steps}' if empty_steps > 0 else ''
                data_processor.log.add(
                    text=f'updating pivot data :: {df.date()} {df.time()} - {date_to.replace(microsecond=0).time()}{r}',
                    log_type=1
                )
                date_from = date_from - timedelta(minutes=interval)
                date_to = date_to - timedelta(minutes=interval)
