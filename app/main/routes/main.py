""" Общие маршруты """
__author__ = 'ke.mizonov'
from datetime import datetime
from typing import Union, Type, Dict, Optional
from flask import render_template, current_app, redirect, url_for, request, Response, flash, jsonify
from flask_login import login_required, logout_user, current_user, login_user
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, socketio
from app.amo.api.client import SwissmedicaAPIClient, DrvorobjevAPIClient
from app.amo.processor.processor import GoogleSheets, SMDataProcessor
from app.google_api.client import GoogleAPIClient
from app.main import bp
from app.main.arrival.handler import waiting_for_arrival
from app.main.auth.form import RegistrationForm
from app.main.auth.utils import requires_roles
from app.main.leads_insurance.handler import LeadsInsurance
from app.main.processors import DATA_PROCESSOR
from app.main.routes.utils import get_data_from_post_request, get_args_from_url, add_if_not_exists, \
    create_view_excluding_columns
from app.main.utils import DateTimeEncoder
from app.models.app_user import SMAppUser
from app.models.chat import SMChat, CDVChat
from app.models.data import SMData, CDVData
from app.models.raw_lead_data import SMRawLeadData, CDVRawLeadData
from app.tawk.controller import TawkController
from app.utils.country_by_ip import get_country_by_ip
from app.whatsapp.controller import WhatsAppController
from config import Config
from modules.utils.utils.functions import clear_phone


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


@bp.route('/')
@requires_roles('admin', 'superadmin')
def index():
    return render_template('index.html')


@bp.route('/menu')
@login_required
def menu():
    return render_template('menu.html')


@bp.route('/get_token', methods=['GET'])
def get_token():
    return render_template('get_token.html')


@bp.route('/arrival_sync', methods=['GET'])
def arrival_sync():
    app = current_app._get_current_object()
    waiting_for_arrival(app=app, branch='swissmedica')
    return render_template('arrival_sync.html')


@bp.route('/swissmedica_org_lead', methods=['POST', 'GET'], strict_slashes=False)
def swissmedica_org_lead():
    """ Пробрасывавет в AMO лиды с сайта swissmedica.org """
    """
    {
        'Name': 'test - please ignore',
        'Clients_Country': 'Georgia',
        'Email': 'Kir@swissmedica21.com',
        'Phone': '591058618',
        'Please_describe_your_problem': 'test - please ignore',
        'Checkbox': 'yes',
        'LP4_EN': 'LP4_EN',
        'tranid': '725354:5774608671',
        'COOKIES': ' _fbp=fb.1.1692261723692.1607646662; _ym_uid=1692261724710250210; _ym_d=1692261724; tildauid=1692261725123.513957; _gcl_au=1.1.523246661.1701948890; rerf=AAAAAGW6VFwObn+DAzEeAg==; _gid=GA1.2.164053568.1706710111; _ym_isad=2; _ym_visorc=w; tildasid=1706765241461.327595; _uetsid=fb0967f0c04211ee83e401378e0b8d50; _uetvid=fb098570c04211eeaed7851553f3f724; _gat_gtag_UA_148716138_1=1; _ga=GA1.1.601091886.1692261724; previousUrl=swissmedica.org%2Finnovative-therapy; _ga_XXMR2575TF=GS1.1.1706765238.15.1.1706769087.31.0.0',
        'formid': 'form480544796'
    }
    """
    # config = Config().swissmewdica_org_forms
    data: Dict = request.json
    print('swissmedica_org_lead', data)
    # определяем идентификатор формы
    # cookies = data.get('COOKIES')       # здесь приходит строка!!
    # form_id = data.get('formid')
    # form_config = config.get(form_id) or {}
    # записываем данные в google-таблицу
    append_form_data_to_google_sheets(form_data={
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'source': f"swissmedica.org {data.get('Clients_Country') or ''}".strip(),
        'name': data.get('Name') or data.get('name') or '',
        'phone': data.get('Phone') or data.get('phone') or '',
        'email': data.get('Email') or data.get('email') or '',
        'msg': data.get('Please_describe_your_problem') or ''
    })
    # # для части форм сделки в Amo не создаем (флаг 'l' != 1)
    # if not form_config or form_config['l'] != 1:
    #     print('swissmedica_org_lead config error')
    #     return Response(status=200)
    # create_lead_based_on_form_data(
    #     lang=form_config['r'],  # регион / язык, ключ "r"
    #     ip=data.get('ip'),
    #     headers=dict(request.headers) or {},        # тут есть сомнения насчет формата
    #     name=data.get('Name'),
    #     phone=clear_phone(data.get('Phone') or ''),
    #     email=data.get('Email') or '',
    #     diagnosis=data.get('Please_describe_your_problem') or '',
    #     country_=data.get('Clients_Country')
    # )
    return Response(status=200)


