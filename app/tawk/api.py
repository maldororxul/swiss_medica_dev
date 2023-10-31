import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import requests
from config import Config


class TawkRestClient:
    base_url: str = 'https://api.tawk.to/v1/'

    def __init__(self, branch: str):
        self.token = Config().tawk_rest_key.get(branch)
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        self.params = None

    def get_channel_info(self, _id: str) -> Dict:
        return self._get_channel_info(_id=_id).get('data') or {}

    def get_channels(self) -> List[Dict]:
        return self._get_channels().get('data') or []

    def get_chat(self, channel_id: str, chat_id: str) -> Dict:
        return self._get_chat(
            channel_id=channel_id,
            chat_id=chat_id
        ).get('data') or []

    def get_chats(self, channel_id: str, dt_from: datetime, dt_to: datetime) -> List[Dict]:
        return self._get_chats(
            channel_id=channel_id,
            dt_from=dt_from,
            dt_to=dt_to
        ).get('data') or []

    def get_messages(self, channel_id: str, chat_id: str) -> Dict:
        """ Получает историю сообщений чата

        Args:
            channel_id: идентификатор канала
            chat_id: идентификатор чата

        Returns:
            Словарь для построения истории чата
            Tawk chat from: https://source-landing.com/
            2023-08-24 06:41:02 :: [chat started]
            2023-08-24 06:41:02 :: Operator Maria :: [operator joined chat]
            2023-08-24 06:41:02 :: Customer name :: Hello, I have a question...
            2023-08-24 06:41:02 :: Operator Maria :: Hi! Considering your question, we can offer...
        """
        result = []
        chat = self._get_chat(
            channel_id=channel_id,
            chat_id=chat_id
        ).get('data') or []
        agent = None
        visitor = None
        site_url = None
        site_title = None
        last_manager = {}
        for msg in chat.get('messages') or []:
            if msg.get('type') == 'nav':
                # откуда пришел посетитель
                nav_data = msg.get('data') or {}
                site_url = nav_data.get('url')
                site_title = nav_data.get('title')
                continue
            text = None
            is_agent = True
            sender = (msg.get('sender') or {})
            sender_type = sender.get('t')
            if sender_type == 'a':
                # имя агента
                last_manager = sender
                agent = sender.get('n')
                text = msg.get('msg') or '[operator joined chat]'
            elif sender_type == 'v':
                # посетитель
                text = msg.get('msg') or ''
                if 'Name :' in text and 'Phone :' in text:
                    # заполнена форма пре-чата
                    visitor = self.__get_visitor(text=text)
                    text = '[chat started]'
                is_agent = False
            elif sender_type == 's':
                # системное сообщение - пропускаем
                continue
            dt = datetime.strptime(msg.get('time'), '%Y-%m-%dT%H:%M:%S.%fZ')
            result.append({
                'date': dt,
                'agent': agent if is_agent else None,
                'text': text
            })
        return {
            'site_url': site_url,
            'site_title': site_title,
            'visitor': visitor,
            'manager': last_manager,
            'messages': result,
        }

    def get_messages_text_and_person(self, channel_id: str, chat_id: str) -> Optional[Dict]:
        """ Возвращает данные чата

        Args:
            channel_id: текстовый идентификатор канала
            chat_id: текстовый идентификатор чата

        Returns:
            Данные чата в формате
            {
                'person': {
                    'name': {'first': 'chat data', 'last': 'transfer'},
                    'emails': [], 'phones': ['2589631477'],
                    'createdOn': '2023-09-07T07:45:55.831Z',
                    'updatedOn': '2023-09-07T07:46:24.430Z',
                    'device': {'ip': '37.232.82.193', 'browser': 'chrome', 'os': 'windows'},
                    'firstSeenOn': '2023-09-07T07:45:55.926Z',
                    'lastSeenOn': '2023-09-07T07:45:55.926Z',
                    'location': {'continent': 'AS', 'country': 'GE', 'cityName': 'Batumi', 'cityId': 615532, 'regionId': 615929, 'regionName': 'Achara', 'point': '41.6473,41.6258'},
                    'webSession': {'count': 1, 'first': '2023-09-07T07:45:55.926Z', 'latest': '2023-09-07T07:45:55.926Z', 'pageViews': 0, 'timeSpent': 0},
                    'primaryPhone': '2589631477',
                    'id': '64f97fb3aab3f51368ed3600'
                },
                'messages': 'Tawk chat from: https://swiss-medica-2e0e7bc937df.herokuapp.com/\nView chat: https://dashboard.tawk.to/#/inbox/64d0945994cf5d49dc68dd99/all/chat/93e94760-4d52-11ee-9f1f-6dfbc0fa7e4b\n2023-09-07 07:46:24 :: [chat started]\n2023-09-07 07:46:24 :: chat data transfer :: hi\n2023-09-07 07:46:24 :: Operator Kirill :: [operator joined chat]\n2023-09-07 07:46:24 :: Operator Kirill :: test\n2023-09-07 07:46:24 :: chat data transfer :: bb'
            }
        """
        chat = self.get_chat(channel_id=channel_id, chat_id=chat_id)
        if not chat:
            return None
        result = self.get_source_and_messages_text(channel_id=channel_id, chat_id=chat_id)
        result['person'] = self.get_person(channel_id=channel_id, person_id=chat.get('personId'))
        return result

    def get_messages_text_and_person_by_phone(self, channel_id: str, phone: str) -> Optional[Dict]:
        chat = self.find_latest_chat_by_phone(channel_id=channel_id, phone=phone)
        if not chat:
            return None
        result = self.get_source_and_messages_text(channel_id=channel_id, chat_id=chat.get('id'))
        result['person'] = self.get_person(channel_id=channel_id, person_id=chat.get('personId'))
        return result

    def get_person(self, channel_id: str, person_id: str) -> Dict:
        return (self._get_person(channel_id=channel_id, person_id=person_id).get('data') or {}).get('person')

    def get_property_members(self, channel_id: str) -> List[Dict]:
        return self._get_property_members(channel_id=channel_id).get('data') or []

    def get_source_and_messages_text(self, channel_id: str, chat_id: str) -> Dict:
        messages = self.get_messages(channel_id=channel_id, chat_id=chat_id)
        site_url = messages.get('site_url')
        text = f"Tawk chat from: {site_url}\n" \
               f"View chat: https://dashboard.tawk.to/#/inbox/{channel_id}/all/chat/{chat_id}"
        visitor = (messages.get('visitor') or {}).get('name')
        for msg in messages.get('messages') or []:
            msg_text = msg.get('text')
            date_str = msg.get('date').strftime('%Y-%m-%d %H:%M:%S')
            if msg_text == '[chat started]':
                text_to_add = f"{date_str} :: {msg_text}"
            else:
                agent = msg.get('agent')
                name = f"Operator {agent}" if agent else visitor
                text_to_add = f"{date_str} :: {name} :: {msg_text}"
            text = f"{text}\n{text_to_add}"
        return {
            'source': site_url,
            'messages': text,
            'manager': messages.get('manager')
        }

    def find_latest_chat_by_phone(self, channel_id: str, phone: str):
        for chat in self.get_chats(
            channel_id=channel_id,
            dt_from=datetime.now() - timedelta(hours=5),
            dt_to=datetime.now() + timedelta(hours=5)
        ):
            for msg in chat.get('messages') or []:
                if msg['type'] != 'msg' or msg['sender']['t'] != 'v':
                    continue
                text = msg['msg']
                if 'Name : ' not in text:
                    continue
                visitor = self.__get_visitor(text=text)
                if visitor['phone'] == phone:
                    return chat
        return None

    def _get_channels(self):
        return self._set_params({
            "type": "business",
            "enabled": True
        }).__fetch(endpoint='property.list')

    def _get_channel_info(self, _id: str):
        return self._set_params({
            "propertyId": _id,
            "fields": {
                "settings": True,
                "agents": True,
                "widgets": True,
                "assets": True,
                "createdOn": True
            }
        }).__fetch(endpoint='property.info')

    def _get_chat(self, channel_id: str, chat_id: str):
        return self._set_params({
            "propertyId": channel_id,
            "chatId": chat_id
        }).__fetch(endpoint='chat.get')

    def _get_chats(self, channel_id: str, dt_from: datetime, dt_to: datetime):
        return self._set_params({
            "propertyId": channel_id,
            "size": 1000,
            "startDate": dt_from.strftime('%Y-%m-%dT%H:%M:%SZ'),
            "endDate": dt_to.strftime('%Y-%m-%dT%H:%M:%SZ'),
            # "messageCount": 0,
            # "deleted": False,
            # "status": "open",
            # "tags": [
            #     "string"
            # ],
            "sort": "co-new-old",
            "dateType": "cso"
        }).__fetch(endpoint='chat.list')

    def _get_person(self, channel_id: str, person_id: str):
        return self._set_params({
            "propertyId": channel_id,
            "personId": person_id,
            'fields': [
                'id', 'name', 'jobTitle', 'primaryEmail', 'emails', 'primaryPhone', 'phones', 'avatar',
                'socialProfiles', 'tags', 'organizationId', 'userId', 'device', 'location', 'webSession', 'liveChat',
                'ticket', 'firstSeenOn', 'lastSeenOn', 'customAttributes', 'customEvents', 'createdOn', 'updatedOn'
            ]
        }).__fetch(endpoint='contact.person.get')

    def _get_property_members(self, channel_id: str):
        return self._set_params({
            "propertyId": channel_id
        }).__fetch(endpoint='members.list')

    def _set_headers(self, headers: Dict):
        self.headers = headers
        return self

    def _set_params(self, params: Dict):
        self.params = params
        return self

    def __fetch(self, endpoint: str) -> Dict:
        response = requests.post(
            f'{self.base_url}{endpoint}',
            headers=self.headers,
            auth=(self.token, ''),
            data=json.dumps(self.params)
        )
        data = response.json()
        if not data or 'error' in data or 'data' not in data:
            return {}
        return data

    @staticmethod
    def __get_visitor(text: str):
        result = {}
        for item in text.split('\r\n'):
            for key, prefix in (('name', 'Name : '), ('email', 'Email : '), ('phone', 'Phone : ')):
                if prefix in item:
                    result[key] = item.replace(prefix, '').strip()
        return result
