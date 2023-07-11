""" Маршруты для работы Telegram-ботов """
__author__ = 'ke.mizonov'
import telebot
from flask import redirect, url_for, request
from app.main import bp
from app.main.utils import handle_new_lead
from config import Config

sm_telegram_bot = telebot.TeleBot(Config.SM_TELEGRAM_BOT_TOKEN)


@sm_telegram_bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    sm_telegram_bot.reply_to(message, f'CHAT_ID={message.chat.id}')


@bp.route("/send_message/<chat_id>/<message>")
def send_message_sm(chat_id, message):
    sm_telegram_bot.send_message(chat_id, message)
    return 'success', 200


@bp.route('/set_telegram_webhooks')
def set_telegram_webhooks():
    sm_telegram_bot.remove_webhook()
    sm_telegram_bot.set_webhook(url=Config.HEROKU_URL + Config.SM_TELEGRAM_BOT_TOKEN)
    return "!", 200


@bp.route('/new_lead_sm', methods=['POST'])
def new_lead_sm():
    if request.content_type == 'application/json':
        data = request.json
    elif request.content_type == 'application/x-www-form-urlencoded':
        data = request.form.to_dict()
    else:
        return 'Unsupported Media Type', 415
    endpoint = 'main.send_message_sm'
    return redirect(url_for(
        endpoint,
        chat_id=Config.NEW_LEADS_CHAT_ID_SM,
        message=handle_new_lead(data=data)
    ))


@bp.route('/' + Config.SM_TELEGRAM_BOT_TOKEN, methods=['POST'])
def get_message_sm():
    sm_telegram_bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "!", 200
