""" Общие маршруты """
__author__ = 'ke.mizonov'
import time
from datetime import datetime
from typing import Dict
from urllib.parse import urlparse, parse_qs
from apscheduler.jobstores.base import JobLookupError
from flask import render_template, current_app, redirect, url_for, request, Response
from app import db, socketio
from app.amo.api.client import SwissmedicaAPIClient, DrvorobjevAPIClient
from app.amo.processor.functions import clear_phone
from app.main import bp
from app.main.arrival.handler import waiting_for_arrival
from app.main.processors import DATA_PROCESSOR
from app.main.tasks import SchedulerTask
from app.models.chat import SMChat, CDVChat
from app.models.data import SMData, CDVData
from app.tawk.api import TawkRestClient
from config import Config

API_CLIENT = {
    'SM': SwissmedicaAPIClient,
    'CDV': DrvorobjevAPIClient,
    'sm': SwissmedicaAPIClient,
    'cdv': DrvorobjevAPIClient,
    'swissmedica': SwissmedicaAPIClient,
    'drvorobjev': DrvorobjevAPIClient,
}

TAWK_CHAT_MODEL = {
    'SM': SMChat,
    'CDV': CDVChat,
    'sm': SMChat,
    'cdv': CDVChat,
    'swissmedica': SMChat,
    'drvorobjev': CDVChat,
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


@bp.route('/arrival_sync', methods=['GET'])
def arrival_sync():
    # waiting_for_arrival('swissmedica')
    return render_template('arrival_sync.html')


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


# @socketio.on('client_message')
# def handle_client_message(message):
#     print('Received message:', message['data'])

def create_lead_from_tawk_chat(data: Dict):
    # по имени чата определяем филиал, инициализируем amo клиент
    chat_name = data.get('chat_name')
    config = Config().TAWK.get(data.get('chat_name')) or {}
    branch = config.get('branch')
    if not branch:
        return Response(status=204)
    visitor = data.get('visitor')
    if not visitor:
        return Response(status=204)
    amo_client = API_CLIENT.get(branch)()
    name = visitor.get('name')
    phone = clear_phone(visitor.get('phone'))
    data['visitor'] = {'name': name, 'phone': phone}
    # готовим сообщение
    # sync_controller = SYNC_CONTROLLER.get(branch)()
    # пытаемся найти лид по номеру телефона
    existing_leads = list(amo_client.find_leads(query=phone, limit=1))
    if existing_leads:
        # лид найден - дописываем чат в ленту событий / примечаний
        existing_lead = existing_leads[0]
        lead_id = int(existing_lead['id'])
    else:
        # лид не найден - создаем
        lead_added = amo_client.add_lead_simple(
            name=f'TEST! Lead from Tawk: {name}',
            tags=['Tawk', chat_name],
            referrer=data.get('refferer'),
            utm=data.get('utm'),
            pipeline_id=int(config.get('pipeline_id')),
            status_id=int(config.get('status_id')),
            contacts=[
                {'value': phone, 'field_id': int(config.get('phone_field_id')), 'enum_code': 'WORK'}
            ]
        )
        # response from Amo [{"id":24050975,"contact_id":28661273,"company_id":null,"request_id":["0"],"merged":false}]
        added_lead_data = lead_added.json()
        if not added_lead_data:
            return
        # print(added_lead_data)

        # {'validation-errors': [{'request_id': '0', 'errors': [{'code': 'TooFew', 'path': 'custom_fields_values', 'detail': 'This collection should contain 1 element or more.'}]}], 'title': 'Bad Request', 'type': 'https://httpstatus.es/400', 'status': 400, 'detail': 'Request validation failed'}

        lead_id = int(added_lead_data.get('id'))
    # messages = sync_controller.chat(lead_id=lead_id, data=data)
    # note_msg = ''
    # for message in messages:
    #     note_msg = f"{note_msg}\n{message['date']} :: {message['type']} :: {message['text']}"

    note_msg = TawkRestClient().get_source_and_messages_text(channel_id=data.get('channel_id'), chat_id=data.get('chat_id'))
    if note_msg:
        amo_client.add_note_simple(entity_id=lead_id, text=note_msg)
    # message = messages[-1]
    # agent = message.get('agent')
    # name = message['type']
    # if name == 'agent' and agent:
    #     name = agent
    # note_msg = f"{message['date']} :: {name} :: {message['text']}"
    # existing_note = amo_client.get_tawk_lead_notes(lead_id=lead_id)
    # if existing_note:
    #     # обновляем существующее примечание
    #     text = (existing_note.get('params') or {}).get('text')
    #     note_msg = f'{text}\n{note_msg.strip()}'
    #     amo_client.update_note_simple(note_id=int(existing_note.get('id')), lead_id=lead_id, text=note_msg)
    #     return
    # # добавляем новое примечание
    # note_msg = f'Tawk chat:\n{note_msg.strip()}'


# @bp.route('/tawk_data', methods=['POST'])
# def tawk_data():
#     """ Принимаем данные со стороны клиента
#     {
#         'type': 'visitor',
#         'visitor': {'name': str, 'phone': str},
#         'message': str,
#         'utm': dict,
#         'referrer': str,
#         'create_lead': bool,
#         'chat_name': str
#     }
#     """
#     data = request.json or {}
#     app = current_app._get_current_object()
#     with app.app_context():
#         create_lead_from_tawk_chat(data=data)
#     return Response(status=204)


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
    {
        'chatId': '61880e20-4d46-11ee-871d-09e91a719de2',
        'visitor': {'name': 'ChatEnds','city': 'batumi', 'country': 'GE'},
        'time': '2023-09-07T06:20:09.450Z',
        'event': 'chat:end',
        'property': {'id': '64d0945994cf5d49dc68dd99', 'name': 'cdv_main'}
    }
    """
    # return Response(status=204)
    # handle data from Tawk here
    data = request.json or {}
    print(data)
    # убеждаемся, что перед нами сообщение с заполненной контактной формой (pre-chat)
    prop = data.get('property') or {}
    chat_name = prop.get('name')
    if not chat_name:
        return Response(status=204)
    # msg_data = data.get('message')
    # if not msg_data:
    #     return Response(status=204)
    # sender = (msg_data.get('sender') or {}).get('type')
    # if sender != 'visitor':
    #     return Response(status=204)
    # имя и телефон клиента
    # spl_text = (msg_data.get('text') or '').split('\r\n')
    # if len(spl_text) != 2:
    #     return Response(status=204)
    # name, phone = spl_text
    # if 'Name : ' not in name or 'Phone : ' not in phone:
    #     return Response(status=204)
    # name = name.replace('Name : ', '')
    # phone = phone.replace('Phone : ', '')

    # тут данные чата могли не успеть записаться в базу Tawk, поэтому циклим
    """
    {
        'person': {
            'name': {'first': 'chat data', 'last': 'transfer'},
            'emails': [], 'phones': ['2589631477'],
            'createdOn': '2023-09-07T07:45:55.831Z',
            'updatedOn': '2023-09-07T07:46:24.430Z',
            'device': {'ip': '37.232.82.193', 'browser': 'chrome', 'os': 'windows'},
            'firstSeenOn': '2023-09-07T07:45:55.926Z',
            'lastSeenOn': '2023-09-07T07:45:55.926Z',
            'location': {'continent': 'AS', 'country': 'GE', 'cityName': 'Batumi', 'cityId': 615532, 'regionId': 615929, 'regionName': 'Achara', 'point': '41.6473,41.6258'},
            'webSession': {'count': 1, 'first': '2023-09-07T07:45:55.926Z', 'latest': '2023-09-07T07:45:55.926Z', 'pageViews': 0, 'timeSpent': 0},
            'primaryPhone': '2589631477',
            'id': '64f97fb3aab3f51368ed3600'
        },
        'messages': 'Tawk chat from: https://swiss-medica-2e0e7bc937df.herokuapp.com/\nView chat: https://dashboard.tawk.to/#/inbox/64d0945994cf5d49dc68dd99/all/chat/93e94760-4d52-11ee-9f1f-6dfbc0fa7e4b\n2023-09-07 07:46:24 :: [chat started]\n2023-09-07 07:46:24 :: chat data transfer :: hi\n2023-09-07 07:46:24 :: Operator Kirill :: [operator joined chat]\n2023-09-07 07:46:24 :: Operator Kirill :: test\n2023-09-07 07:46:24 :: chat data transfer :: bb'
    }
    """
    tawk_data = None
    counter = 0
    max_counter = 24
    while not tawk_data:
        counter += 1
        if counter > max_counter:
            break
        tawk_data = TawkRestClient().get_messages_text_and_person(channel_id=prop.get('id'), chat_id=data['chatId'])
        print('tawk_data', tawk_data)
        time.sleep(5)
    if not tawk_data:
        return Response(status=204)
    person_dict = tawk_data.get('person') or {}
    # разбираем utm-метки из source
    utm_dict = {}
    source = tawk_data.get('source')
    if source:
        parsed_url = urlparse(source)
        utm_dict = parse_qs(parsed_url.query)
    # имя и номер пациента
    name_data = person_dict.get('name')
    name = f"{name_data.get('first') or ''} {name_data.get('last') or ''}".strip()
    phones_data = person_dict.get('phones') or []
    if not phones_data:
        return Response(status=204)
    emails_data = person_dict.get('emails') or []
    if not emails_data:
        return Response(status=204)
    phone = clear_phone(phones_data[0])
    email = emails_data[0]

    # по имени чата определяем филиал, инициализируем amo клиент
    config = Config().tawk.get(chat_name) or {}
    branch = config.get('branch')
    if not branch:
        return Response(status=204)
    amo_client = API_CLIENT.get(branch)()
    # пытаемся найти лид по номеру телефона
    existing_leads = list(amo_client.find_leads(query=phone, limit=1))
    # note_msg = f"Incoming chat https://dashboard.tawk.to/#/inbox/{prop.get('id')}/all/chat/{data['chatId']}"

    # определяем идентификатор ответственного пользователя
    manager_id = tawk_data.get('manager').get('id')
    managers = Config().managers.get(branch) or {}
    tawk_amo_dict = {
        value['tawk_id']: value['amo_id']
        for value in managers.values()
        if value['tawk_id'] and value['amo_id']
    }
    responsible_user_id = tawk_amo_dict.get(manager_id) or 0

    lead_id = None
    if existing_leads:
        # лид найден - дописываем чат в ленту событий / примечаний
        lead_id = int(existing_leads[0]['id'])
    else:
        # лид не найден - создаем
        print('creating new lead')
        lead_added = amo_client.add_lead_simple(
            name=f'TEST! Lead from Tawk: {name}',
            tags=['Tawk', chat_name],
            referrer=(person_dict.get('customAttributes') or {}).get('ref'),
            utm=utm_dict,
            pipeline_id=int(config.get('pipeline_id')),
            status_id=int(config.get('status_id')),
            contacts=[
                {'value': phone, 'field_id': int(config.get('phone_field_id')), 'enum_code': 'WORK'},
                {'value': email, 'field_id': int(config.get('email_field_id')), 'enum_code': 'WORK'},
            ],
            responsible_user_id=responsible_user_id
        )
        # response from Amo [{"id":24050975,"contact_id":28661273,"company_id":null,"request_id":["0"],"merged":false}]
        added_lead_data = lead_added.json()
        print(added_lead_data)
        try:
            lead_id = int(added_lead_data[0]['id'])
        except:
            pass
    if lead_id:
        print('adding note to lead', lead_id, tawk_data.get('messages'))
        amo_client.add_note_simple(entity_id=lead_id, text=tawk_data.get('messages'))
    return Response(status=200)


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
    from app.models.chat import SMChat, CDVChat
    with current_app.app_context():
        db.create_all()
    return 'tables created'


@bp.route('/drop_all')
def drop_all():
    with current_app.app_context():
        db.drop_all()
    return 'tables dropped'
