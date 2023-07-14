""" Маршруты для работы Telegram-ботов """
__author__ = 'ke.mizonov'
from typing import Optional, Dict, Callable
import telebot
from flask import redirect, url_for, request
from app.main import bp
from app.main.utils import handle_new_lead, handle_autocall_success
from config import Config

BOTS = {
    pipeline_or_branch: telebot.TeleBot(params['TOKEN'])
    for pipeline_or_branch, params in Config.NEW_LEAD_TELEGRAM.items()
    if params.get('TOKEN')
}


def get_data_from_post_request(_request) -> Optional[Dict]:
    if request.content_type == 'application/json':
        return _request.json
    elif request.content_type == 'application/x-www-form-urlencoded':
        return _request.form.to_dict()
    else:
        return None


def reply_on_new_lead(_request, msg_builder: Callable):
    data = get_data_from_post_request(_request=_request)
    if not data:
        return 'Unsupported Media Type', 415
    branch = data.get('account[subdomain]')
    pipeline_id, message = msg_builder(data=data)
    # в параметрах содержится идентификатор чата; вероятно, есть параметры конкретной воронки (по дефолту - филиала)
    params = Config.NEW_LEAD_TELEGRAM.get(pipeline_id)
    if params:
        bot_key = pipeline_id
    else:
        params = Config.NEW_LEAD_TELEGRAM.get(branch)
        bot_key = branch
    if not params:
        return 'Bot not found', 404
    return redirect(url_for(
        'main.send_message',
        bot_key=bot_key,
        chat_id=params.get('CHAT_ID'),
        message=message
    ))


def make_send_welcome_handler(tg_bot):
    @tg_bot.message_handler(commands=['start', 'help'])
    def send_welcome(message):
        tg_bot.reply_to(message, f'CHAT_ID={message.chat.id}')
    return send_welcome


for bot in BOTS.values():
    make_send_welcome_handler(bot)


@bp.route('/test_telegram')
def test_telegram():
    return redirect(url_for(
        'main.send_message',
        bot_key="drvorobjev",
        chat_id="-983109006",
        message='test cdv'
    ))


@bp.route("/<bot_key>/send_message/<chat_id>/<message>")
def send_message(bot_key, chat_id, message):
    if bot_key not in BOTS:
        return 'Bot not found', 404
    print(f'Bot key: {bot_key}, Chat id: {chat_id}, msg: {message}')
    BOTS[bot_key].send_message(chat_id, message)
    return 'success', 200


@bp.route('/set_telegram_webhooks')
def set_telegram_webhooks():
    for pipeline_or_branch, _bot in BOTS.items():
        _bot.remove_webhook()
        token = Config.NEW_LEAD_TELEGRAM.get(pipeline_or_branch).get('TOKEN')
        _bot.set_webhook(url=Config.HEROKU_URL + token)
    return "Telegram webhooks were configured", 200


@bp.route('/new_lead', methods=['POST'])
def new_lead():
    return reply_on_new_lead(_request=request, msg_builder=handle_new_lead)


@bp.route('/autocall_success', methods=['POST'])
def autocall_success():
    return reply_on_new_lead(_request=request, msg_builder=handle_autocall_success)


@bp.route('/<bot_token>', methods=['POST'])
def get_message(bot_token):
    _bot = None
    for pipeline_or_branch, params in Config.NEW_LEAD_TELEGRAM.items():
        if params.get('TOKEN') == bot_token:
            _bot = BOTS.get(pipeline_or_branch)
            break
    if not _bot:
        return "Invalid bot token", 400
    _bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "!", 200
