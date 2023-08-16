""" Общие маршруты """
__author__ = 'ke.mizonov'

import uuid
from datetime import datetime
from apscheduler.jobstores.base import JobLookupError
from flask import render_template, current_app, redirect, url_for, request, Response
from app import db, socketio
from app.amo.api.client import SwissmedicaAPIClient, DrvorobjevAPIClient
from app.amo.processor.processor import GoogleSheets
from app.google_api.client import GoogleAPIClient
from app.main import bp
from app.main.processors import DATA_PROCESSOR
from app.main.routes.telegram import get_data_from_post_request
from app.main.tasks import SchedulerTask
from app.models.data import SMData, CDVData
from config import Config

API_CLIENT = {
    'SM': SwissmedicaAPIClient,
    'CDV': DrvorobjevAPIClient,
    'sm': SwissmedicaAPIClient,
    'cdv': DrvorobjevAPIClient,
    'swissmedica': SwissmedicaAPIClient,
    'drvorobjev': DrvorobjevAPIClient,
}

DATA_MODEL = {
    'sm': SMData,
    'cdv': CDVData
}


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
    processor = DATA_PROCESSOR.get(branch)()
    if not app.scheduler.get_job(scheduler_id):
        app.scheduler.add_job(
            id=scheduler_id,
            func=socketio.start_background_task,
            args=[SchedulerTask().get_data_from_amo, app, branch, lowest_dt],
            trigger='interval',
            seconds=60,
            max_instances=1
        )
        if not app.scheduler.running:
            app.scheduler.start()
        with app.app_context():
            processor.log.add(text=f'Amo data loader has started', log_type=1)
            return Response(status=204)
    with app.app_context():
        processor.log.add(text=f'Amo data loader is already running', log_type=1)
    return Response(status=204)
    # return render_template('index.html')


def stop_get_data_from_amo_scheduler(branch: str):
    scheduler_id = f'get_data_from_amo_{branch}'
    # current_app - это проксированный экземпляр приложения,
    # _get_current_object - доступ к объекту приложения напрямую
    # с проксированным объектом получается некорректный контекст => костыляем
    app = current_app._get_current_object()
    # загрузка данных из Amo CDV
    try:
        app.scheduler.remove_job(scheduler_id)
    except JobLookupError:
        pass
    processor = DATA_PROCESSOR.get(branch)()
    # if not app.scheduler.running:
    #     app.scheduler.start()
    with app.app_context():
        processor.log.add(text=f'Amo data loader has stopped', log_type=1)
    return Response(status=204)


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
    processor = DATA_PROCESSOR.get(branch)()
    if not app.scheduler.get_job(scheduler_id):
        app.scheduler.add_job(
            id=scheduler_id,
            func=socketio.start_background_task,
            args=[SchedulerTask().update_pivot_data, app, branch],
            trigger='interval',
            seconds=60,
            max_instances=1
        )
        if not app.scheduler.running:
            app.scheduler.start()
        with app.app_context():
            processor.log.add(text=f'Amo data builder has started', log_type=1)
            return Response(status=204)
    with app.app_context():
        processor.log.add(text=f'Amo data builder is already running', log_type=1)
    return Response(status=204)


def stop_update_pivot_data(branch: str):
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
    processor = DATA_PROCESSOR.get(branch)()
    # if not app.scheduler.running:
    #     app.scheduler.start()
    with app.app_context():
        processor.log.add(text=f'Amo data builder has stopped', log_type=1)
    return Response(status=204)


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


# class DateTimeDecoder(json.JSONDecoder):
#     def __init__(self, *args, **kwargs):
#         json.JSONDecoder.__init__(self, object_hook=self.object_hook, *args, **kwargs)
#
#     def object_hook(self, dct):
#         for k, v in dct.items():
#             if isinstance(v, str):
#                 try:
#                     dct[k] = datetime.fromisoformat(v)
#                 except ValueError:
#                     try:
#                         dct[k] = date.fromisoformat(v)
#                     except ValueError:
#                         pass
#         return dct


def data_to_excel(branch: str):

    model = DATA_MODEL.get(branch)
    portion_size = 1000
    offset = 0
    # print(f'sending {branch} pivot data started')
    socketio.emit('pivot_data', {
        'start': True,
        'data': [],
        'headers': None,
        'done': False,
        'file_name': None
    })
    num = 0
    headers = []
    while True:
        collection = model.query.limit(portion_size).offset(offset).all()
        if not collection:
            break
        if not headers:
            headers = [x for x in collection[0].to_dict().get('data').keys()]
            # print(f'headers: {headers} ')
        data = [
            x.to_dict().get('data')
            for x in collection
        ]
        num += 1
        # print(f'sending {branch} pivot data [{num} :: {len(data)}]')
        if len(data) > 0:
            print('sending', data[0]['pipeline_name'])
        socketio.emit('pivot_data', {
            'start': False,
            'data': data,
            'headers': headers,
            'done': False,
            'file_name': None
        })
        offset += portion_size
    # print(f'sending {branch} pivot data stopped')
    socketio.emit('pivot_data', {
        'start': False,
        'data': [],
        'headers': headers,
        'done': True,
        'file_name': f'data_{branch}'
    })
    return Response(status=204)


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


