""" Маршруты для работы Telegram-ботов """
__author__ = 'ke.mizonov'
from typing import Dict, Callable
import telebot
from flask import request, current_app, Response

from app.amo.api.client import SwissmedicaAPIClient
from app.amo.processor.processor import SMDataProcessor
from app.main import bp
from app.main.routes.utils import get_data_from_post_request
from app.main.utils import handle_new_lead, handle_autocall_success, handle_get_in_touch, DATA_PROCESSOR, \
    handle_new_lead_slow_reaction, get_data_from_external_api, handle_new_interaction, DUP_TAG, \
    check_for_duplicated_leads
from config import Config
from modules.constants.constants.constants import GoogleSheets
from modules.google_api.google_api.client import GoogleAPIClient

BOTS = {
    pipeline_or_branch: telebot.TeleBot(params['TOKEN'])
    for pipeline_or_branch, params in Config().new_lead_telegram.items()
    if params.get('TOKEN')
}


def reply_on_lead_event(_request, msg_builder: Callable):
    data = get_data_from_post_request(_request=_request)
    if not data:
        return 'Unsupported Media Type', 415
    chat_key, pipeline_id, message = msg_builder(data=data)
    if not message:
        # если сообщения нет, ничего не делаем
        return 'Ok', 200
    config = Config()
    # в параметрах содержится идентификатор чата; вероятно, есть параметры конкретной воронки (по дефолту - филиала)
    branch = data.get('account[subdomain]') or data.get('branch')
    params = config.new_lead_telegram.get(pipeline_id)
    if params:
        bot_key = pipeline_id
    else:
        params = config.new_lead_telegram.get(branch)
        bot_key = branch
    if not params:
        return 'Bot not found', 404
    BOTS[bot_key].send_message(params.get(chat_key), message)
    return 'Ok', 200


def make_send_welcome_handler(tg_bot):
    @tg_bot.message_handler(commands=['start', 'help'])
    def send_welcome(message):
        tg_bot.reply_to(message, f'CHAT_ID={message.chat.id}')
    return send_welcome


def make_buttons_handlers(tg_bot):
    @tg_bot.callback_query_handler(func=lambda call: True)
    def handle_button_click(call):
        if call.data == 'btn_test':
            tg_bot.send_message(call.message.chat.id, "Button clicked!")
        elif call.data == 'button2':
            tg_bot.send_message(call.message.chat.id, "Button 2 clicked!")
    return handle_button_click


for bot in BOTS.values():
    make_send_welcome_handler(bot)
    make_buttons_handlers(bot)


@bp.route('/set_telegram_webhooks')
def set_telegram_webhooks():
    config = Config()
    app = current_app._get_current_object()
    for pipeline_or_branch, _bot in BOTS.items():
        try:
            _bot.remove_webhook()
        except Exception as exc:
            print('_bot.remove_webhook error:', exc)
        token = config.new_lead_telegram.get(pipeline_or_branch).get('TOKEN')
        try:
            _bot.set_webhook(url=config.heroku_url + token)
        except Exception as exc:
            print('_bot.set_webhook error:', exc)
        keyboard = telebot.types.InlineKeyboardMarkup()
        button1 = telebot.types.InlineKeyboardButton(text="Button 1", callback_data="btn_test")
        button2 = telebot.types.InlineKeyboardButton(text="Button 2", callback_data="button2")
        keyboard.row(button1, button2)
        processor = DATA_PROCESSOR.get(pipeline_or_branch)
        if not processor:
            print('NO PROCESSOR FOR', pipeline_or_branch)
            continue
        with app.app_context():
            processor().log.add(text=f'Telegram webhooks were set')
    return Response(status=204)
    # return render_template('index.html')


@bp.route('/new_lead', methods=['POST'])
def new_lead():
    return reply_on_lead_event(_request=request, msg_builder=handle_new_lead)


