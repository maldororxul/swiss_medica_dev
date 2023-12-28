""" Общие маршруты """
__author__ = 'ke.mizonov'
from datetime import datetime
from typing import Union, Type
from urllib.parse import urlparse, parse_qs

from apscheduler.jobstores.base import JobLookupError
from flask import render_template, current_app, redirect, url_for, request, Response
from app import db, socketio
from app.amo.api.chat_client import AmoChatsAPIClient
from app.amo.api.client import SwissmedicaAPIClient, DrvorobjevAPIClient
from app.main import bp
from app.main.arrival.handler import waiting_for_arrival
from app.main.processors import DATA_PROCESSOR
from app.main.routes.utils import get_data_from_post_request
from app.main.tasks import SchedulerTask
from app.main.utils import DateTimeEncoder
from app.models.chat import SMChat, CDVChat
from app.models.data import SMData, CDVData
from app.models.raw_lead_data import SMRawLeadData, CDVRawLeadData
from app.tawk.controller import TawkController
from app.whatsapp.controller import WhatsAppController
from config import Config

API_CLIENT = {
    'SM': SwissmedicaAPIClient,
    'CDV': DrvorobjevAPIClient,
    'sm': SwissmedicaAPIClient,
    'cdv': DrvorobjevAPIClient,
    'swissmedica': SwissmedicaAPIClient,
    'drvorobjev': DrvorobjevAPIClient,
}