@bp.route('/tawk', methods=['POST'])
def tawk():
    """
    {
        'chatId': 'aaf4ff90-3a7d-11ee-86b6-71ef2c3aef2f',
        'visitor': {'name': 'Test Name', 'city': 'batumi', 'country': 'GE'},
        'message': {'sender': {'type': 'visitor'}, 'text': 'Name : Test Name\r\nPhone : 79216564906', 'type': 'msg'},
        'time': '2023-08-14T08:37:11.874Z',
        'event': 'chat:start',
        'property': {'id': '64d0945994cf5d49dc68dd99', 'name': 'CDV'} <-- это название чата, с ним будем мапать
    }
    """
    data = request.json or {}
    print(data)
    # убеждаемся, что перед нами сообщение с заполненной контактной формой (pre-chat)
    prop = data.get('property') or {}
    chat_name = prop.get('name')
    if not chat_name:
        print(1)
        return Response(status=204)
    msg_data = data.get('message')
    if not msg_data:
        print(2)
        return Response(status=204)
    sender = (msg_data.get('sender') or {}).get('type')
    if sender != 'visitor':
        print(3)
        return Response(status=204)
    # имя и телефон клиента
    spl_text = (msg_data.get('text') or '').split('\r\n')
    if len(spl_text) != 2:
        print(4)
        return Response(status=204)
    name, phone = spl_text
    if 'Name : ' not in name:
        print(5)
        return Response(status=204)
    if 'Phone : ' not in phone:
        print(6)
        return Response(status=204)
    name = name.replace('Name : ', '')
    phone = phone.replace('Phone : ', '')
    # по имени чата определяем филиал, инициализируем amo клиент
    config = Config().TAWK.get(chat_name) or {}
    branch = config.get('branch')
    if not branch:
        print(7)
        return Response(status=204)
    amo_client = API_CLIENT.get(branch)()
    # пытаемся найти лид по номеру телефона
    existing_leads = list(amo_client.find_leads(query=phone, limit=1))
    note_msg = f"Incoming chat https://dashboard.tawk.to/#/inbox/{prop.get('id')}/all/chat/{data['chatId']}"
    if existing_leads:
        # лид найден - дописываем чат в ленту событий / примечаний
        existing_lead = existing_leads[0]
        amo_client.add_note_simple(entity_id=int(existing_lead['id']), text=note_msg)
    else:
        # лид не найден - создаем
        # print('creating new lead')
        lead_added = amo_client.add_lead_simple(
            name=f'TEST! Lead from Tawk: {name}',
            tags=['Tawk', chat_name],
            pipeline_id=int(config.get('pipeline_id')),
            status_id=int(config.get('status_id')),
            contacts=[
                {'value': phone, 'field_id': int(config.get('phone_field_id')), 'enum_code': 'WORK'}
            ]
        )
        # response from Amo [{"id":24050975,"contact_id":28661273,"company_id":null,"request_id":["0"],"merged":false}]
        added_lead_data = lead_added.json()
        if added_lead_data and 'id' in added_lead_data[0]:
            amo_client.add_note_simple(entity_id=int(added_lead_data[0]['id']), text=note_msg)
            return Response(status=204)
    return Response(status=204)


@bp.route('/agree_for_treatment', methods=['POST'])
def agree_for_treatment():
    data = get_data_from_post_request(_request=request)
    if not data:
        return 'Unsupported Media Type', 415
    branch = data.get('account[subdomain]')
    processor = DATA_PROCESSOR.get(branch)()
    pipeline_id = data.get('leads[status][0][pipeline_id]')
    # pipeline = processor.get_pipeline_and_status_by_id(
    #     pipeline_id=pipeline_id,
    #     status_id=data.get('leads[status][0][status_id]')
    # )
    # получаем лид из Amo
    amo_client = API_CLIENT.get(branch)()
    lead_id = data.get('leads[status][0][id]')
    lead = amo_client.get_lead_by_id(lead_id=lead_id)
    # получаем пользователя, ответственного за лид
    user = processor.get_user_by_id(user_id=lead.get('responsible_user_id'))
    # print('agree_for_treatment lead', lead)
    # print('agree_for_treatment user', user)
    GoogleAPIClient(
        book_id=GoogleSheets.ArrivalSM.value,
        sheet_title='Draft'
    ).write_data_to_sheet(data=[{'lead': lead, 'user': user}])
    return Response(status=204)


@bp.route('/stop_get_amo_data_sm')
def stop_get_amo_data_sm():
    return stop_get_data_from_amo_scheduler(branch='sm')


@bp.route('/stop_get_amo_data_cdv')
def stop_get_amo_data_cdv():
    return stop_get_data_from_amo_scheduler(branch='cdv')


@bp.route('/start_update_pivot_data_sm')
def start_update_pivot_data_sm():
    return start_update_pivot_data(branch='sm')


@bp.route('/start_update_pivot_data_cdv')
def start_update_pivot_data_cdv():
    return start_update_pivot_data(branch='cdv')


@bp.route('/stop_update_pivot_data_sm')
def stop_update_pivot_data_sm():
    return stop_update_pivot_data(branch='sm')


@bp.route('/stop_update_pivot_data_cdv')
def stop_update_pivot_data_cdv():
    return stop_update_pivot_data(branch='cdv')


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
