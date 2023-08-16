""" Маршруты для работы с Автообзвоном """
__author__ = 'ke.mizonov'
import time
from apscheduler.jobstores.base import JobLookupError
from flask import request, current_app, render_template, Response
from app import socketio
from app.main import bp
from app.main.autocall.handler import Autocall, start_autocall_iteration
from app.main.utils import get_data_from_external_api, DATA_PROCESSOR
from config import Config


@bp.route('/start_autocalls')
def start_autocalls():
    app = current_app._get_current_object()
    for branch in ('drvorobjev', 'swissmedica'):
        scheduler_id = f'autocalls_{branch}'
        try:
            app.scheduler.remove_job(f'autocalls_{branch}')
        except JobLookupError:
            pass
        processor = DATA_PROCESSOR.get(branch)()
        if not app.scheduler.get_job(scheduler_id):
            app.scheduler.add_job(
                id=f'autocalls_{branch}',
                func=socketio.start_background_task,
                args=[start_autocall_iteration, app, branch],
                trigger='interval',
                seconds=int(Config().autocall_interval),
                max_instances=1
            )
            if not app.scheduler.running:
                app.scheduler.start()
            with app.app_context():
                processor.log.add(text=f'Autocalls scheduler started')
        else:
            with app.app_context():
                processor.log.add(text=f'Autocalls scheduler is already running')
    return Response(status=204)


@bp.route('/autocall_handler', methods=['POST'])
def autocall_handler():
    """
    Call data:
        {
            'number': '995591058618',
            'dateTime': '2023-07-04 14:44:17',
            'status': 'Исходящие, отвеченные',
            'operator': '',
            'record': 'https://sipuni.com/api/callback/record/05578a253f510b1840c67016426218c1',
            'callId': '1688471056.154959'
        }
    """
    return get_data_from_external_api(
        request=request,
        handler_func=Autocall().handle_autocall_result,
    )


@bp.route('/autocall', methods=['POST'])
def init_autocall():
    return get_data_from_external_api(
        request=request,
        handler_func=Autocall().handle_lead_status_changed
    )
