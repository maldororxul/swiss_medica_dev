""" Клиент API чатов AmoCRM - отдельный от основного API

amojo_id получаем через запрос https://swissmedica.amocrm.ru/api/v4/account?with=amojo_id
"""
import hashlib
import hmac
import json
import datetime
from typing import Optional, Dict
import requests
from config import Config


class AmoChatsAPIClient:
    """ Класс клиента API чатов AmoCRM """
    base_url: str = 'https://amojo.amocrm.ru/v2/origin/custom/'

    def __init__(self, branch: str):
        self.config = Config().amo_chat.get(branch)

    def connect_account(self):
        """ Подключение канала чата в аккаунте

        Docs:
            Чтобы подключить аккаунт к каналу чатов, вам необходимо выполнить POST запрос,
            передав в теле запроса ID подключаемого аккаунта.
            В ответ вы получите уникальный scope_id аккаунта для этого канала, который будет использоваться в дальнейшем
            при отправке сообщений.
            Также после подключения канала к чату можно будет работать с сообщениями и получать хуки об исходящих
            сообщениях.
            Подключение необходимо производить после каждой установки интеграции в аккаунте, так как при отключении
            интеграции канал автоматически отключается.

        Explanation:
            1. Через запрос https://subdomen.amocrm.ru/api/v4/account?with=amojo_id получаем amojo_id
            2. Прописываем его в конфиг
            3. Зовем данный метод через эндпоинт <...>
            4. Дописываем в конфиг scope_id
        """
        path = f'{self.config.get("id")}/connect'
        body = {
            'account_id': self.config.get('amojo_id'),
            'title': self.config.get('name'),  # Название канала, отображаемое пользователю
            'hook_api_version': 'v2',
        }
        return self.__request(path=path, body=body)

    def disconnect_account(self):
        """ Отключение канала чата в аккаунте """
        path = f'{self.config.get("id")}/disconnect'
        body = {
            'account_id': self.config.get('amojo_id')
        }
        return self.__request(path=path, body=body)

    def get_message(self, timestamp: int, name: str, phone: str, text: str, conversation_id: str, msg_id: str):
        path = f'{self.config.get("scope_id")}'
        body = {
          "event_type": "new_message",
          "payload": {
            "timestamp": timestamp,
            "msec_timestamp": timestamp * 1000,
            "msgid": msg_id,
            "conversation_id": conversation_id,
            "sender": {
              "id": phone,
              # "avatar": "https://example.com/users/avatar.png",
              "profile": {
                "phone": phone,
                # "email": "example.client@example.com"
              },
              # "profile_link": "https://example.com/profile/example.client",
              "name": name
            },
            "message": {
              "type": "text",
              "text": text
            },
            "silent": False
          }
        }
        return self.__request(path=path, body=body)

    # кейсов автоматической отправки сообщений пока нет, все сообщения отправляются с интерфейса вручную

    # def send_message(self):
    #     path = f'{self.config.get("scope_id")}'
    #     body = {
    #       "event_type": "new_message",
    #       "payload": {
    #         "timestamp": 1639604903,
    #         "msec_timestamp": 1639604903161,
    #         "msgid": "my_int-5f2836a8ca476",
    #         "conversation_id": "my_int-d5a421f7f217",
    #         "sender": {
    #           "id": "my_int-manager1_user_id",
    #           "name": "Имя менеджера",
    #           "ref_id": "76fc2bea-902f-425c-9a3d-dcdac4766090"
    #         },
    #         "receiver": {
    #           "id": "my_int-1376265f-86df-4c49-a0c3-a4816df41af8",
    #           "avatar": "https://example.com/users/avatar.png",
    #           "name": "Вася клиент",
    #           "profile": {
    #             "phone": "+79151112233",
    #             "email": "example.client@example.com"
    #           },
    #           "profile_link": "https://example.com/profile/example.client"
    #         },
    #         "message": {
    #           "type": "text",
    #           "text": "Сообщение от менеджера 76fc2bea-902f-425c-9a3d-dcdac4766090"
    #         },
    #         "silent": True
    #       }
    #     }
    #     return self.__request(path=path, body=body)

    def __request(self, path: str, body: Dict, method: str = 'POST') -> Optional[Dict]:
        """ Отправка запроса в Amo

        Args:
            path: адрес метода API
            body: тело запроса
            method: метод, по умолчанию POST

        Returns:
            результат выполнения запроса или None
        """
        content_type = 'application/json'
        date = datetime.datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')
        request_body = json.dumps(body, ensure_ascii=False).encode('utf-8')
        checksum = hashlib.md5(request_body).hexdigest()
        # Подготовка строки для подписи
        str_to_sign = '\n'.join([
            method.upper(),
            checksum,
            content_type,
            date,
            path,
        ])
        signature = hmac.new(
            self.config.get('secret_key').encode('utf-8'),
            str_to_sign.encode('utf-8'),
            hashlib.sha1
        ).hexdigest()
        # Подготовка заголовков запроса
        headers = {
            'Date': date,
            'Content-Type': content_type,
            'Content-MD5': checksum,
            'X-Signature': signature,
        }
        # Выполнение запроса
        response = requests.request(method, f'{self.base_url}{path}', headers=headers, data=request_body)
        if response.status_code != 200:
            print(f"Amo chats error: Received response {response.status_code} {response.text}")
            return None
        try:
            return response.json()
        except:
            return None
