""" Общие маршруты """
__author__ = 'ke.mizonov'
import os
from datetime import datetime, timedelta
from apscheduler.jobstores.base import JobLookupError
from flask import render_template, current_app, redirect, url_for, request, send_file
from app import db, socketio
from app.amo.api.client import SwissmedicaAPIClient, DrvorobjevAPIClient
from app.main import bp
from app.main.processors import DATA_PROCESSOR
from app.main.tasks import get_data_from_amo, update_pivot_data
from app.models.data import SMData
from app.utils.excel import ExcelClient

API_CLIENT = {
    'SM': SwissmedicaAPIClient,
    'CDV': DrvorobjevAPIClient,
}


@bp.route('/')
def index():
    processor = DATA_PROCESSOR.get('sm')()
    # границы данных
    df, dt = processor.get_data_borders()
    date_from = datetime.fromtimestamp(df) if df else None
    date_to = datetime.fromtimestamp(dt) if dt else None
    date_curr = date_from + timedelta(minutes=60) if date_from else datetime.now()
    return render_template(
        'index.html',
        sm_df=date_from,
        sm_dt=date_to,
        sm_curr=date_curr.strftime("%Y-%m-%dT%H:%M")
    )


@bp.route('/get_token', methods=['GET'])
def get_token():
    return render_template('get_token.html')


@bp.route('/get_token', methods=['POST'])
def send_auth_code():
    auth_code = request.form.get('auth_code')
    client_id = request.form.get('client_id')
    client_secret = request.form.get('client_secret')
    redirect_url = request.form.get('redirect_url')
    branch = request.form.get('branch')
    # записываем креды в БД
    with current_app.app_context():
        api_client = API_CLIENT.get(branch)()
        api_client.get_token(
            auth_code=auth_code,
            client_id=client_id,
            client_secret=client_secret,
            redirect_url=redirect_url,
        )
    return redirect(url_for('main.get_token'))


@bp.route('/sm_data_excel')
def data_to_excel():
    collection = SMData.query.all()
    data = [(x.to_dict() or {}).get('data') for x in collection]
    ExcelClient(file_path=os.path.join('app', 'data'), file_name='sm_data').write(data=[
        ExcelClient.Data(data=data)
    ])
    return send_file(os.path.join('data', 'sm_data.xlsx'), as_attachment=True)


# @bp.route('/handle_new_leads_cdv', methods=['POST'])
# def handle_new_leads_cdv():
#     if request.content_type == 'application/json':
#         handle_lead_status_changed(data=request.json)
#         return 'success', 200
#     elif request.content_type == 'application/x-www-form-urlencoded':
#         handle_lead_status_changed(data=request.form.to_dict())
#         return 'success', 200
#     return 'Unsupported Media Type', 415


@bp.route('/button1')
def start_sm():
    lowest_dt = datetime.strptime(request.args.get('time', default=None, type=str), "%Y-%m-%dT%H:%M")
    # current_app - это проксированный экземпляр приложения,
    # _get_current_object - доступ к объекту приложения напрямую
    # с проксированным объектом получается некорректный контекст => костыляем
    app = current_app._get_current_object()
    # загрузка данных из Amo SM
    try:
        app.scheduler.remove_job('get_data_from_amo_sm')
    except JobLookupError:
        pass
    app.scheduler.add_job(
        id='get_data_from_amo_sm',
        func=socketio.start_background_task,
        args=[get_data_from_amo, app, 'sm', lowest_dt],
        trigger='interval',
        seconds=5,
        max_instances=1
    )
    if not app.scheduler.running:
        app.scheduler.start()
    # загрузка данных из Amo CDV
    # app.scheduler.add_job(
    #     id='get_data_from_amo_cdv',
    #     func=get_data_from_amo,
    #     args=[app, 'cdv'],
    #     trigger='interval',
    #     seconds=5,
    #     max_instances=1
    # )
    return render_template('index.html')


@bp.route('/start_update_pivot_data')
def start_update_pivot_data():
    app = current_app._get_current_object()
    # обновление данных для сводной таблицы SM
    app.scheduler.add_job(
        id='update_pivot_data_sm',
        func=update_pivot_data,
        args=[app, 'sm'],
        trigger='interval',
        seconds=5,
        max_instances=1
    )
    return 'started scheduler "update pivot data"'


@bp.route('/create_all')
def create_all():
    # импорты нужны для создания структуры БД!
    from app.models.amo_credentials import CDVAmoCredentials, SMAmoCredentials
    from app.models.amo_token import SMAmoToken, CDVAmoToken
    from app.models.contact import SMContact, CDVContact
    from app.models.event import SMEvent, CDVEvent
    from app.models.lead import CDVLead, SMLead
    from app.models.note import SMNote, CDVNote
    from app.models.pipeline import CDVPipeline, SMPipeline
    from app.models.user import SMUser, CDVUser
    from app.models.task import SMTask, CDVTask
    from app.models.company import SMCompany, CDVCompany
    from app.models.data import SMData, CDVData
    from app.models.log import SMLog, CDVLog
    from app.models.autocall import SMAutocallNumber, CDVAutocallNumber
    with current_app.app_context():
        db.create_all()
    return 'tables created'


@bp.route('/drop_all')
def drop_all():
    with current_app.app_context():
        db.drop_all()
    return 'tables dropped'
