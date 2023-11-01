""" Управление сообщениями WhatsApp

https://developers.facebook.com/docs/whatsapp/cloud-api/reference/messages#examples
https://developers.facebook.com/docs/whatsapp/api/messages/message-templates#supported-languages
https://developers.facebook.com/docs/whatsapp/cloud-api/reference/phone-numbers
"""
from typing import Optional
import requests
from config import Config


class WhatsAppController:
    """ Класс для отправки сообщений WhatsApp """

    def __init__(self, branch: str):
        self.config = Config().whatsapp.get(branch)

    def send_message(
        self,
        number_to: str,
        number_id_from: Optional[str] = None,
        template: Optional[str] = None,
        message: Optional[str] = None
    ):
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
            return None
        headers = {
            'Authorization': f"Bearer {self.config.get('system_user_token')}",
            'Content-Type': 'application/json'
        }
        response = requests.post(
            url=f'https://graph.facebook.com/v17.0/{number_id_from}/messages',
            headers=headers,
            json=data
        )
        print('WhatsApp response on sending msg', response.text)