RAW_LEAD = {
    'SM': SMRawLeadData,
    'CDV': CDVRawLeadData,
    'sm': SMRawLeadData,
    'cdv': CDVRawLeadData,
    'swissmedica': SMRawLeadData,
    'drvorobjev': CDVRawLeadData,
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
    app = current_app._get_current_object()
    waiting_for_arrival(app=app, branch='swissmedica')
    return render_template('arrival_sync.html')


@bp.route('/add_lead_from_cf', methods=['POST', 'GET'], strict_slashes=False)
def process_request():
    # http://167.172.109.78/calltracking3/?lang=FR
    # https://swiss-medica-2e0e7bc937df.herokuapp.com/add_lead_from_cf/?lang=FR

    print('got request from webform')

    try:

        post = request.form.to_dict()
        print(post)

        lang = request.args.get('lang', default='EN')  # Получаем язык из GET-параметров, по умолчанию 'EN'
        form_data = post

        pipeline_ids = {'EN': 772717, 'DE': 2048428, 'FR': 2047060, 'IT': 5707270}
        status_ids = {'EN': 19045762, 'DE': 29839168, 'FR': 29830081, 'IT': 50171236}
        temptags = {'EN': 689047, 'DE': 689049, 'FR': 689053, 'IT': 689051, 'CZ': 689055}

        form_data['pipeline_id'] = pipeline_ids.get(lang, 772717)
        form_data['status_id'] = status_ids.get(lang, 19045762)
        form_data['tags'] = [{"id": temptags.get(lang, 689057)}]

        form_data['message'] = post.get('message', post.get('diagnosis', 'No message'))

        if not form_data.get('name'):
            return "NO NAME", 400

        parsed_url = urlparse(post.get('utm_referer', ''))
        getmass = parse_qs(parsed_url.query)

        for key, value in getmass.items():
            form_data[key] = value[0][:250]

        if 'utm_referer' in form_data:
            form_data['utm_referer'] = form_data['utm_referer'][:250]

        form_data.setdefault('email', 'no email')
        form_data.setdefault('detected_country', 'not_detected_country')
        form_data.setdefault('detected_city', 'not_detected_city')

        print(form_data)
        # вот это вообще от балды...
        utm_dict = {
            'utm_source': form_data.get('utm_source'),
            'utm_campaign': form_data.get('utm_campaign'),
            'utm_medium': form_data.get('utm_medium')
        }
        amo_client = SwissmedicaAPIClient()
        lead_added = amo_client.add_lead_simple(
            name=f"New lead |{lang}| {form_data['name']}",
            pipeline_id=int(form_data['pipeline_id']),
            status_id=int(form_data['status_id']),
            contacts=[
                {'value': form_data.get('phone'), 'field_id': 771220, 'enum_code': 'WORK'},
                {'value': form_data.get('email'), 'field_id': 771222, 'enum_code': 'WORK'},
            ],
            tags=form_data['tags'],
            referrer=form_data['utm_referer'],
            utm=utm_dict,
            custom_fields_values=[{
                "field_id": 957691,
                "values": [
                    {
                        "value": form_data['diagnosis']
                    }
                ]
            }]
        )
        added_lead_data = lead_added.json()
        try:
            lead_id = int(added_lead_data[0]['id'])
            note_text = ''
            for k, v in form_data.items():
                note_text = f"{form_data}\n{k} :: {v}"
            amo_client.add_note_simple(entity_id=lead_id, text=note_text.strip())
        except:
            pass
        # {
        #     'name': 'test me',
        #     'phone': '963258741',
        #     'diagnosis': 'sdfsdg',
        #     'email': 'Kirill.Mizonov@swissmedica21.com',
        #     'agree': 'on',
        #     'clientid': '864083159.1695878461',
        #     'pipeline_id': 2047060,
        #     'status_id': 29830081,
        #     'tags': [{'id': 689053}],
        #     'message': 'sdfsdg',
        #     'detected_country': 'not_detected_country',
        #     'detected_city': 'not_detected_city'
        # }

    except Exception as exc:
        print('error', exc)

    return Response(status=200)


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


@bp.route('/new_raw_lead', methods=['POST'])
def new_raw_lead():
    """ В Amo пришел новый лид, его данные необходимо записать в RawLeadData """
    data = get_data_from_post_request(_request=request)
    if not data:
        return 'Unsupported Media Type', 415
    lead_id = data.get('leads[add][0][id]')
    if not lead_id:
        return Response(status=204)
    branch = data.get('account[subdomain]')
    # вытаскиваем данные сделки и контакта
    amo_client = API_CLIENT.get(branch)()
    lead = amo_client.get_lead_by_id(lead_id=lead_id) or {}
    contacts = (lead.get('_embedded') or {}).get('contacts')
    contact = amo_client.get_contact_by_id(contact_id=contacts[0]['id']) if contacts else {}
    # добавляем запись в RawLeadData
    raw_lead_model: Type[Union[SMRawLeadData, CDVRawLeadData]] = RAW_LEAD.get(branch)
    app = current_app._get_current_object()
    with app.app_context():
        raw_lead_model.add(
            id_on_source=lead['id'],
            created_at=lead['created_at'],
            updated_at=lead['updated_at'],
            data=DateTimeEncoder.encode({
                'lead': lead,
                'contact': contact
            })
        )
    return Response(status=204)


@bp.route('/get_amo_data_sm')
def get_amo_data_sm():
    return start_get_data_from_amo_scheduler(branch='sm')


@bp.route('/amo_chat/<scope_id>', methods=['POST'])
def amo_chat(scope_id):
    """ Пришло сообщение из Amo Chat:
        менеджер через интерфейс Amo написал клиенту - нам нужно переслать сообщение в WhatsApp
        Формат данных:
            {'account_id': '59a2fb56-7492-4c16-8bbe-f776345af46c', 'time': 1700951116, 'message': {'receiver': {'id': '8cab93ac-a6cc-40c7-9021-989ae3629bb1', 'name': 'Kirill Mizonow', 'phone': '995591058618', 'client_id': '995591058618'}, 'sender': {'id': 'ab8317cd-eb38-4bf4-8462-47a4b328a887', 'name': 'Василий Админ'}, 'conversation': {'id': '988b9688-e8b9-47ed-8eb8-2339dffd4f17', 'client_id': 'cc5d7525-6e8d-4cd1-8ace-e09900e88ea1'}, 'timestamp': 1700951116, 'msec_timestamp': 1700951116276, 'message': {'id': '527af4d5-2a69-48b2-87f0-b665f4bd2b9c', 'type': 'text', 'text': 'should work', 'markup': None, 'tag': '', 'media': '', 'thumbnail': '', 'file_name': '', 'file_size': 0}}}
    Args:
        scope_id: идентификатор, позволяющий судить о том, с какого аккаунта Amo прилетели данные
    """
    # print('got info from AMO Chat', scope_id, request.json)
    data = request.json
    message = data.get('message')
    if not message:
        return Response(status=204)
    receiver = message['receiver']['phone']
    msg = message['message']['text']
    # по scope_id определяем аккаунт
    for branch, config in Config().amo_chat.items():
        if config.get('scope_id') == scope_id:
            # будет выбран первый номер из списка (переменная WHATSAPP) для данного филиала
            WhatsAppController(branch=branch).send_message(number_to=receiver, message=msg)
            break
    return Response(status=204)


@bp.route('/get_amo_data_cdv')
def get_amo_data_cdv():
    return start_get_data_from_amo_scheduler(branch='cdv')


@bp.route('/tawk', methods=['POST'])
def tawk():
    return TawkController().handle(request=request)


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
    from app.models.raw_lead_data import SMRawLeadData, CDVRawLeadData
    with current_app.app_context():
        db.create_all()
    return 'tables created'


@bp.route('/drop_all')
def drop_all():
    with current_app.app_context():
        db.drop_all()
    return 'tables dropped'
