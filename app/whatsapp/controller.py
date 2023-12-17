""" Управление сообщениями WhatsApp

https://developers.facebook.com/docs/whatsapp/cloud-api/reference/messages#examples
https://developers.facebook.com/docs/whatsapp/api/messages/message-templates#supported-languages
https://developers.facebook.com/docs/whatsapp/cloud-api/reference/phone-numbers
"""
import os.path
import uuid
from typing import Optional, List, Dict
import requests
from config import Config


class WhatsAppController:
    """ Класс для отправки сообщений WhatsApp """
    base_url = 'https://graph.facebook.com/v17.0/'

    def __init__(self, branch: str):
        self.config = Config().whatsapp.get(branch)

    def get_attachments_from_incoming_msg(self, data: Dict) -> List[str]:
        """ Скачивает вложения из входящего сообщения BWA и возвращает список имен файлов

        Args:
            data: данные сообщения

        Returns:
            список имен файлов вложений
        """
        entry = data.get('entry')
        if not entry:
            return []
        changes = entry[0].get('changes')
        if not changes:
            return []
        messages = changes[0]['value'].get('messages')
        if not messages:
            return []
        headers = {
            'Authorization': f"Bearer {self.config.get('system_user_token')}"
        }
        result = []
        for msg in messages:
            _type = msg.get('type')
            document = msg.get(_type)
            if not document:
                continue
            # получаем id и расширение файла
            _id = document['id']
            try:
                _, ext = os.path.splitext(document['filename'])
            except:
                ext = f".{(document.get('mime_type') or '').split('/')[1]}"
            # отправляем запрос на получение ссылки на файл
            response = requests.get(
                url=f'{self.base_url}{_id}/',
                headers=headers
            )
            if response.status_code != 200:
                print('failed to get WhatsApp attachments url', response.text)
                continue
            # отправляем запрос на скачивание файла
            url = response.json().get('url')
            response = requests.get(url=url, headers=headers)
            if response.status_code != 200:
                print('failed to get WhatsApp attachments content', response.text)
                continue
            # имя файла задаем уникальное, независимо от того, какое имя было в оригинале
            file = f"{uuid.uuid4()}{ext}"
            with open(file, 'wb') as f:
                f.write(response.content)
            result.append(file)
        return result

    def send_message(
        self,
        number_to: str,
        number_id_from: Optional[str] = None,
        template: Optional[str] = None,
        message: Optional[str] = None
    ):
        """ Отправляет сообщение через BWA по шаблону или без

        Args:
            number_to: номер получателя
            number_id_from: идентификатор номера отправителя (по умолчанию будет взят первый из настроек)
            template: шаблон
            message: текст сообщения (игнорируется, если передан шаблон)
        """
        if not number_id_from:
            # если номер не передан явно, возьмем первый в списке для данного филиала
            number_id_from = self.config.get('numbers')[0].get('id')
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
            return
        headers = {
            'Authorization': f"Bearer {self.config.get('system_user_token')}",
            'Content-Type': 'application/json'
        }
        response = requests.post(
            url=f'{self.base_url}{number_id_from}/messages',
            headers=headers,
            json=data
        )
        print('WhatsApp response on sending msg', response.text)


if __name__ == '__main__':
    files = WhatsAppController(branch='').get_attachments_from_incoming_msg(
        data={'object': 'whatsapp_business_account', 'entry': [{'id': '133570986506988', 'changes': [{'value': {'messaging_product': 'whatsapp', 'metadata': {'display_phone_number': '381114221400', 'phone_number_id': '151648284687808'}, 'contacts': [{'profile': {'name': 'Kirill Mizonow'}, 'wa_id': '995591058618'}], 'messages': [{'from': '995591058618', 'id': 'wamid.HBgMOTk1NTkxMDU4NjE4FQIAEhggNjQ4QzgwN0YwNkMyNTExOUUwQzNDM0U3QkVGRDNBRjQA', 'timestamp': '1701754196', 'type': 'document', 'document': {'filename': '_8YqPudlHCC2RuFf.mp4', 'mime_type': 'video/mp4', 'sha256': 'ObBcFZ4y8ejXrQJDyCqW0LGxm+xrm1J7WANZd3JW1ZE=', 'id': '635706828763179'}}]}, 'field': 'messages'}]}]}
    )
    print(files)
