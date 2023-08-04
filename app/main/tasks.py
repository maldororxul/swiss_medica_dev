""" Фоновые задачи: загрузка данных с источников, обновление pivot data и проч. """
__author__ = 'ke.mizonov'
import json
from datetime import datetime, timedelta, date
from flask import Flask
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
    interval = 5
    empty_steps_limit = 100
    empty_steps = 0
    # starting_date = datetime(2023, 5, 26, 15, 0, 0)
    starting_date = datetime.now()
    date_from = starting_date - timedelta(minutes=interval)
    date_to = starting_date
    data_processor_class = DATA_PROCESSOR.get(branch)
    data_processor = data_processor_class()
    with app.app_context():
        controller = SYNC_CONTROLLER.get(branch)()
        while True:
            for item in sync_generator(
                data_processor=data_processor,
                date_from=date_from,
                date_to=date_to
            ):
                has_new = controller.sync_record(item, table_name='Data')
                if has_new:
                    empty_steps += 1
        #     # collection = []
        #     for line in data_processor.update(date_from=date_from, date_to=date_to) or []:
        #         item = {key.split('_(')[0]: value for key, value in line.items()}
        #         yield controller.sync_record({
        #             'id': line['id'],
        #             'created_at': line['created_at_ts'],
        #             'updated_at': line['updated_at_ts'],
        #             'data': json.dumps(item, cls=DateTimeEncoder)
        #         })
                # collection.append({
                #     'id': line['id'],
                #     'created_at': line['created_at_ts'],
                #     'updated_at': line['updated_at_ts'],
                #     'data': json.dumps(item, cls=DateTimeEncoder)
                # })
            # has_new = controller.update_data(collection=collection, date_from=date_from, date_to=date_to)
            # del collection
            # with app.app_context():
            data_processor.log.add(f'updating pivot data :: {date_from} :: {date_to}')
            # if not has_new:
            #     empty_steps += 1
            # else:
            #     empty_steps = 0
            if empty_steps_limit == empty_steps:
                break
            date_from = date_from - timedelta(minutes=interval)
            date_to = date_to - timedelta(minutes=interval)