@bp.route('/startstemcells_lead', methods=['POST', 'GET'], strict_slashes=False)
def startstemcells_lead():
    """ Пробрасывавет в AMO лиды с сайта startstemcells.com """
    config = Config().startstemcells_forms
    data: Dict = request.json
    form_data = data.get('post') or {}
    print('startstemcells_lead', form_data)
    # определяем идентификатор формы
    form_id = form_data.get('_hf_form_id')
    form_config = config.get(form_id) or {}
    # записываем данные в google-таблицу
    append_form_data_to_google_sheets(form_data={
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'source': f"startstemcells {form_config.get('r') or ''}".strip(),
        'name': form_data.get('name') or '',
        'phone': form_data.get('phone') or '',
        'email': form_data.get('email') or '',
        'msg': form_data.get('diagnosis') or form_data.get('message') or form_data.get('msg') or ''
    })
    # проверяем лид на спам
    is_spam = False
    phone = clear_phone(form_data.get('phone') or '')
    email = form_data.get('email') or ''
    msg = form_data.get('diagnosis') or form_data.get('message') or form_data.get('msg') or ''
    try:
        is_spam = LeadsInsurance(branch='swissmedica').is_spam(line={'phone': phone, 'email': email, 'msg': msg})
    except Exception as exc:
        print('failed to perform spam check', exc)
    if is_spam:
        print('spam lead detected')
        return Response(status=200)
    # для части форм сделки в Amo не создаем (флаг 'l' != 1)
    if not form_config or form_config['l'] != 1:
        print('startstemcells_lead config error')
        return Response(status=200)
    utm_dict = {
        'utm_source': form_data.get('utm_source') or '',
        'utm_medium': form_data.get('utm_medium') or '',
        'utm_campaign': form_data.get('utm_campaign') or '',
        'utm_content': form_data.get('utm_content') or '',
        'utm_term': form_data.get('utm_term') or '',
        'referer': form_data.get('referer') or '',
        'ym_cid': form_data.get('ym_cid') or '',
        'lead_url': form_data.get('lead_url') or ''
    }
    create_lead_based_on_form_data(
        lang=form_config['r'],  # регион / язык, ключ "r"
        ip=data.get('ip') or (data.get('location') or {}).get('ip'),
        headers=data.get('headers') or {},
        cookies=data.get('cookies') or {},
        name=form_data.get('name'),
        phone=phone,
        email=email,
        diagnosis=msg,
        utm_dict=utm_dict
    )
    return Response(status=200)


def append_form_data_to_google_sheets(form_data):
    if len(form_data) != 6:
        return
    for key in ('date', 'source', 'name', 'phone', 'email', 'msg'):
        if key not in form_data:
            return
    try:
        GoogleAPIClient(
            book_id=GoogleSheets.LeadsFromSites.value,
            sheet_title='Leads'
        ).add_row(form_data)
    except Exception as exc:
        print(exc)


