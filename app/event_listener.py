from datetime import datetime
from apscheduler.events import (
    EVENT_SCHEDULER_STARTED,
    EVENT_SCHEDULER_SHUTDOWN,
    EVENT_SCHEDULER_PAUSED,
    EVENT_SCHEDULER_RESUMED,
    EVENT_JOB_EXECUTED,
    EVENT_JOB_ERROR,
    EVENT_JOB_MISSED
)
from flask import current_app
from app import socketio
from app.models.log import SMLog, CDVLog

LOG_MODEL = {
    'sm': SMLog,
    'cdv': CDVLog,
}


def add_log_record(branch, text):
    log_model = LOG_MODEL.get(branch)
    if not log_model:
        return None
    log_model.add(branch=branch, text=text, log_type=1)
    # отправка данных клиенту
    curr = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    socketio.emit('new_event', {'msg': f'{curr} :: {branch} :: {text[:1000]}'})


def scheduler_listener(event):
    app = current_app._get_current_object()
    branch = 'cdv' if 'cdv' in event.job_id else 'sm'
    with app.app_context():
        if event.code == EVENT_SCHEDULER_STARTED:
            add_log_record(branch=branch, text=f'Scheduler {event.job_id} started.')
        elif event.code == EVENT_SCHEDULER_SHUTDOWN:
            add_log_record(branch=branch, text=f'Scheduler {event.job_id} was shut down.')
        elif event.code == EVENT_SCHEDULER_PAUSED:
            add_log_record(branch=branch, text=f'Scheduler {event.job_id} was paused.')
        elif event.code == EVENT_SCHEDULER_RESUMED:
            add_log_record(branch=branch, text=f'Scheduler {event.job_id} was resumed.')
        elif event.code == EVENT_JOB_MISSED:
            add_log_record(branch=branch, text=f"Job was missed: {event.job_id}")
        elif event.code == EVENT_JOB_EXECUTED:
            add_log_record(branch=branch, text=f"Job executed: {event.job_id}")
        elif event.code == EVENT_JOB_ERROR:
            add_log_record(branch=branch, text=f"Job {event.job_id} raised an exception: {event.exception}")
