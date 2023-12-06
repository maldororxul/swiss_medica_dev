""" Маршруты для работы WhatsApp-ботов """
__author__ = 'ke.mizonov'

import time
import uuid
from typing import Optional, List, Dict
import requests
from flask import request, jsonify, Response

from app.amo.api.chat_client import AmoChatsAPIClient
from app.amo.processor.functions import clear_phone
from app.main import bp
from app.main.routes.utils import get_data_from_post_request
from app.main.utils import API_CLIENT, DATA_PROCESSOR
from app.whatsapp.controller import WhatsAppController
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

@bp.route('bwa_send_msg_by_template/<template_name>', methods=['POST'])
def bwa_send_msg_by_template(template_name: str):
    """ Отклик на событие перемещения лида на определенный этап в Amo. Нам придут следующие данные:
        leads[status][0][id] :: 23802129
        leads[status][0][status_id] :: 58841526
        leads[status][0][pipeline_id] :: 3508507
        leads[status][0][old_status_id] :: 58840350
        leads[status][0][old_pipeline_id] :: 7010970

    Args:
        template_name: имя шаблона BWA, используемого для отправки сообщений
    """
    # получаем данные с Amo, отправленные через вебхук
    data = get_data_from_post_request(_request=request)
    if not data:
        return 'Unsupported Media Type', 415
    lead_id = data.get('leads[status][0][id]')
    if not lead_id:
        return '200 OK HTTPS.', 200
    config = Config().whatsapp
    branch, template = None, None
    for _branch, branch_config in config.items():
        for _template in branch_config.get('templates') or []:
            if _template['name'] == template_name:
                template = _template
                branch = _branch
                break
    numbers = config.get(branch).get('numbers') or [{}]
    number_id = numbers[0].get('id')
    if not branch or not template or not number_id:
        return '200 OK HTTPS.', 200
    # получаем лид из Amo
    amo_client = API_CLIENT.get(branch)()
    lead = amo_client.get_lead_by_id(lead_id=lead_id) or {}
    contacts = (lead.get('_embedded') or {}).get('contacts') or [{}]
    contact_id = contacts[0].get('id')
    if not contact_id:
        return '200 OK HTTPS.', 200
    contact = amo_client.get_contact_by_id(contact_id=contact_id) or {}
    phone = None
    for cf in contact.get('custom_fields_values') or []:
        if cf['field_code'] == 'PHONE':
            phone = clear_phone(cf['values'][0]['value'])
            break
    if not phone:
        return '200 OK HTTPS.', 200
    # собственно отправляем сообщение через BWA
    send_whatsapp_message(template=template, number_to=phone, number_id_from=number_id)
    return '200 OK HTTPS.', 200


def send_whatsapp_message(
    # https://developers.facebook.com/docs/whatsapp/cloud-api/reference/messages#examples
    # https://developers.facebook.com/docs/whatsapp/api/messages/message-templates#supported-languages
    number_to: str,
    number_id_from: str,
    template: Optional[Dict] = None,
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
            # print('no branch')
            return '200 OK HTTPS.', 200
        contact = (value.get('contacts') or [{}])[0]
        if not contact:
            print('uncatched WhatsApp error')
            return '200 OK HTTPS.', 200
        msg = value['messages'][0]
        # print('msg', msg)
        timestamp = int(msg['timestamp'])
        name = contact['profile']['name']
        phone = contact['wa_id']
        # текста может не быть - вероятно, нам прислали файл
        text = (msg.get('text') or {}).get('body')
        # ищем лид и связанный с ним контакт
        contact_id = None
        # print('init amo api client...')
        amo_client = API_CLIENT.get(branch)()
        # print('searching contacts...', phone[-8:])
        contacts = [x for x in amo_client.find_contacts(query=phone[-8:]) or []]
        if contacts:
            contact_id = contacts[0]['id']
            # print('contact found!', contacts)
        # leads = [x for x in amo_client.find_leads(query=phone[-8:])]
        # print('leads', leads)
        # if leads:
        #     contacts = leads[0]['_embedded']['contacts']
        #     if contacts:
        #         contact_id = contacts[0]['id']
        # если контакт существует, ищем связанные с ним чаты
        chat_id = None
        if contact_id:
            print('trying to find chats...')
            chats = amo_client.get_chats(contact_id=contact_id)
            print('chats', chats)
            if chats:
                chat_id = chats[-1]['chat_id']
        else:
            # контакта не существует, кидаем чат в "неразобранное"
            # conversation_id = str(uuid.uuid4())
            # print('creating chat', name, phone)
            if text:
                amo_chats_client = AmoChatsAPIClient(branch=branch)
                new_chat = amo_chats_client.get_new_message(
                    name=name,
                    phone=phone,
                    conversation_id=str(uuid.uuid4())
                )
                new_chat_id = new_chat['id']
                print('trying to create unsorted...', timestamp, name, phone, text, new_chat_id)
                amo_chats_client.get_message(
                    timestamp=timestamp,
                    name=name,
                    phone=phone,
                    text=text,
                    conversation_id=new_chat_id,
                    msg_id=str(uuid.uuid4())
                )
                print('ok')
            return '200 OK HTTPS.', 200
        # есть контакт, но нет чата - создаем новый чат и связываем его с контактом
        if not chat_id and text:
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
        if chat_id and text:
            print('writing msg', name, phone, text, chat_id)
            AmoChatsAPIClient(branch=branch).get_message(
                timestamp=int(time.time()),  # поправка по времени?
                name=name,
                phone=phone,
                text=text,
                conversation_id=str(uuid.uuid4()),
                conversation_ref_id=chat_id,
                msg_id=str(uuid.uuid4())
            )
        # всегда проверяем и вложения (вероятно, нам прислали какие-то файлы)
        attachments: List[str] = WhatsAppController(branch=branch).get_attachments_from_incoming_msg(data=data)
        print('attachments:', attachments)
        lead_id = amo_client.get_lead_id_by_contact_id(contact_id=contact_id)
        print('lead_id', lead_id)
        for file in attachments:
            amo_client.upload_file(file_path=file, lead_id=lead_id)
    except Exception as exc:
        print(f'WhatsApp webhook error: {exc}')
        # todo WhatsApp webhook error: 'contacts'
        """
        WhatsApp response on sending msg {"messaging_product":"whatsapp","contacts":[{"input":"375292799419","wa_id":"375292799419"}],"messages":[{"id":"wamid.HBgMMzc1MjkyNzk5NDE5FQIAERgSNEEwOTI2MUFEMDI1OEVBQjIxAA=="}]}
        2023-11-27T10:03:08.195474+00:00 app[web.1]: 10.1.37.119 - - [27/Nov/2023:10:03:08 +0000] "POST /amo_chat/3a952d6f-afb1-4154-977a-a6f2eeb2053e_59a2fb56-7492-4c16-8bbe-f776345af46c HTTP/1.1" 204 0 "-" "amoCRM amoJo/1.0"
        """
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
