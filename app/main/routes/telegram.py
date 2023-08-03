""" Маршруты для работы Telegram-ботов """
__author__ = 'ke.mizonov'
from typing import Optional, Dict, Callable
import telebot
from flask import request, current_app, render_template
from app.main import bp
from app.main.utils import handle_new_lead, handle_autocall_success, handle_get_in_touch
from config import Config

BOTS = {
    pipeline_or_branch: telebot.TeleBot(params['TOKEN'])
    for pipeline_or_branch, params in Config().new_lead_telegram.items()
    if params.get('TOKEN')
}


def get_data_from_post_request(_request) -> Optional[Dict]:
    if request.content_type == 'application/json':
        return _request.json
    elif request.content_type == 'application/x-www-form-urlencoded':
        return _request.form.to_dict()
    else:
        return None


def reply_on_lead_event(_request, msg_builder: Callable):
    data = get_data_from_post_request(_request=_request)
    if not data:
        return 'Unsupported Media Type', 415
    pipeline_id, message = msg_builder(data=data)
    if not message:
        # если сообщения нет, ничего не делаем
        return 'Ok', 200
    config = Config()
    # в параметрах содержится идентификатор чата; вероятно, есть параметры конкретной воронки (по дефолту - филиала)
    branch = data.get('account[subdomain]')
    params = config.new_lead_telegram.get(pipeline_id)
    if params:
        bot_key = pipeline_id
    else:
        params = config.new_lead_telegram.get(branch)
        bot_key = branch
    if not params:
        return 'Bot not found', 404
    BOTS[bot_key].send_message(params.get('CHAT_ID'), message)
    return 'Ok', 200


def make_send_welcome_handler(tg_bot):
    @tg_bot.message_handler(commands=['start', 'help'])
    def send_welcome(message):
        tg_bot.reply_to(message, f'CHAT_ID={message.chat.id}')
    return send_welcome


# def make_buttons_handlers(tg_bot):
#     @tg_bot.callback_query_handler(func=lambda call: True)
#     def handle_button_click(call):
#         if call.data == 'btn_test':
#             tg_bot.send_message(call.message.chat.id, "Button clicked!")
#         elif call.data == 'button2':
#             tg_bot.send_message(call.message.chat.id, "Button 2 clicked!")
#     return handle_button_click


for bot in BOTS.values():
    make_send_welcome_handler(bot)
    # make_buttons_handlers(bot)


@bp.route('/set_telegram_webhooks')
def set_telegram_webhooks():
    config = Config()
    # app = current_app._get_current_object()
    print(f'BOTS {BOTS}')
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
        # keyboard = telebot.types.InlineKeyboardMarkup()
        # button1 = telebot.types.InlineKeyboardButton(text="Button 1", callback_data="btn_test")
        # button2 = telebot.types.InlineKeyboardButton(text="Button 2", callback_data="button2")
        # keyboard.row(button1, button2)
        # processor = DATA_PROCESSOR.get(pipeline_or_branch)
        # if not processor:
        #     print('NO PROCESSOR FOR', pipeline_or_branch)
        #     continue
        # with app.app_context():
        #     processor.log.add(text=f'Telegram webhooks were set')
    return render_template('index.html')


@bp.route('/new_lead', methods=['POST'])
def new_lead():
    print('calling new_lead handler')
    return reply_on_lead_event(_request=request, msg_builder=handle_new_lead)


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
