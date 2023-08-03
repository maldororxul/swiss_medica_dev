""" Общие маршруты """
__author__ = 'ke.mizonov'
import json
from datetime import date, datetime
from apscheduler.jobstores.base import JobLookupError
from flask import render_template, current_app, redirect, url_for, request
from app import db, socketio
from app.amo.api.client import SwissmedicaAPIClient, DrvorobjevAPIClient
from app.main import bp
from app.main.processors import DATA_PROCESSOR
from app.main.tasks import get_data_from_amo, update_pivot_data
from app.models.data import SMData, CDVData

API_CLIENT = {
    'SM': SwissmedicaAPIClient,
    'CDV': DrvorobjevAPIClient,
}

DATA_MODEL = {
    'sm': SMData,
    'cdv': CDVData
}


# class CustomJSONEncoder(json.JSONEncoder):
#     def default(self, obj):
#         if isinstance(obj, date) or isinstance(obj, datetime):
#             return obj.isoformat()
#         return super().default(obj)


def start_get_data_from_amo_scheduler(branch: str):
    scheduler_id = f'get_data_from_amo_{branch}'
    lowest_dt = datetime.strptime(request.args.get('time', default=None, type=str), "%Y-%m-%dT%H:%M")
    # current_app - это проксированный экземпляр приложения,
    # _get_current_object - доступ к объекту приложения напрямую
    # с проксированным объектом получается некорректный контекст => костыляем
    app = current_app._get_current_object()
    # загрузка данных из Amo CDV
    try:
        app.scheduler.remove_job(scheduler_id)
    except JobLookupError:
        pass
    app.scheduler.add_job(
        id=scheduler_id,
        func=socketio.start_background_task,
        args=[get_data_from_amo, app, branch, lowest_dt],
        trigger='interval',
        seconds=60,
        max_instances=1
    )
    processor = DATA_PROCESSOR.get(branch)()
    if not app.scheduler.running:
        app.scheduler.start()
    with app.app_context():
        processor.log.add(text=f'Amo data loader has started', log_type=1)
    return render_template('index.html')


def start_update_pivot_data(branch: str):
    scheduler_id = f'update_pivot_data_{branch}'
    # current_app - это проксированный экземпляр приложения,
    # _get_current_object - доступ к объекту приложения напрямую
    # с проксированным объектом получается некорректный контекст => костыляем
    app = current_app._get_current_object()
    # загрузка данных из Amo CDV
    try:
        app.scheduler.remove_job(scheduler_id)
    except JobLookupError:
        pass
    app.scheduler.add_job(
        id=scheduler_id,
        func=socketio.start_background_task,
        args=[update_pivot_data, app, branch],
        trigger='interval',
        seconds=600,
        max_instances=1
    )
    processor = DATA_PROCESSOR.get(branch)()
    if not app.scheduler.running:
        app.scheduler.start()
    with app.app_context():
        processor.log.add(text=f'Amo data builder has started', log_type=1)
    return render_template('index.html')


@bp.route('/')
def index():
    # границы данных и текущая дата SM
    processor = DATA_PROCESSOR.get('sm')()
    sm_date_from, sm_date_to, sm_date_curr = processor.get_data_borders_and_current_date()
    # границы данных и текущая дата CDV
    processor = DATA_PROCESSOR.get('cdv')()
    cdv_date_from, cdv_date_to, cdv_date_curr = processor.get_data_borders_and_current_date()
    return render_template(
        'index.html',
        sm_df=sm_date_from,
        sm_dt=sm_date_to,
        sm_curr=sm_date_curr,
        cdv_df=cdv_date_from,
        cdv_dt=cdv_date_to,
        cdv_curr=cdv_date_curr
    )


# @bp.route('/favicon.ico')
# def favicon():
#     app = current_app._get_current_object()
#     path = os.path.join(app.root_path, 'static')
#     return send_from_directory(path, 'favicon.ico', mimetype='image/vnd.microsoft.icon')


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


def data_to_excel(branch: str):
    model = DATA_MODEL.get(branch)
    portion_size = 1000
    offset = 0
    socketio.emit('pivot_data', {
        'start': True,
        'data': [],
        'done': False,
        'file_name': None
    })
    while True:
        collection = model.query.limit(portion_size).offset(offset).all()
        if not collection:
            break
        socketio.emit('pivot_data', {
            'start': False,
            'data': json.dumps([(x.to_dict() or {}).get('data') for x in collection], default=str),
            'done': False,
            'file_name': f'data_{branch}'
        })
        offset += portion_size
    socketio.emit('pivot_data', {
        'start': False,
        'data': [],
        'done': True,
        'file_name': None
    })
    return render_template('index.html')


@bp.route('/data_excel_sm')
def data_to_excel_sm():
    return data_to_excel(branch='sm')


@bp.route('/data_excel_cdv')
def data_to_excel_cdv():
    # collection = CDVData.query.all()
    # data = [(x.to_dict() or {}).get('data') for x in collection]
    # ExcelClient(file_path=os.path.join('app', 'data'), file_name='data_cdv').write(data=[
    #     ExcelClient.Data(data=data)
    # ])
    # return send_file(os.path.join('data', 'data_cdv.xlsx'), as_attachment=True)
    return data_to_excel(branch='cdv')


@bp.route('/get_amo_data_sm')
def get_amo_data_sm():
    return start_get_data_from_amo_scheduler(branch='sm')


@bp.route('/get_amo_data_cdv')
def get_amo_data_cdv():
    return start_get_data_from_amo_scheduler(branch='cdv')


@bp.route('/start_update_pivot_data_sm')
def start_update_pivot_data_sm():
    start_update_pivot_data(branch='sm')


@bp.route('/start_update_pivot_data_cdv')
def start_update_pivot_data_cdv():
    start_update_pivot_data(branch='cdv')


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
