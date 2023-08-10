""" Фоновые задачи: загрузка данных с источников, обновление pivot data и проч. """
__author__ = 'ke.mizonov'
from datetime import datetime, timedelta
from flask import Flask
from app import socketio
from app.main.controllers import SYNC_CONTROLLER
from app.main.processors import DATA_PROCESSOR
from app.main.utils import DateTimeEncoder

# get_data_from_amo_is_running = False
# update_pivot_data_is_running = False


def get_data_from_amo(app: Flask, branch: str, starting_date: datetime):

    # print('get_data_from_amo start working', branch)

    # global get_data_from_amo_is_running
    # if get_data_from_amo_is_running:
    #     return
    # get_data_from_amo_is_running = True

    interval = 60
    empty_steps_limit = 20
    empty_steps = 0
    date_from = starting_date - timedelta(minutes=interval)
    date_to = starting_date
    processor = DATA_PROCESSOR.get(branch)()
    with app.app_context():
        processor.log.add(
            text='reading data :: iteration started',
            log_type=1
        )
        controller = SYNC_CONTROLLER.get(branch)()
        while True:
            # if not get_data_from_amo_is_running:
            #     break
            has_new = controller.run(date_from=date_from, date_to=date_to)
            if not has_new:
                empty_steps += 1
            # else:
            #     empty_steps = 0
            df = date_from.strftime("%Y-%m-%d %H:%M:%S")
            dt = date_to.strftime("%H:%M:%S")
            repeated_iteration = "" if has_new else f" :: R{empty_steps}"
            msg = f'reading data :: {df} - {dt}{repeated_iteration}'
            # запись лога в БД
            processor.log.add(text=msg, log_type=1)
            if empty_steps_limit == empty_steps:
                # print('get_data_from_amo', branch)
                processor.log.add(
                    text='reading data :: iteration finished',
                    log_type=1
                )
                # get_data_from_amo_is_running = False
                return
            date_from = date_from - timedelta(minutes=interval)
            date_to = date_to - timedelta(minutes=interval)


def update_pivot_data(app: Flask, branch: str):

    # print('update_pivot_data start working', branch)

    # global update_pivot_data_is_running
    # if update_pivot_data_is_running:
    #     return
    # update_pivot_data_is_running = True

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
            # if not update_pivot_data_is_running:
            #     break
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
                    # print('not updated')
                    not_updated += 1
                total += 1
            if total == not_updated:
                empty_steps += 1
            if empty_steps_limit == empty_steps:
                # starting_date = datetime.now()
                # print('updating pivot data stopped', branch)
                data_processor.log.add(
                    text='updating pivot data :: iteration finished',
                    log_type=1
                )
                # update_pivot_data_is_running = False
                return
            # else:
            #     empty_steps = 0
            df = date_from.replace(microsecond=0)
            r = f' R{empty_steps}' if empty_steps > 0 else ''
            data_processor.log.add(
                text=f'updating pivot data :: {df.date()} {df.time()} - {date_to.replace(microsecond=0).time()}{r}',
                log_type=1
            )
            date_from = date_from - timedelta(minutes=interval)
            date_to = date_to - timedelta(minutes=interval)
