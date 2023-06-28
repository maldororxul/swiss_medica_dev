import json
import string
import random
from datetime import datetime, timedelta, date
from flask import Flask
from app import db, socketio
from app.main.controllers import SYNC_CONTROLLER
from app.main.processors import DATA_PROCESSOR
from app.models.lead import SMLead


is_running = False


class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()


def add_random_lead(app: Flask):
    with app.app_context():
        lead = SMLead(name=''.join(random.choices(string.ascii_uppercase + string.digits, k=10)))
        db.session.add(lead)
        db.session.commit()


# def get_logs(app: Flask, branch: str):
#     processor = DATA_PROCESSOR.get('sm')()
#     with app.app_context():
#         # тащим лог
#         for log in processor.get_logs(branch=branch) or []:
#             dt = datetime.fromtimestamp(log.created_at).strftime("%Y-%m-%d %H:%M:%S")
#             socketio.emit('new_event', {'msg': f'{dt} :: {log.text}'})


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
            curr = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            df = date_from.strftime("%Y-%m-%d %H:%M:%S")
            dt = date_to.strftime("%H:%M:%S")
            repeated_iteration = "" if has_new else f" :: R{empty_steps}"
            msg = f'reading {branch} data :: {df} - {dt}{repeated_iteration}'
            # запись лога в БД
            processor.add_log(branch=branch, text=msg, log_type=1)
            # отправка данных клиенту
            socketio.emit('new_event', {'msg': f'{curr} :: {msg}'})
            if empty_steps_limit == empty_steps:
                is_running = False
                break
            date_from = date_from - timedelta(minutes=interval)
            date_to = date_to - timedelta(minutes=interval)


def update_pivot_data(app: Flask, branch: str):
    interval = 59
    empty_steps_limit = 20
    empty_steps = 0
    # starting_date = datetime(2023, 5, 26, 15, 0, 0)
    starting_date = datetime.now()
    date_from = starting_date - timedelta(minutes=interval)
    date_to = starting_date
    data_processor = DATA_PROCESSOR.get(branch)
    with app.app_context():
        while True:
            collection = []
            for line in data_processor(date_from=date_from, date_to=date_to).update() or []:
                item = {key.split('_(')[0]: value for key, value in line.items()}
                collection.append({
                    'id': line['id'],
                    'created_at': line['created_at_ts'],
                    'updated_at': line['updated_at_ts'],
                    'data': json.dumps(item, cls=DateTimeEncoder)
                })
            controller = SYNC_CONTROLLER.get(branch)
            has_new = controller(date_from=date_from, date_to=date_to).update_data(collection=collection)
            print(f'{datetime.now()} :: updating data :: {date_from} :: {date_to} :: {has_new}')
            if not has_new:
                empty_steps += 1
            else:
                empty_steps = 0
            if empty_steps_limit == empty_steps:
                break
            date_from = date_from - timedelta(minutes=interval)
            date_to = date_to - timedelta(minutes=interval)