def create_lead_based_on_form_data(
    lang: str,
    ip: str,
    headers: Dict,
    cookies: Dict,
    name: str,
    phone: str,
    email: str,
    diagnosis: str,
    country_: Optional[str] = None,
    utm_dict: Optional[Dict] = None
):
    referer = headers.get('Referer') or ''
    origin = headers.get('Origin') or headers.get('origin') or ''
    site = origin.replace('https://', '').replace('http://', '')
    country_data = get_country_by_ip(ip=ip) if ip else {}
    country, city = country_data.get('country'), country_data.get('city')
    # если страну по ip не определили, но она указана явно
    if not country and country_:
        country = country_
    if not utm_dict:
        utm_dict = get_args_from_url(url=referer) if referer else {}
    spoken_language = {'EN': 'English', 'DE': 'German', 'FR': 'French', 'IT': 'Italian'}
    custom_fields_values = [
        # Spoken language
        {"field_id": 1099051, "values": [{"value": spoken_language.get(lang) or 'Another'}]},
        # Country_from_Jivo
        {"field_id": 976545, "values": [{"value": country}]},
        # City_from_Jivo
        {"field_id": 976549, "values": [{"value": city}]},
        # Disease if other
        {"field_id": 957691, "values": [{"value": diagnosis}]},
        # идентификатор яндекс-метрики
        # {"field_id": 1102815, "values": [{"value": cookies.get('_ym_uid') or cookies.get('_YM_UID')}]},
    ]
    # идентификаторы сущностей в Amo: p - pipeline, s - status, t - tag
    amo_ids = {
        'EN': {'p': 772717, 's': 19045762, 't': 689047},
        'DE': {'p': 2048428, 's': 29839168, 't': 689049},
        'FR': {'p': 2047060, 's': 29830081, 't': 689053},
        'IT': {'p': 5707270, 's': 50171236, 't': 689051},
        # пока что проброс в английскую воронку
        'CZ': {'p': 772717, 's': 19045762, 't': 689055}
    }
    # пустым конфиг не будет, по умолчанию всегда английская воронка
    amo_config = amo_ids.get(lang) or amo_ids.get('EN')
    amo_client = SwissmedicaAPIClient()
    # проверка на дубли
    # existing_leads = []
    # if phone:
    #     existing_leads = list(amo_client.find_leads(query=phone, limit=1))
    # if not existing_leads and email:
    #     existing_leads = list(amo_client.find_leads(query=email, limit=1))
    # lead_id = int(existing_leads[0]['id']) if existing_leads else None
    # if lead_id:
    #     # лид уже существует, отправим оповещение о том, что он попытался выйти на связь
    #     pass
    #     return Response(status=200)
    # добавляем лид
    response = amo_client.add_lead_simple(
        title=f"{name} :: {site}",
        name=name,
        pipeline_id=amo_config['p'],
        status_id=amo_config['s'],
        contacts=[
            {'value': phone, 'field_id': 771220, 'enum_code': 'WORK'},
            {'value': email, 'field_id': 771222, 'enum_code': 'WORK'},
        ],
        tags=[{'id': amo_config['t']}],
        utm=utm_dict,
        referer=referer,
        custom_fields_values=custom_fields_values,
        responsible_user_id=0
    )
    print('lead creation result', response.status_code, response.text)


