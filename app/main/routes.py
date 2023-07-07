import os
from datetime import datetime, timedelta
import telebot
from apscheduler.jobstores.base import JobLookupError
from flask import render_template, current_app, redirect, url_for, request, send_file
from app import db, socketio
from app.amo.api.client import SwissmedicaAPIClient, DrvorobjevAPIClient
from app.main import bp
from app.main.processors import DATA_PROCESSOR
from app.main.tasks import get_data_from_amo, update_pivot_data
from app.main.utils import handle_lead_status_changed, handle_autocall_result, handle_new_lead
from app.models.data import SMData
from app.utils.excel import ExcelClient
from config import Config
from modules.external.sipuni.sipuni_api import Sipuni

API_CLIENT = {
    'SM': SwissmedicaAPIClient,
    'CDV': DrvorobjevAPIClient,
}

sm_telegram_bot = telebot.TeleBot(Config.SM_TELEGRAM_BOT_TOKEN)


@socketio.on('connect')
def pre_load_from_socket():
    """ Предзагрузка данных через сокет в момент установки соединения """
    # вытаскиваем логи
    logs = []
    for processor_entity in DATA_PROCESSOR.values():
        processor = processor_entity()
        logs.extend(processor.log.get() or [])
    logs = sorted([log for log in logs], key=lambda x: x.created_at)
    for log in logs:
        dt = datetime.fromtimestamp(log.created_at).strftime("%Y-%m-%d %H:%M:%S")
        socketio.emit('new_event', {'msg': f"{dt} :: {log.text}"})


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


@bp.route("/send_message/<chat_id>/<message>")
def send_message_sm(chat_id, message):
    sm_telegram_bot.send_message(chat_id, message)
    return 'success', 200


@bp.route('/set_telegram_webhooks')
def set_telegram_webhooks():
    sm_telegram_bot.remove_webhook()
    sm_telegram_bot.set_webhook(url=Config.HEROKU_URL + Config.SM_TELEGRAM_BOT_TOKEN)
    return "!", 200


@bp.route('/add_to_autocall')
def add_to_autocall():
    client = Sipuni(Config.SUPUNI_ID_CDV, Config.SIPUNI_KEY_CDV)
    client.add_number_to_autocall(number='995591058618', autocall_id=Config.SIPUNI_AUTOCALL_ID_CDV)
    start_autocall()
    return redirect(url_for('main.index'))


@sm_telegram_bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    sm_telegram_bot.reply_to(message, f'CHAT_ID={message.chat.id}')


@bp.route('/start_autocall')
def start_autocall():
    # client = Sipuni(Config.SUPUNI_ID_CDV, Config.SIPUNI_KEY_CDV)
    # client.start_autocall(autocall_id=Config.SIPUNI_AUTOCALL_ID_CDV)
    return redirect(url_for('main.index'))


@bp.route('/new_lead_sm', methods=['POST'])
def new_lead_sm():
    chat_id = Config.NEW_LEADS_CHAT_ID_SM
    endpoint = 'main.send_message_sm'
    if request.content_type == 'application/json':
        msg = handle_new_lead(data=request.json)
        return redirect(url_for(endpoint, chat_id=chat_id, message=msg))
    elif request.content_type == 'application/x-www-form-urlencoded':
        msg = handle_new_lead(data=request.form.to_dict())
        return redirect(url_for(endpoint, chat_id=chat_id, message=msg))
    return 'Unsupported Media Type', 415


@bp.route('/' + Config.SM_TELEGRAM_BOT_TOKEN, methods=['POST'])
def get_message_sm():
    sm_telegram_bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "!", 200


@bp.route('/autocall_handler_cdv', methods=['POST'])
def autocall_handler_cdv():
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
    branch = 'drvorobjev'
    if request.content_type == 'application/json':
        handle_autocall_result(data=request.json, branch=branch)
        return 'success', 200
    elif request.content_type == 'application/x-www-form-urlencoded':
        handle_autocall_result(data=request.form.to_dict(), branch=branch)
        return 'success', 200
    return 'Unsupported Media Type', 415


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


@bp.route('/handle_new_leads_cdv', methods=['POST'])
def handle_new_leads_cdv():
    if request.content_type == 'application/json':
        handle_lead_status_changed(data=request.json)
        return 'success', 200
    elif request.content_type == 'application/x-www-form-urlencoded':
        handle_lead_status_changed(data=request.form.to_dict())
        return 'success', 200
    return 'Unsupported Media Type', 415


@bp.route('/init_autocall_cdv', methods=['POST'])
def init_autocall_cdv():
    if request.content_type == 'application/json':
        handle_lead_status_changed(data=request.json)
        return 'success', 200
    elif request.content_type == 'application/x-www-form-urlencoded':
        handle_lead_status_changed(data=request.form.to_dict())
        return 'success', 200
    # else:
    #     processor = DATA_PROCESSOR.get('sm')()
    #     processor.log.add(
    #         text=f'Unsupported response: {request.content_type}. Data: {request.get_data(as_text=True)}'
    #     )
    return 'Unsupported Media Type', 415


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
    # return 'started scheduler "get data from amo"'


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
    # ипорты нужны для создания структуры БД!
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
