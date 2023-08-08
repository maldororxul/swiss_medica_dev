""" Фоновые задачи: загрузка данных с источников, обновление pivot data и проч. """
__author__ = 'ke.mizonov'
import json
import time
from datetime import datetime, timedelta, date
from flask import Flask, current_app
from app import socketio
from app.main.controllers import SYNC_CONTROLLER
from app.main.processors import DATA_PROCESSOR

is_running = False


class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()


def get_data_from_amo(app: Flask, branch: str, starting_date: datetime):

    global is_running
    if is_running:
        return
    is_running = True

    interval = 60
    empty_steps_limit = 20
    empty_steps = 0
    date_from = starting_date - timedelta(minutes=interval)
    date_to = starting_date
    processor = DATA_PROCESSOR.get(branch)()
    with app.app_context():
        while True:
            controller = SYNC_CONTROLLER.get(branch)(date_from=date_from, date_to=date_to)
            has_new = controller.run()
            if not has_new:
                empty_steps += 1
            else:
                empty_steps = 0
            df = date_from.strftime("%Y-%m-%d %H:%M:%S")
            dt = date_to.strftime("%H:%M:%S")
            repeated_iteration = "" if has_new else f" :: R{empty_steps}"
            msg = f'reading data :: {df} - {dt}{repeated_iteration}'
            # запись лога в БД
            processor.log.add(text=msg, log_type=1)
            if empty_steps_limit == empty_steps:
                is_running = False
                break
            date_from = date_from - timedelta(minutes=interval)
            date_to = date_to - timedelta(minutes=interval)


def sync_generator(data_processor, date_from, date_to):
    for line in data_processor.update(date_from=date_from, date_to=date_to) or []:
        item = {key.split('_(')[0]: value for key, value in line.items()}
        yield {
            'id': line['id'],
            'created_at': line['created_at_ts'],
            'updated_at': line['updated_at_ts'],
            'data': json.dumps(item, cls=DateTimeEncoder)
        }


def update_pivot_data(app: Flask, branch: str):
    interval = 10
    empty_steps_limit = 20
    empty_steps = 0
    # starting_date = datetime(2023, 5, 26, 15, 0, 0)
    starting_date = datetime.now()
    date_from = starting_date - timedelta(minutes=interval)
    date_to = starting_date
    data_processor = DATA_PROCESSOR.get(branch)()
    with app.app_context():
        controller = SYNC_CONTROLLER.get(branch)()
        while True:
            not_updated = 0
            total = 0
            for line in data_processor.update(date_from=date_from, date_to=date_to) or []:
                item = {key.split('_(')[0]: value for key, value in line.items()}
                print('updating', item)
                if not controller.sync_record({
                    'id': line['id'],
                    'created_at': line['created_at_ts'],
                    'updated_at': line['updated_at_ts'],
                    'data': json.dumps(item, cls=DateTimeEncoder)
                }):
                    print('not updated')
                    not_updated += 1
                total += 1
            if total == not_updated:
                empty_steps += 1
            data_processor.log.add(text=f'updating pivot data :: {date_from} :: {date_to}', log_type=1)
            if empty_steps_limit == empty_steps:
                break
            else:
                empty_steps = 0
            time.sleep(10)
            date_from = date_from - timedelta(minutes=interval)
            date_to = date_to - timedelta(minutes=interval)