@bp.route('/new_lead_sm', methods=['POST'])
def new_lead_sm():
    """ Отправляет оповещение о новых лидах / перемещении лидов в Telegram

    Notes:
        По текущим настройкам работает с ботом sm_leads_informer_bot
    """
    # из GET-параметров вытаскиваем идентификаторы чатов, в которые нужно написать
    #   Строка должна выглядеть так: /new_lead_sm?channels=-948431515,-4069329874
    chat_ids = [int(x) for x in (request.args.get('channels') or '').split(',') if x]
    # предобработка данных запроса
    data = get_data_from_post_request(_request=request)
    if not data:
        return 'Unsupported Media Type', 415
    # определяем тип события - либо добавили новый лид, либо переместили существующий
    lead_id = data.get('leads[add][0][id]')
    event = 'New lead'
    key = 'add'
    if not lead_id:
        event = 'Lead moved'
        key = 'status'
        lead_id = data.get(f'leads[{key}][0][id]')
    if not lead_id:
        return 'Ok', 200
    # поддомен (swissmedica) получаем из запроса
    branch = data.get('account[subdomain]')
    # API-клиент для обращения к Amo
    amo_client = SwissmedicaAPIClient()
    # получаем лид
    lead = amo_client.get_lead_by_id(lead_id=lead_id)
    # получаем пользователя, ответственного за лид
    user = amo_client.get_user(_id=lead.get('responsible_user_id'))
    # получаем названия воронки и статуса
    pipeline = amo_client.get_pipeline_and_status(
        pipeline_id=data.get(f'leads[{key}][0][pipeline_id]'),
        status_id=data.get(f'leads[{key}][0][status_id]')
    )
    # получаем теги
    existing_tags = [
        {'name': tag['name']}
        for tag in (lead.get('_embedded') or {}).get('tags') or []
        if tag['name'] != DUP_TAG
    ]
    tags_str = ', '.join([tag['name'] for tag in existing_tags])
    if tags_str:
        tags_str = f'{tags_str}'
    # проверка на дубли (находит первый дубль из возможных)
    duplicate = check_for_duplicated_leads(
        processor=SMDataProcessor(),
        lead=lead,
        amo_client=amo_client,
        branch=branch,
        existing_tags=existing_tags
    )
    message = f"{pipeline.get('pipeline') or ''} :: {pipeline.get('status') or ''}\n" \
              f"{event}: https://{branch}.amocrm.ru/leads/detail/{lead_id}\n" \
              f"Tags: {tags_str}\n" \
              f"Responsible: {user.get('name') or ''}\n" \
              f"{duplicate}".strip()
    telegram_bot_token = Config().sm_telegram_bot_token
    for chat_id in chat_ids:
        telebot.TeleBot(telegram_bot_token).send_message(chat_id, message)
    return 'Ok', 200


@bp.route('/new_communication_sm', methods=['POST'])
def new_communication_sm():
    """
    {'leads[call_in][0][id]': '34484349', 'leads[call_in][0][status_id]': '19045762', 'leads[call_in][0][pipeline_id]': '772717', 'account[id]': '9884604', 'account[subdomain]': 'swissmedica'}
    Returns:

    """
    # из GET-параметров вытаскиваем идентификаторы чатов, в которые нужно написать
    #   Строка должна выглядеть так: /new_communication_sm?channels=-948431515,-4069329874
    chat_ids = [int(x) for x in (request.args.get('channels') or '').split(',') if x]
    # предобработка данных запроса
    data = get_data_from_post_request(_request=request)
    if not data:
        return 'Unsupported Media Type', 415
    # входящий звонок или входящее письмо
    new_call = data.get('leads[call_in][0][id]')
    new_mail = data.get('leads[mail_in][0][id]')
    event = 'New call' if new_call else ''
    if not event:
        event = 'New email' if new_mail else ''
    lead_id = new_call or new_mail
    if not lead_id:
        return 'Ok', 200
    # поддомен (swissmedica) получаем из запроса
    branch = data.get('account[subdomain]')
    # API-клиент для обращения к Amo
    amo_client = SwissmedicaAPIClient()
    # получаем лид
    lead = amo_client.get_lead_by_id(lead_id=lead_id)
    # получаем пользователя, ответственного за лид
    user = amo_client.get_user(_id=lead.get('responsible_user_id'))
    # получаем названия воронки и статуса
    pipeline = amo_client.get_pipeline_and_status(
        pipeline_id=data.get(f'leads[call_in][0][pipeline_id]') or data.get(f'leads[mail_in][0][pipeline_id]'),
        status_id=data.get(f'leads[call_in][0][status_id]') or data.get(f'leads[mail_in][0][status_id]')
    )
    # получаем теги
    existing_tags = [
        {'name': tag['name']}
        for tag in (lead.get('_embedded') or {}).get('tags') or []
        if tag['name'] != DUP_TAG
    ]
    tags_str = ', '.join([tag['name'] for tag in existing_tags])
    if tags_str:
        tags_str = f'{tags_str}'
    # тегаем пользователя через @
    telegram_name = None
    managers = GoogleAPIClient(book_id=GoogleSheets.Managers.value, sheet_title='managers').get_sheet()
    for manager in managers:
        if manager.get('manager') == user:
            telegram_name = manager.get('telegram')
            break
    telegram_name = f"@{telegram_name}" if telegram_name else ''
    message = f"{pipeline.get('pipeline') or ''} :: {pipeline.get('status') or ''}\n" \
              f"{event}: https://{branch}.amocrm.ru/leads/detail/{lead_id}\n" \
              f"Tags: {tags_str}\n" \
              f"Responsible: {telegram_name or user.get('name') or ''}".strip()
    telegram_bot_token = Config().sm_telegram_bot_token
    for chat_id in chat_ids:
        telebot.TeleBot(telegram_bot_token).send_message(chat_id, message)
    return 'Ok', 200


