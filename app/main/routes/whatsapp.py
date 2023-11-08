""" Маршруты для работы WhatsApp-ботов """
__author__ = 'ke.mizonov'
from typing import Optional
import requests
from flask import request, jsonify, Response

from app.amo.api.chat_client import AmoChatsAPIClient
from app.main import bp
from config import Config


# @bp.route('/send_test_msg', methods=['GET', 'POST'])
# def send_test_msg():
#     whatsapp_config = Config().whatsapp.get('drvorobjev')
#     template = None
#     for item in whatsapp_config.get('templates') or []:
#         # хардкод пока что, т.к. не ясно, как ассоциировать номер автообзвона с шаблоном
#         if item['name'] in ("couldnt_reach_you_serbian",):
#             template = item
#             break
#     number_from = (whatsapp_config.get('numbers') or [None])[0] or {}
#     send_wahtsapp_message(number_to='995591058618', number_id_from=number_from['id'], template=template)
#     return Response(status=204)


def send_wahtsapp_message(
    # https://developers.facebook.com/docs/whatsapp/cloud-api/reference/messages#examples
    # https://developers.facebook.com/docs/whatsapp/api/messages/message-templates#supported-languages
    number_to: str,
    number_id_from: str,
    template: Optional[str] = None,
    message: Optional[str] = None
):
    if template:
        data = {
            'messaging_product': 'whatsapp',
            "recipient_type": "individual",
            'to': number_to,
            'type': 'template',
            'template': template
        }
    elif message:
        data = {
            'messaging_product': 'whatsapp',
            "recipient_type": "individual",
            'to': number_to,
            'type': 'text',
            "text": {
                "body": message
            }
        }
    else:
        return None
    headers = {
        'Authorization': f"Bearer {Config().meta_system_user_token}",
        'Content-Type': 'application/json'
    }
    res = requests.post(
        url=f'https://graph.facebook.com/v17.0/{number_id_from}/messages',
        headers=headers,
        json=data
    )
    print(res.text)


@bp.route('/whatsapp', methods=['POST'])
def whatsapp_webhook():
    """ Нам отправили сообщение в WhatsApp,
        чтобы менеджер увидел его в интерфейсе Amo, необходимо использовать AmoChatsAPIClient
        {'object': 'whatsapp_business_account', 'entry': [{'id': '133570986506988', 'changes': [{'value': {'messaging_product': 'whatsapp', 'metadata': {'display_phone_number': '381114221400', 'phone_number_id': '151648284687808'}, 'contacts': [{'profile': {'name': 'Kirill Mizonow'}, 'wa_id': '995591058618'}], 'messages': [{'from': '995591058618', 'id': 'wamid.HBgMOTk1NTkxMDU4NjE4FQIAEhggQ0JBQUY5QkQwQTE0OUUxQ0Q4NTVCNkUwREVGOUQ3MEUA', 'timestamp': '1699356265', 'text': {'body': 'Test'}, 'type': 'text'}]}, 'field': 'messages'}]}]}
    """
    # see https://www.pragnakalp.com/automate-messages-using-whatsapp-business-api-flask-part-1/
    #   https://developers.facebook.com/blog/post/2022/10/24/sending-messages-with-whatsapp-in-your-python-applications/
    data = request.get_json()
    try:
        entry = data['entry'][0]
        value = entry['changes'][0]['value']
        # определяем идентификатор нашего номера, на который пришло сообщение
        phone_number_id = value['metadata']['phone_number_id']
        # по идентификатору номера определяем филиал
        branch = None
        for _branch, config in Config().whatsapp.items():
            for number in config.get('numbers'):
                if number['id'] == phone_number_id:
                    branch = _branch
                    break
            if branch:
                break
        if not branch:
            return '200 OK HTTPS.', 200
        contact = value['contacts'][0]['profile']
        msg = value['messages'][0]
        AmoChatsAPIClient(branch=branch).get_message(
            timestamp=int(msg['timestamp']),
            name=contact['profile']['name'],
            phone=contact['wa_id'],
            text=msg['text']['body'],
            conversation_id=entry['id'],
            msg_id=msg['id']
        )
    except Exception as exc:
        print(f'WhatsApp webhook error: {exc}')
    return '200 OK HTTPS.', 200


@bp.route('/whatsapp_remove', methods=['GET', 'POST'])
def whatsapp_remove():
    pass


@bp.route('/connect_account_to_chat_sm', methods=['GET'])
def connect_account_to_chat_sm():
    return jsonify(AmoChatsAPIClient(branch='SM').connect_account())


@bp.route('/connect_account_to_chat_cdv', methods=['GET'])
def connect_account_to_chat_cdv():
    return jsonify(AmoChatsAPIClient(branch='CDV').connect_account())
