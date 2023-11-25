""" Маршруты для работы WhatsApp-ботов """
__author__ = 'ke.mizonov'

import time
import uuid
from typing import Optional
import requests
from flask import request, jsonify, Response

from app.amo.api.chat_client import AmoChatsAPIClient
from app.main import bp
from app.main.utils import API_CLIENT
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
    print('incoming WhatsApp data:', data)
    """
    {'profile': {'name': 'Kirill Mizonow'}, 'wa_id': '995591058618'}], 'messages': [{'from': '995591058618', 'id': 'wamid.HBgMOTk1NTkxMDU4NjE4FQIAEhggQkFDNTcwN0VGMzY1RDEyNUZBQTcxRDZBM0U5QjE4OTMA', 'timestamp': '1700943407', 'text': {'body': 'Сообщение отправлено из WhatsApp... 2'}, 'type': 'text'}]}, 'field': 'messages'}]}]}
    """
    try:
        entry = data['entry'][0]
        value = entry['changes'][0]['value']
        # определяем идентификатор нашего номера, на который пришло сообщение
        phone_number_id = value['metadata']['phone_number_id']      # пришло 151648284687808
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
            print('no branch')
            return '200 OK HTTPS.', 200
        contact = value['contacts'][0]
        msg = value['messages'][0]
        print('msg', msg)
        timestamp = int(msg['timestamp'])
        name = contact['profile']['name']
        phone = contact['wa_id']
        text = msg['text']['body']
        # ищем лид и связанный с ним контакт
        contact_id = None
        print('init amo api client...')
        amo_client = API_CLIENT.get(branch)()
        print('searching leads...', phone[-8:])
        leads = [x for x in amo_client.find_leads(query=phone[-8:])]
        print('leads', leads)
        if leads:
            contacts = leads[0]['_embedded']['contacts']
            if contacts:
                contact_id = contacts[0]['id']
        # если контакт существует, ищем связанные с ним чаты
        chat_id = None
        if contact_id:
            chats = amo_client.get_chats(contact_id=contact_id)
            if chats:
                chat_id = chats[-1]['chat_id']
        else:
            # контакта не существует, кидаем чат в "неразобранное"
            print('trying to create unsorted...', timestamp, name, phone, text)
            AmoChatsAPIClient(branch=branch).get_message(
                timestamp=timestamp,
                name=name,
                phone=phone,
                text=text,
                conversation_id=str(uuid.uuid4()),
                msg_id=str(uuid.uuid4())
            )
            print('ok')
            return '200 OK HTTPS.', 200
        # есть контакт, но нет чата - создаем новый чат и связываем его с контактов
        if not chat_id:
            print('creating chat', name, phone)
            new_chat = AmoChatsAPIClient(branch=branch).get_new_message(
                name=name,
                phone=phone,
                conversation_id=str(uuid.uuid4())
            )
            chat_id = new_chat['id']
            # связываем чат с контактом
            print('linking chat with contact', chat_id, contact_id)
            amo_client.link_chat_with_contact(contact_id=contact_id, chat_id=chat_id)
        # пишем сообщение в чат
        if chat_id:
            print('writing msg', name, phone, text, chat_id)
            AmoChatsAPIClient(branch=branch).get_message(
                timestamp=int(time.time()),  # поправка по времени?
                name=name,
                phone=phone,
                text=text,
                conversation_id=chat_id,
                msg_id=str(uuid.uuid4())
            )
    except Exception as exc:
        print(f'WhatsApp webhook error: {exc}')
    return '200 OK HTTPS.', 200


@bp.route('/whatsapp_remove', methods=['GET', 'POST'])
def whatsapp_remove():
    pass


@bp.route('/connect_account_to_chat_sm', methods=['GET'])
def connect_account_to_chat_sm():
    """
    Amo chats error: Received response 403 {"status":0,"error_code":403,"error_type":"ORIGIN_INVALID_SIGNATURE","error_description":"invalid signature"}
    URL: https://amojo.amocrm.ru/v2/origin/custom/3a952d6f-afb1-4154-977a-a6f2eeb2053e/connect
    HEADERS: {'Date': 'Thu, 23 Nov 2023 06:39:58 +0000', 'Content-Type': 'application/json', 'Content-MD5': 'd60c4ec9ca70e3ddb50b1852c7326f0f', 'X-Signature': '024796f7085b2eb42244c19909c5704bbea436ce', 'User-Agent': 'amoCRM-Chats-Doc-Example/1.0'}
    BODY: {"account_id":"59a2fb56-7492-4c16-8bbe-f776345af46c","title":"WhatsApp Business","hook_api_version":"v2"}
    response: None
    """
    return jsonify(AmoChatsAPIClient(branch='SM').connect_account())


@bp.route('/connect_account_to_chat_cdv', methods=['GET'])
def connect_account_to_chat_cdv():
    return jsonify(AmoChatsAPIClient(branch='CDV').connect_account())