@bp.route('/missed_call_sm', methods=['POST'])
def missed_call_sm():
    """ Обработка результата пропущенного звонка (Sipuni)

    Args:
        data: данные, пришедшие через webhook в формате
            {
              "call_args": {
                "call_id": "1698153245.6379",
                "event": 2,
                "dst_type": 1,
                "dst_num": "74996470000",
                "src_type": 1,
                "src_num": "74996470001",
                "timestamp": "1698153245",
                "pbx_user_id": "187484",
                "is_autocall": false,
                "operator_name": "Николай Смирнов",
                "status": "NOANSWER",
                "call_start_timestamp": "1698153235",
                "call_record_link": "https://commons.wikimedia.org/wiki/File:Heart_Monitor_Beep--freesound.org.mp3",
                "line_number": "74996470000",
                "line_name": "Общая",
                "tree_name": "Входащая",
                "tree_number": "00090001"
              },
    Notes:
        Запрос отправляется через Node.js функцию со стороны Sipuni
    """
    # из GET-параметров вытаскиваем идентификаторы чатов, в которые нужно написать
    #   Строка должна выглядеть так: /missed_call_sm?channels=-948431515,-4069329874
    chat_ids = [int(x) for x in (request.args.get('channels') or '').split(',') if x]
    # предобработка данных запроса
    data = get_data_from_post_request(_request=request)
    if not data:
        return 'Unsupported Media Type', 415
    message = f"Missed call: {data['src_num']}"
    telegram_bot_token = Config().sm_telegram_bot_token
    for chat_id in chat_ids:
        telebot.TeleBot(telegram_bot_token).send_message(chat_id, message)
    return 'Ok', 200


@bp.route('/new_lead_slow_reaction', methods=['POST'])
def new_lead_slow_reaction():
    return reply_on_lead_event(_request=request, msg_builder=handle_new_lead_slow_reaction)


@bp.route('/new_interaction', methods=['POST'])
def new_interaction():
    return reply_on_lead_event(_request=request, msg_builder=handle_new_interaction)


@bp.route('/autocall_success', methods=['POST'])
def autocall_success():
    return reply_on_lead_event(_request=request, msg_builder=handle_autocall_success)


@bp.route('/get_in_touch', methods=['POST'])
def get_in_touch():
    return reply_on_lead_event(_request=request, msg_builder=handle_get_in_touch)


@bp.route('/<bot_token>', methods=['POST'])
def get_message(bot_token):
    _bot = None
    for pipeline_or_branch, params in Config().new_lead_telegram.items():
        if params.get('TOKEN') == bot_token:
            _bot = BOTS.get(pipeline_or_branch)
            break
    if not _bot:
        return "Invalid bot token", 400
    _bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "!", 200


@bp.route('/missed_call_handler', methods=['POST'])
def missed_call_handler():
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
    # deprecated
    return get_data_from_external_api(
        request=request,
        handler_func=handle_missed_call_result,
    )


def handle_missed_call_result(data: Dict):
    """ Обработка результата пропущенного звонка (Sipuni)

    Args:
        data: данные, пришедшие через webhook в формате
            {
              "call_args": {
                "call_id": "1698153245.6379",
                "event": 2,
                "dst_type": 1,
                "dst_num": "74996470000",
                "src_type": 1,
                "src_num": "74996470001",
                "timestamp": "1698153245",
                "pbx_user_id": "187484",
                "is_autocall": false,
                "operator_name": "Николай Смирнов",
                "status": "NOANSWER",
                "call_start_timestamp": "1698153235",
                "call_record_link": "https://commons.wikimedia.org/wiki/File:Heart_Monitor_Beep--freesound.org.mp3",
                "line_number": "74996470000",
                "line_name": "Общая",
                "tree_name": "Входащая",
                "tree_number": "00090001"
              },
    """
    def missed_call_msg_builder(**kwargs):
        return (
            'MISSED_CALL',
            None,
            f"Missed call: {data['src_num']}"
        )
    reply_on_lead_event(_request=request, msg_builder=missed_call_msg_builder)