@bp.route('/cellulestaminali_lead', methods=['POST', 'GET'], strict_slashes=False)
def cellulestaminali_lead():
    data: Dict = request.json
    form_data = data.get('post') or {}
    # записываем данные в google-таблицу
    append_form_data_to_google_sheets(form_data={
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'source': f"cellulestaminali {'IT'}".strip(),
        'name': form_data.get('name') or '',
        'phone': form_data.get('phone') or '',
        'email': form_data.get('email') or '',
        'msg': form_data.get('message') or ''
    })
    # проверяем лид на спам
    is_spam = False
    phone = clear_phone(form_data.get('phone') or '')
    email = form_data.get('email') or ''
    msg = form_data.get('diagnosis') or form_data.get('message') or form_data.get('msg') or ''
    try:
        is_spam = LeadsInsurance(branch='swissmedica').is_spam(line={'phone': phone, 'email': email, 'msg': msg})
    except Exception as exc:
        print('failed to perform spam check', exc)
    if is_spam:
        print('spam lead detected')
        return Response(status=200)
    utm_dict = {
        'utm_source': form_data.get('utm_source') or '',
        'utm_medium': form_data.get('utm_medium') or '',
        'utm_campaign': form_data.get('utm_campaign') or '',
        'utm_content': form_data.get('utm_content') or '',
        'utm_term': form_data.get('utm_term') or '',
        'referer': form_data.get('referer') or '',
        'ym_cid': form_data.get('ym_cid') or '',
        'lead_url': form_data.get('lead_url') or ''
    }
    create_lead_based_on_form_data(
        lang='IT',  # регион / язык, ключ "r"
        ip=data.get('ip'),
        headers=data.get('headers') or {},
        cookies=data.get('cookies') or {},
        name=form_data.get('name'),
        phone=phone,
        email=email,
        diagnosis=msg,
        utm_dict=utm_dict
    )
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


def data_to_excel(branch: str):
    model = DATA_MODEL.get(branch)
    portion_size = 1000
    offset = 0
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
        data = [
            x.to_dict().get('data')
            for x in collection
        ]
        num += 1
        socketio.emit('pivot_data', {
            'start': False,
            'data': data,
            'headers': headers,
            'done': False,
            'file_name': None
        })
        offset += portion_size
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


@bp.route('/tawk', methods=['POST'])
def tawk():
    return TawkController().handle(request=request)


@bp.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data)
        new_user = SMAppUser(
            username=form.username.data,
            email=form.email.data,
            password_hash=hashed_password,
            role_id=form.role.data.id
        )
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful.')
        return redirect(url_for('main.login'))
    return render_template('register.html', form=form)


@bp.route('/update_users_leads', methods=['GET'])
@login_required
def update_users_leads():
    SMDataProcessor().update_users_leads(app=current_app._get_current_object())
    return jsonify({'status': 'complete'})


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.menu'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = SMAppUser.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash('You have been logged in!', 'success')
            return redirect(url_for('main.menu'))
        else:
            flash('Login Unsuccessful. Please check username and password', 'danger')
    return render_template('login.html')


@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.login'))


@bp.route('/find_duplicates')
@login_required
def find_duplicates():
    return render_template('find_duplicates.html')


@socketio.on('find_lead_duplicates')
def handle_find_lead_duplicates(json):
    lead_id = json['lead_id']
    print('Received request to find duplicates for lead ID:', lead_id)
    # Отправляем тестовые данные обратно на клиент
    test_data = [{'id': 1, 'msg': 'Duplicate 1'}, {'id': 2, 'msg': 'Duplicate 2'}, {'id': 3, 'msg': 'Duplicate 3'}]
    for item in test_data:
        socketio.emit('duplicate_lead', item)


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
    from app.models.app_user import SMRole, CDVRole, SMAppUser, CDVAppUser
    from app.models.task import SMTask, CDVTask
    from app.models.company import SMCompany, CDVCompany
    from app.models.data import SMData, CDVData
    from app.models.log import SMLog, CDVLog
    from app.models.autocall import SMAutocallNumber, CDVAutocallNumber
    from app.models.chat import SMChat, CDVChat
    from app.models.raw_lead_data import SMRawLeadData, CDVRawLeadData
    with current_app.app_context():
        db.create_all()
        # добавляем роли
        session = db.session
        for model in (SMRole, CDVRole):
            for name in ('user', 'admin', 'superadmin', 'guest'):
                add_if_not_exists(session=session, model=model, filter_by={'name': name})
        # создаем представления
        create_view_excluding_columns(session, SMData, ['contacts', 'phone'])
        create_view_excluding_columns(session, CDVData, ['contacts', 'phone'])
    return 'tables created'


# @bp.route('/drop_all')
# def drop_all():
#     with current_app.app_context():
#         db.drop_all()
#     return 'tables dropped'
