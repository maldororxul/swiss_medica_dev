""" API-клиент AMO """
__author__ = 'ke.mizonov'
import json
import mimetypes
import os
from datetime import datetime
import random
import requests
from time import sleep, time
from typing import Dict, List, Optional, Union, Type

from app.amo.api.sync_controller import SMSyncController, CDVSyncController
from app.engine import get_engine
from app.extensions import db
from app.amo.api.constants import AmoEvent
from app.models.amo_credentials import CDVAmoCredentials, SMAmoCredentials
from app.models.amo_token import SMAmoToken, CDVAmoToken
from app.models.contact import SMContact, CDVContact
from app.models.event import SMEvent, CDVEvent
from app.models.lead import CDVLead, SMLead
from app.models.note import SMNote, CDVNote
from app.models.pipeline import CDVPipeline, SMPipeline
from app.models.user import SMUser, CDVUser

ERROR_SLEEP_INTERVAL = 5
REQUEST_SLEEP_INTERVAL = 1
DATA_LIMIT = 50     # Больше 50 не ставить, т.к. по контактам, к примеру, ограничение 50

MULTI_PROCESS = False

TSyncController = Union[Type[SMSyncController], Type[CDVSyncController]]


class APIClient:
    """ Базовый API-клиент AMO """
    domain: str = 'amocrm.ru/api/v4'
    credentials: db.Model = NotImplemented
    token: db.Model = NotImplemented
    lead: db.Model = NotImplemented
    pipeline: db.Model = NotImplemented
    contact: db.Model = NotImplemented
    event: db.Model = NotImplemented
    note: db.Model = NotImplemented
    user: db.Model = NotImplemented
    sub_domain: str = NotImplemented
    referer_field_id: int = NotImplemented
    utm_map: Dict = NotImplemented
    sync_controller_class: TSyncController

    def __init__(self):
        # self.token_pkl: str = f'{self.sub_domain}_token'
        # self.amo_settings_pkl: str = f'amo_{self.sub_domain}_settings'
        self.session = db.session
        self.sync_controller = self.sync_controller_class()

        # # fixme tmp
        # credentials = self.credentials(
        #     auth_code='def502005ec4ebd5836866847873f5d11133fef516464b7aeea051bf96f51e7743867a20ddaffc2323b4c4a2cf396c9bc7a97641f34bb9e4d2d0a1f5a52d2cf0b3bb51a83dd11d617cb1df7d2590bf0c908b587e79681d26775d7d9505e2b018ededcf3f54e5b58636b6098bc514eea25dde989e6037006b523489127387759c71cc46c799e87f89511abc7302a7b23eed8103acc8b38a8005b0dbddc0a70508d1a6ee2f2946e389d5e1499dbfd54188c2fb6a5ad2f08f180a0a3748ae4658aa9282db8395dee11a2c29a97510edf43c94f0b5d08d3372fe08756aacc4fcaccf9265712558963f1f4ad082d504113f12e5e09825b7b3d6afc4a452aca37143d63f3512d942b5ece2ab2980b36e386c63d011611f9cf1cb8bf4c902717d9e0505ae4adea80338dfd05a047484d6ae6649ebfe9024a245741dc120af13ba9df6c8177745546e02d566f72c497e39cb023ae32d076106fc9614cbdcacf9cb4a34d5532e3d87b4b1e4dba1a997474ad476a791278c39c0e0ab9f9608fc9b49fcf58d52ec26645f5d167316acbbe214e659b2bf1f1e7502545c6259e0a2e954b262eb16672ff3213b272ef0bf37dbd9fee44a67760da060b6959c4e6250db74c71c898585f6c3d8f1c731',
        #     client_id='3a62f0e9-16fe-48f4-9391-ecec86e2b805',
        #     client_secret='hUFdVr1NK3OtYKYDbWBCZJnxNEhRKd56uIMy12vi0ERDQ9KzRYQjAnG0K94nN42q',
        #     redirect_url='https://ya.ru/'
        # )
        # self.session.add(credentials)
        # self.session.commit()

        # считываем креды
        credentials = self.session.query(self.credentials).order_by(self.credentials.id.desc()).first()
        if credentials:
            self._client_id = credentials.client_id
            self._client_secret = credentials.client_secret
            self._redirect_url = credentials.redirect_url
            self._auth_code = credentials.auth_code
        else:
            self._client_id = None
            self._client_secret = None
            self._redirect_url = None
            self._auth_code = None
        # авторизация и проверочный запрос
        self.headers = {}
        self._set_auth_headers()
        self.test_request()

    def get_drive_url(self):
        response = self.__execute(endpoint='account', params='with=drive_url')
        return response.json().get('drive_url')

    def get_lead_id_by_contact_id(self, contact_id: Optional[int] = None) -> Optional[int]:
        if not contact_id:
            return None
        params = f'filter[id][]={contact_id}' \
                 f'&with=leads' \
                 f'&limit={1}' \
                 f'&order=created_at'
        data = [x for x in self.__get_data(endpoint='contacts', params=params)]
        if not data:
            return None
        _embedded = data[0].get('_embedded')
        leads = _embedded.get('leads')
        if not leads:
            return None
        return leads[0]['id']

    def upload_file(self, file_path: str, lead_id: int):
        file_name = file_path
        file_size = os.path.getsize(file_path)
        mime_type, _ = mimetypes.guess_type(file_path)
        drive_url = self.get_drive_url()
        self._set_auth_headers()
        # создаем сессию загрузки
        data = {
            "file_name": file_name,
            "file_size": file_size,
            "content_type": mime_type,
            # "file_uuid": "367b9f38-5f01-4cea-947e-dfab47aea522"
        }
        response = requests.post(url=f"{drive_url}/v1.0/sessions", headers=self.headers, json=data)
        if response.status_code != 200:
            return
        session = response.json()
        upload_url = session.get('upload_url')
        chunk_size = session.get('max_part_size')  # Размер части в байтах
        headers = {'Content-Type': mime_type}
        # Отправка файла частями
        data = None
        with open(file_path, 'rb') as f:
            while True:
                file_chunk = f.read(chunk_size)
                if not file_chunk:
                    break
                response = requests.post(upload_url, headers=headers, data=file_chunk)
                # Обработка ответа для каждой части
                try:
                    response.raise_for_status()
                except requests.exceptions.HTTPError as err:
                    print(f"Ошибка при отправке части файла: {err}")
                    break  # Прерывание цикла в случае ошибки
                data = response.json()
                upload_url = data.get('next_url')
        # прикрепляем файл к лиду
        if lead_id:
            print('adding note with file')
            self.add_note(
                entity_id=lead_id,
                data=[{
                    "entity_id": lead_id,
                    'note_type': 'attachment',
                    'params': {
                        "version_uuid": data['version_uuid'],
                        "file_uuid": data['uuid'],
                        "file_name": f"{data['name']}.{data['metadata']['extension']}"
                    }
                }]
            )
        return data

    def get_tasks(self, date_from: datetime, date_to: datetime) -> bool:
        """ Получить список задач

        Args:
            date_from: дата с
            date_to: дата по

        Returns:
            True - если получены новые данные
        """
        params = f'filter[updated_at][from]={date_from.timestamp()}' \
                 f'&filter[updated_at][to]={date_to.timestamp()}' \
                 f'&limit={50}' \
                 f'&order=created_at'
        return self.get_and_sync_data(endpoint='tasks', params=params, limit=50, db_table='Task')

    def get_companies(self, date_from: datetime, date_to: datetime) -> List[Dict]:
        """ Получить список компаний

        Args:
            date_from: дата с
            date_to: дата по

        Returns:
            список компаний
        """
        # с источника мы получаем лиды по updated_at всегда
        params = f'filter[updated_at][from]={date_from.timestamp()}' \
                 f'&filter[updated_at][to]={date_to.timestamp()}' \
                 f'&limit={250}' \
                 f'&with=customers' \
                 f'&order=created_at'
        return self.__get_data(endpoint='companies', params=params, limit=250)

    def get_contacts(self, date_from: datetime, date_to: datetime) -> bool:
        """ Получить список контактов

        Args:
            date_from: дата с
            date_to: дата по

        Returns:
            True - если получены новые данные
        """
        # с источника мы получаем лиды по updated_at всегда
        params = f'filter[updated_at][from]={date_from.timestamp()}' \
                 f'&filter[updated_at][to]={date_to.timestamp()}' \
                 f'&limit={50}' \
                 f'&with=customers' \
                 f'&order=created_at'
        return self.get_and_sync_data(endpoint='contacts', params=params, limit=50, db_table='Contact')

    def write_credentials(self, auth_code: str, client_id: str, client_secret: str, redirect_url: str):
        # fixme depr
        new_creds = self.credentials(
            auth_code=auth_code,
            client_id=client_id,
            client_secret=client_secret,
            redirect_url=redirect_url
        )
        self.session.add(new_creds)
        self.session.commit()

    def get_deleted_events(
        self,
        date_from: datetime,
        date_to: datetime,
    ) -> Dict:
        """ Получить список удаленных событий за период

        Args:
            date_from: с
            date_to: по

        Returns:
            словарь, мапающий идентификатор сделки с событиями удаления
        """
        # получаем список пользователей для определения того, кто удалил сделку
        users = self._get_users()
        users_dict = {user['id']: user for user in users}
        # получаем события удаления сделок и подмешиваем к ним пользователей
        events = self._get_deleted_events(date_from=date_from, date_to=date_to)
        # todo проверить
        self._save_entity_events(collection=events, entity='leads')
        for event in events:
            user = users_dict.get(event['created_by']) or {}
            event['user'] = {'id': user.get('id'), 'name': user.get('name'), 'email': user.get('email')}
        return {
            event['entity_id']: {'user': event['user'], 'date': event['created_at']}
            for event in events
        }

    @classmethod
    def get_lead_url_by_id(cls, lead_id: int) -> str:
        """ Получение ссылки на сделку по идентификатору """
        return f'https://{cls.sub_domain}.amocrm.ru/leads/detail/{lead_id}'

    def run(self, date_from: Optional[datetime] = None, date_to: Optional[datetime] = None) -> bool:
        """
        Returns:
            True - если на источнике была обнаружена хотя бы одна новая / измененная запись за период
        """
        self.get_users()
        self.get_pipelines()
        return any([
            self.get_contacts(date_from=date_from, date_to=date_to),
            self.get_events(date_from=date_from, date_to=date_to),
            self.get_leads(date_from=date_from, date_to=date_to),
            self.get_notes(date_from=date_from, date_to=date_to),
            self.get_tasks(date_from=date_from, date_to=date_to),
        ])

    def get_events(self, date_from: datetime, date_to: datetime) -> bool:
        """ Получить список событий

        Args:
            date_from: дата с
            date_to: дата по

        Returns:
            True - если получены новые данные
        """
        params = f'filter[created_at][from]={date_from.timestamp()}' \
                 f'&filter[created_at][to]={date_to.timestamp()}' \
                 f'&limit={100}' \
                 f'&order=created_at'
        return self.get_and_sync_data(endpoint='events', params=params, limit=100, db_table='Event')

    def get_notes(self, date_from: datetime, date_to: datetime) -> bool:
        """ Получить список примечаний

        Args:
            date_from: дата с
            date_to: дата по

        Returns:
            список примечаний
        """
        """ Получить список примечаний

        Args:
            date_from: дата с
            date_to: дата по

        Returns:
            True - если получены новые данные
        """
        limit = 250
        params = f'filter[updated_at][from]={date_from.timestamp()}' \
                 f'&filter[updated_at][to]={date_to.timestamp()}' \
                 f'&limit={limit}' \
                 f'&order=created_at'
        # у нас две отдельные сущности, к которым привязаны примечания: лиды и контакты
        update_leads_notes = self.get_and_sync_data(
            params=params,
            limit=limit,
            entity='leads',
            endpoint='notes',
            db_table='Note'
        )
        update_contacts_notes = self.get_and_sync_data(
            params=params,
            limit=limit,
            entity='contacts',
            endpoint='notes',
            db_table='Note'
        )
        return update_leads_notes or update_contacts_notes

    def get_pipelines(self) -> bool:
        """ Получить список воронок

        Returns:
            True - если получены новые данные
        """
        return self.get_and_sync_data(endpoint='pipelines', params='', entity='leads')

    def add_lead(self, data: Union[Dict, List]):
        return self.__execute(endpoint='leads/complex', method='POST', data=data)

    def add_lead_simple(
        self,
        title: str,
        name: str,
        pipeline_id: int,
        status_id: int,
        contacts: Optional[List[Dict]] = None,
        tags: Optional[Union[List[str], List[Dict]]] = None,
        referer: Optional[str] = None,
        utm: Optional[Dict] = None,
        custom_fields_values: Optional[List] = None,
        responsible_user_id: int = 0
    ):
        custom_fields_values = custom_fields_values or []
        utm = utm or {}
        if referer and self.referer_field_id:
            custom_fields_values.append({
                "field_id": self.referer_field_id,
                "values": [
                    {
                        "value": str(referer)
                    }
                ]
            })
        for key, value in utm.items():
            if not value:
                continue
            lower_key = key.lower()
            utm_field_id = self.utm_map.get(lower_key)
            if not utm_field_id:
                continue
            custom_fields_values.append({
                "field_id": utm_field_id,
                "values": [
                    {
                        "value": str(value)
                    }
                ]
            })
        contacts_fileds = []
        for contact in contacts or []:
            contacts_fileds.append({
                "field_id": contact['field_id'],
                "values": [{
                    "value": contact['value'],
                    "enum_code": contact['enum_code']
                }]
            })
        lead_data = {
            "name": title,
            "created_by": 0,
            'created_at': int(time()),
            'pipeline_id': pipeline_id,
            'status_id': status_id,
            # 'custom_fields_values': custom_fields_values,
            'responsible_user_id': responsible_user_id,
            "_embedded": {
                "tags": [{"name": tag} for tag in tags or []] if tags and isinstance(tags[0], str) else tags,
                'contacts': [{
                    "name": name,
                    "created_at": int(time()),
                    "custom_fields_values": contacts_fileds,
                    "updated_by": 0
                }]
            }
        }
        if custom_fields_values:
            lead_data['custom_fields_values'] = custom_fields_values
        return self.add_lead(data=[lead_data])

    def add_note(self, entity_id: int, data: Union[Dict, List]):
        return self.__execute(endpoint=f'leads/{entity_id}/notes', method='POST', data=data)

    def add_note_simple(self, entity_id: int, text: str):
        note_data = [{
            "entity_id": entity_id,
            "created_by": 0,
            "note_type": "common",
            "params": {
                "text": text
            }
        }]
        return self.add_note(entity_id=entity_id, data=note_data)

    def get_tawk_lead_notes(self, lead_id: int) -> Optional[Dict]:
        limit = 250
        params = f'limit={limit}&order=created_at'
        notes = self.get_entity_notes(params=params, limit=limit, entity='leads', entity_id=lead_id)
        for note in notes:
            params = note.get('params') or {}
            text = params.get('text')
            if 'Tawk chat' in text:
                return note
        return None

    def update_lead(self, lead_id: int, data: Dict):
        self.__execute(endpoint='leads', method='PATCH', data=data, entity_id=lead_id)

    def update_note(self, lead_id: int, data: List):
        self.__execute(endpoint='notes', method='PATCH', data=data, entity='lead', entity_id=lead_id)

    def update_note_simple(self, note_id: int, lead_id: int, text: str):
        note_data = {
            "id": note_id,
            "note_type": "common",
            "params": {
                "text": text
            }
        }
        self.update_note(lead_id=lead_id, data=[note_data])

    def get_lead_notes(self, lead_id: int, note_type: Optional[str] = None, limit: int = 10, page: Optional[int] = None):
        params = f'filter[entity_id]={lead_id}' \
                 f'&limit={limit}' \
                 f'&order=created_at'
        if note_type:
            params = f'{params}&filter[note_type]={note_type}'
        return self.__get_data(endpoint='notes', params=params, limit=limit, entity='leads', page=page)

    def get_contact_notes(self, contact_id: int, note_type: Optional[str] = None, limit: int = 10, page: Optional[int] = None):
        params = f'filter[entity_id]={contact_id}' \
                 f'&limit={limit}' \
                 f'&order=created_at'
        if note_type:
            params = f'{params}&filter[note_type]={note_type}'
        return self.__get_data(endpoint='notes', params=params, limit=limit, entity='contacts', page=page)

    def get_lead_events(self, lead_id: int, event_type: Optional[str] = None, limit: int = 10, page: Optional[int] = None):
        params = f'filter[entity]=leads&filter[entity_id]={lead_id}' \
                 f'&limit={limit}' \
                 f'&order=created_at'
        if event_type:
            params = f'{params}&filter[type]={event_type}'
        return self.__get_data(endpoint='events', params=params, limit=limit, page=page)

    def get_contact_events(self, contact_id: int, event_type: Optional[str] = None, limit: int = 10, page: Optional[int] = None):
        params = f'filter[entity]=contacts&filter[entity_id]={contact_id}' \
                 f'&limit={limit}' \
                 f'&order=created_at'
        if event_type:
            params = f'{params}&filter[type]={event_type}'
        return self.__get_data(endpoint='events', params=params, limit=limit, page=page)

    def get_entity_notes(self, params: str, limit: int, entity: str, entity_id: Optional[int] = None) -> List[Dict]:
        """ Получить список примечаний

        Args:
            params: параметры запроса
            limit: ограничение по количеству примечаний в запросе
            entity: сущность
            entity_id: идентификатор сущности

        Returns:
            список примечаний
        """
        return self.__get_data(endpoint='notes', params=params, limit=limit, entity=entity, entity_id=entity_id)

    def _save_entity_events(self, collection: List[Dict], entity: str) -> List[Dict]:
        """ Получить список примечаний

        Args:
            collection: полученные с источника события
            entity: сущность

        Returns:
            список примечаний
        """
        serializer = object     # fixme 2023-6 PklSerializer(file_name=f'{self.sub_domain}_{entity}_events')
        events = []     # serializer.load() or []
        events_dict = {event['id']: event for event in events}
        for item in collection:
            event = events_dict.get(item['id'])
            try:
                if event:
                    if item['updated_at'] != event['updated_at']:
                        events_dict[item['id']] = item
                else:
                    events_dict[item['id']] = item
            except KeyError:
                events_dict[item['id']] = item
        serializer.save(obj=[event for event in events_dict.values()])
        return events

    def get_token(self, auth_code: str, client_id: str, client_secret: str, redirect_url: str):
        """ Получение токена в обмен на код авторизации """
        # сохраняем используемые креды (они будут использоваться при обновлении токена)
        credentials = self.credentials(
            auth_code=auth_code,
            client_id=client_id,
            client_secret=client_secret,
            redirect_url=redirect_url
        )
        self.session.add(credentials)
        self.session.commit()
        # меняем код авторизации на токен
        response = requests.post(
            url=f'https://{self.sub_domain}.amocrm.ru/oauth2/access_token',
            data={
                'client_id': client_id,
                'client_secret': client_secret,
                'grant_type': 'authorization_code',
                'code': auth_code,
                'redirect_uri': redirect_url
            }
        )
        response_json = response.json()
        if 'access_token' in response_json:
            token = self.token(
                token_type=response_json.get('token_type'),
                expires_in=response_json.get('expires_in'),
                access_token=response_json.get('access_token'),
                refresh_token=response_json.get('refresh_token'),
            )
            self.session.add(token)
            self.session.commit()

    def refresh_token(self):
        """ Обновление токена """
        token_data = self.__get_token_data()
        if not token_data:
            return
        response = requests.post(
            url=f'https://{self.sub_domain}.amocrm.ru/oauth2/access_token',
            data={
                'client_id': self._client_id,
                'client_secret': self._client_secret,
                'grant_type': 'refresh_token',
                'refresh_token': token_data.refresh_token,
                'redirect_uri': self._redirect_url
            }
        )
        response_json = response.json()
        if 'access_token' in response_json:
            token = self.token(
                token_type=response_json.get('token_type'),
                expires_in=response_json.get('expires_in'),
                access_token=response_json.get('access_token'),
                refresh_token=response_json.get('refresh_token'),
            )
            self.session.add(token)
            self.session.commit()

    def test_request(self):
        """ Проверочный запрос, чтобы убедиться, что токен жив """
        response = requests.get(url=self.__get_url(f'leads/pipelines'), headers=self.headers)
        if response.status_code == 401:
            self.refresh_token()
            self._set_auth_headers()
        elif response.status_code != 200:
            print(f'err {self.sub_domain} amo test_request responded with: {response.status_code}')

    def _get_contacts_by_id(self, _ids: List[int]) -> List[Dict]:
        """ Получить список контактов

        Args:
            _ids: список идентификаторов контактов

        Returns:
            список контактов
        """
        contacts = []
        total = len(_ids)
        step = DATA_LIMIT
        steps = total // step + 1
        for x in range(steps):
            beg = x * step
            fin = x * step + step
            str_ids = '&filter[id][]='.join(map(str, _ids[beg:fin]))
            if not str_ids:
                break
            params = f'filter[id][]={str_ids}' \
                     f'&with=customers' \
                     f'&limit={DATA_LIMIT}' \
                     f'&order=created_at'
            chunk = self.__get_data(endpoint='contacts', params=params)
            if not chunk:
                print('_get_contacts_by_id skip', x, 'ids:', _ids[beg:fin])
                continue
            contacts.extend(chunk)
        return contacts

    def _get_deleted_events(
        self,
        date_from: datetime,
        date_to: datetime,
    ) -> List[Dict]:
        """ Получить список удаленных событий за период

        Args:
            date_from: с
            date_to: по

        Returns:
            список удаленных событий
        """
        # здесь нельзя поставить больше 10
        # см. https://www.amocrm.ru/developers/content/crm_platform/events-and-notes#events-types
        step = 10
        params = f'filter[entity]=lead' \
                 f'&filter[type]={AmoEvent.Deleted.value}' \
                 f'&filter[created_at][from]={date_from.timestamp()}' \
                 f'&filter[created_at][to]={date_to.timestamp()}' \
                 f'&limit={step}' \
                 f'&order=created_at'
        result = self.__get_data(endpoint='events', params=params, limit=step)
        return result

    def _get_events_by_id(self, lead_ids: List[int]) -> List[Dict]:
        """ Получить список событий, связанных со сделками

        Args:
            lead_ids: список идентификаторов сделок

        Returns:
            список событий
        """
        return self.load_events(
            lead_ids=lead_ids,
            event_types=[stage.value for stage in AmoEvent],
        )

    def p_get_data(self, args):
        return self.__get_data(*args)

    def load_events(self, lead_ids: List[int], event_types: List[str]) -> List[Dict]:
        """ Получить список событий, связанных со сделками

        Args:
            lead_ids: список идентификаторов сделок
            event_types: типы событий

        Returns:
            список событий
        """
        result = []
        if not lead_ids:
            return result
        str_statuses = '&filter[type][]='.join(event_types)
        total = len(lead_ids)
        # здесь нельзя поставить больше 10
        # см. https://www.amocrm.ru/developers/content/crm_platform/events-and-notes#events-types
        step = 10
        steps = total // step + 1

        if MULTI_PROCESS:
            # готовим список параметров для параллельной загрузки
            processes_num = 5
            tasks_list = []
            for x in range(steps):
                beg = x * step
                fin = x * step + step
                str_ids = '&filter[entity_id][]='.join(map(str, lead_ids[beg:fin]))
                if not str_ids:
                    break
                params = f'filter[entity_id][]={str_ids}' \
                         f'&filter[entity]=lead' \
                         f'&filter[type][]={str_statuses}' \
                         f'&limit={step}' \
                         f'&order=created_at'
                # здесь важен правильный порядок аргументов
                tasks_list.append(('events', params, None, None, step))
            # запускаем параллельную загрузку
            chunks_dict = object     # fixme 2023-6 ParallelWorker(processes=processes_num).start(func=self.p_get_data, tasks_list=tasks_list)
            for chunk in chunks_dict.values():
                if not chunk:
                    continue
                result.extend(chunk)
        else:
            for x in range(steps):
                beg = x * step
                fin = x * step + step
                msg = f'Получение событий: {x + 1} из {steps}'
                str_ids = '&filter[entity_id][]='.join(map(str, lead_ids[beg:fin]))
                if not str_ids:
                    break
                params = f'filter[entity_id][]={str_ids}' \
                         f'&filter[entity]=lead' \
                         f'&filter[type][]={str_statuses}' \
                         f'&limit={step}' \
                         f'&order=created_at'
                chunk = self.__get_data(endpoint='events', params=params, limit=step, msg=msg)
                if not chunk:
                    continue
                result.extend(chunk)

        return result

    def get_leads(self, date_from: datetime, date_to: datetime) -> bool:
        """ Получить список сделок

        Args:
            date_from: дата с
            date_to: дата по

        Returns:
            True - если получены новые данные
        """
        # с источника мы получаем лиды по updated_at всегда
        params = f'filter[updated_at][from]={date_from.timestamp()}' \
                 f'&filter[updated_at][to]={date_to.timestamp()}' \
                 f'&with=contacts,loss_reason' \
                 f'&limit={250}' \
                 f'&order=created_at'
        return self.get_and_sync_data(endpoint='leads', params=params, db_table='Lead')

    def get_contact_by_id(self, contact_id: Union[int, str]) -> Dict:
        """ Получение контакта по идентификатору  """
        response = self.__execute(endpoint='contacts', entity_id=contact_id)
        return response.json()

    def get_lead_by_id(self, lead_id: Union[int, str]) -> Dict:
        """ Получение лида по идентификатору  """
        params = 'with=contacts,loss_reason'
        response = self.__execute(endpoint='leads', params=params, entity_id=lead_id)
        # print('get_lead_by_id', lead_id, response.status_code)
        try:
            return response.json()
        except:
            print(response.text)
            return {}

    def get_leads_by_pipeline_and_status(self, pipeline_id: Union[int, str], status_id: Union[int, str]) -> List[Dict]:
        """ Получение лидов с указанной воронки / стадии """
        params = f'filter[statuses][0][pipeline_id]={pipeline_id}' \
                 f'&filter[statuses][0][status_id]={status_id}' \
                 f'&with=contacts,loss_reason&limit={250}'
        return self.__get_data(endpoint='leads', params=params)

    def link_chat_with_contact(self, contact_id: int, chat_id: str):
        """ Связывает чат с контактом

        Args:
            contact_id: идентификатор контакта
            chat_id: идентификатор чата
        """
        return self.__execute(
            endpoint='contacts/chats',
            data=[{"contact_id": contact_id, "chat_id": chat_id}],
            method='POST'
        )

    def get_chats(
        self,
        contact_id: Optional[int] = None,
        chat_id: Optional[str] = None,
    ) -> List[Dict]:
        """ Поиск чатов, связанных с контактом, либо по идентификатору

        Args:
            contact_id: идентификатор контакта
            chat_id: идентификатор чата

        Returns:
            список чатов
        """
        params = f'contact_id={contact_id}' if contact_id else f'chat_id={chat_id}'
        response = self.__execute(endpoint='contacts/chats', params=params)
        data = response.json()
        return (data.get('_embedded') or {}).get('chats') or []
        # return self.__get_data(endpoint='contacts/chats', params=params, key='chats')

    def find_leads(self, query: str, limit: int = 1) -> List[Dict]:
        """ Поиск сделок по запросу

        Args:
            query: запрос для поиска
            limit: ограничение по количеству найденных лидов

        Returns:
            список сделок
        """
        params = f'query={query}' \
                 f'&limit={limit}' \
                 f'&order=created_at'
        return self.__get_data(endpoint='leads', params=params)

    def find_contacts(self, query: str, limit: int = 1, field_code: Optional[str] = None) -> List[Dict]:
        """ Поиск сделок по запросу

        Args:
            query: запрос для поиска
            limit: ограничение по количеству найденных лидов
            field_code: код поля, по которому ищем контакт

        Returns:
            список сделок
        """
        _limit = limit
        if field_code:
            # если задано конкретное поле, мы должны вытянуть с источника больше записей для уточнения поиска
            _limit += 10
        query = query.lower()
        params = f'query={query}' \
                 f'&limit={_limit}' \
                 f'&order=created_at'
        collection = self.__get_data(endpoint='contacts', params=params)
        if not field_code:
            return collection
        result = []
        for item in collection:
            for cf in item.get('custom_fields_values') or []:
                if cf.get('field_code') != field_code:
                    continue
                value = (cf.get('values') or [{}])[0].get('value') or ''
                if query in str(value).lower():
                    result.append(item)
                    break
            if len(result) == limit:
                break
        return result

    def _get_pipelines_and_statues(self) -> Dict:
        """ Получить словарь воронок и их статусов

        Returns:
            словарь воронок и их статусов в формате {
                pipeline_id: {
                    'name': pipeline_name
                    'status': {
                        status_id: status_name,
                        ...
                    }
                },
                ...
            }
        """
        result = {}
        response = requests.get(url=self.__get_url(endpoint='pipelines', entity='leads'), headers=self.headers)
        json_response = response.json()
        pipelines = (json_response.get('_embedded') or {}).get('pipelines') or []
        for pipeline in pipelines:
            statuses = (pipeline.get('_embedded') or {}).get('statuses') or []
            result[pipeline['id']] = {
                'name': pipeline['name'],
                'status': {status['id']: status['name'] for status in statuses}
            }
        return result

    def _get_tasks_by_id(self, lead_ids: List[int]) -> List[Dict]:
        """ Получить список задач, связанных со сделками

        Args:
            lead_ids: список идентификаторов сделок

        Returns:
            список контактов
        """
        result = []
        if not lead_ids:
            return result
        total = len(lead_ids)
        step = DATA_LIMIT
        steps = total // step + 1
        for x in range(steps):
            beg = x * step
            fin = x * step + step
            str_ids = '&filter[entity_id][]='.join(map(str, lead_ids[beg:fin]))
            if not str_ids:
                break
            params = f'filter[entity_id][]={str_ids}' \
                     f'&limit={DATA_LIMIT}' \
                     f'&order=created_at'
            chunk = self.__get_data(endpoint='tasks', params=params)
            if not chunk:
                print('_get_tasks_by_id skip', x)
                continue
            result.extend(chunk)
        return result

    def get_user(self, _id: int) -> Dict:
        """ Получить пользователя по идентификатору

        Args:
            _id: идентификатор пользователя

        Returns:
            данные пользователя
        """
        params = f'with=role,group' \
                 f'&limit={DATA_LIMIT}'
        response = self.__execute(endpoint='users', params=params, entity_id=_id)
        return response.json() if response.status_code == 200 else {}

    def get_pipeline_and_status(self, pipeline_id: int, status_id: int) -> Dict:
        """ Название воронки и статуса

        Args:
            pipeline_id: идентификатор воронки
            status_id: идентификатор статуса

        Returns:
            Название воронки и статуса
        """
        response = self.__execute(endpoint=f'leads/pipelines/{pipeline_id}')
        data = response.json() if response.status_code == 200 else {}
        status = {}
        for item in (data.get('_embedded') or {}).get('statuses') or []:
            if item['id'] == int(status_id):
                status = item
                break
        return {'pipeline': data.get('name'), 'status': status.get('name')}

    def get_users(self) -> bool:
        """ Получить список пользователей

        Returns:
            True - если получены новые данные
        """
        params = f'with=role,group' \
                 f'&limit={DATA_LIMIT}'
        return self.get_and_sync_data(endpoint='users', params=params, limit=50, db_table='User')

    def __get_token_data(self):
        return self.session.query(self.token).order_by(self.token.id.desc()).first()

    def _set_auth_headers(self):
        """ Устанавливает заголовки авторизации """
        token_data = self.__get_token_data()
        if not token_data:
            return
        self.headers = {
            'Authorization': f'Bearer {token_data.access_token}'
        }

    def __get_data(
        self,
        endpoint: str,
        params: str,
        page: Optional[int] = None,
        limit: int = DATA_LIMIT,
        entity: str = '',
        entity_id: Optional[int] = None,
        msg: str = '',
        key: Optional[str] = None
    ) -> List[Dict]:
        """ Получение данных с эндпоинта порциями

        Args:
            endpoint: адрес запроса (leads, contacts, etc.)
            params: параметры запроса (сортировка, даты и проч.)
            limit: ограничение по размеру выдачи
            entity: сущность, например, leads, может использоваться как дополнение к эндпоинту
            entity_id: идентификатор сущности
            key: ключ данных в _embedded

        Returns:
            данные из AMO
        """
        has_page = page is not None
        page = page or 0
        base_params = params
        while True:
            page += 1
            params = f'{base_params}&page={page}'
            response = self.__execute(endpoint=endpoint, params=params, entity=entity, entity_id=entity_id)
            if not response:
                print('no response', response)
                break
            # нет данных - выходим из цикла
            if response.status_code == 204:
                print(f'{datetime.now()} response.status_code == 204', response.text)
                break
            try:
                json_response = response.json()
                # print(response.status_code, len((json_response.get('_embedded') or {}).get(endpoint) or []))
            except requests.exceptions.JSONDecodeError as exc:
                print('JSONDecodeError')
                if '500 Internal Server Error' in response.text:
                    print(f'{endpoint} 500 Internal Server Error')
                elif '414 Request-URI Too Large' in response.text:
                    print(f'{endpoint} 414 Request-URI Too Large')
                raise exc
            except Exception as exc:
                print(exc)
                print(response.status_code, response.text)
            chunk = (json_response.get('_embedded') or {}).get(key or endpoint) or []
            for item in chunk:
                yield item
            if has_page:
                break
            sleep(random.uniform(0.1, REQUEST_SLEEP_INTERVAL))
            # нам вернули данных меньше предельного размера чанка, значит, записей больше нет
            if len(chunk) < limit:
                break

    def get_and_sync_data(
        self,
        endpoint: str,
        params: str,
        limit: int = DATA_LIMIT,
        entity: str = '',
        entity_id: Optional[int] = None,
        db_table: str = '',
        key: Optional[str] = None
    ) -> bool:
        """ Читает данные с источника и записывает их построчно в указанную таблицу БД (синхронизирует)

        Args:
            endpoint: адрес запроса (leads, contacts, etc.)
            params: параметры запроса (сортировка, даты и проч.)
            limit: ограничение по размеру выдачи
            entity: сущность, например, leads, может использоваться как дополнение к эндпоинту
            entity_id: идентификатор сущности
            db_table: таблица БД, с которой производится синхронизация данных
            key: ключ данных в _embedded

        Returns:
            True - если были вставлены или обновлены записи
        """
        page = 0
        base_params = params
        engine = get_engine()
        updated_or_inserted_records = []
        with engine.begin() as connection:
            while True:
                page += 1
                params = f'{base_params}&page={page}'
                response = self.__execute(endpoint=endpoint, params=params, entity=entity, entity_id=entity_id)
                if not response:
                    print('no response', response)
                    break
                # нет данных - выходим из цикла
                if response.status_code == 204:
                    print(f'{datetime.now()} response.status_code == 204', response.text)
                    break
                try:
                    json_response = response.json()
                    # print(response.status_code, len((json_response.get('_embedded') or {}).get(endpoint) or []))
                except requests.exceptions.JSONDecodeError as exc:
                    print('JSONDecodeError')
                    if '500 Internal Server Error' in response.text:
                        print(f'{endpoint} 500 Internal Server Error')
                    elif '414 Request-URI Too Large' in response.text:
                        print(f'{endpoint} 414 Request-URI Too Large')
                    raise exc
                except Exception as exc:
                    print(exc)
                    print(response.status_code, response.text)
                chunk = (json_response.get('_embedded') or {}).get(key or endpoint) or []
                records = [item for item in chunk]
                result = self.sync_controller.sync_records(
                    records=records,
                    table_name=db_table,
                    connection=connection,
                    engine=engine
                )
                updated_or_inserted_records.append(result)
                sleep(random.uniform(0.1, REQUEST_SLEEP_INTERVAL))
                # нам вернули данных меньше предельного размера чанка, значит, записей больше нет
                if len(chunk) < limit:
                    break
        return any(updated_or_inserted_records)

    def __get_url(self, endpoint: str, params: str = '', entity: str = '', entity_id: Optional[int] = None):
        """ Адрес для запроса в AMO

        Args:
            endpoint: эндпоинт для запроса
            params: дополнительные параметры запроса
            entity: сущность, например, leads, может использоваться как дополнение к эндпоинту
            entity_id: идентификатор сущности

        Returns:
            Адрес для запроса в AMO
        """
        if entity:
            entity = f'{entity}/'
        entity_id = f'/{entity_id}' if entity_id else ''
        url = f"https://{self.sub_domain}.{self.domain}/{entity}{endpoint}{entity_id}"
        if params:
            url = f'{url}?{params}'
        # print('fetching...', url)
        return url

    def __execute(
        self,
        endpoint: str,
        params: str = '',
        entity: str = '',
        entity_id: Optional[int] = None,
        method: str = 'GET',
        data: Optional[Union[Dict, List]] = None
    ) -> requests.Response:
        """ Выполнение запроса с повторными попытками

        Args:
            endpoint: адрес
            params: строковые параметры
            entity: сущность, например, leads, может использоваться как дополнение к эндпоинту
            entity_id: идентификатор сущности
            method: HTTP-метод
            data: данные, отправляемые на сервер в теле запроса

        Returns:
            ответ от сервера
        """
        response = None
        while not response:
            try:
                if method == 'GET':
                    response = requests.get(
                        url=self.__get_url(endpoint=endpoint, params=params, entity=entity, entity_id=entity_id),
                        headers=self.headers
                    )
                    # todo вот тут надо бы обработать всякие 401 - "не авторизован"
                    # print(response.text)
                elif method == 'PATCH':
                    response = requests.patch(
                        url=self.__get_url(endpoint=endpoint, params=params, entity=entity, entity_id=entity_id),
                        headers=self.headers,
                        data=json.dumps(data)
                    )
                    return response
                elif method == 'POST':
                    response = requests.post(
                        url=self.__get_url(endpoint=endpoint, params=params, entity=entity, entity_id=entity_id),
                        headers=self.headers,
                        json=data
                    )
                    return response
                else:
                    raise Exception(f'unknown method {method}')     # todo
                if not response.text:
                    break
                try:
                    json_response = response.json()
                except ValueError:
                    json_response = json.loads(response.text)
                # print(response.status_code, json_response)
                if json_response.get('status') == 401:
                    print('refreshing token')
                    self.refresh_token()
                    self._set_auth_headers()
            except requests.exceptions.ConnectionError:
                # повторный запрос
                sleep(REQUEST_SLEEP_INTERVAL)
            except Exception as exc:
                print(exc)
                if response:
                    print(response.text)
                sleep(REQUEST_SLEEP_INTERVAL)
        return response


class DrvorobjevAPIClient(APIClient):
    """ API-клиент AMO для Drvorobjev """
    credentials: db.Model = CDVAmoCredentials
    token: db.Model = CDVAmoToken
    lead: db.Model = CDVLead
    pipeline: db.Model = CDVPipeline
    contact: db.Model = CDVContact
    event: db.Model = CDVEvent
    note: db.Model = CDVNote
    user: db.Model = CDVUser
    sub_domain = 'drvorobjev'
    referer_field_id: int = 518713
    utm_map: Dict = {
        'utm_source': 46631,
        'utm_medium': 498455,
        'utm_campaign': 46619,
        'utm_content': 46633,
        'utm_term': 498811,
        'utm_original': 498813,
        'gclid': 498451,
        'fbclid': 498815,
    }
    sync_controller_class: TSyncController = CDVSyncController

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class SwissmedicaAPIClient(APIClient):
    """ API-клиент AMO для Swissmedica """
    credentials: db.Model = SMAmoCredentials
    token: db.Model = SMAmoToken
    lead: db.Model = SMLead
    pipeline: db.Model = SMPipeline
    contact: db.Model = SMContact
    event: db.Model = SMEvent
    note: db.Model = SMNote
    user: db.Model = SMUser
    sub_domain = 'swissmedica'
    referer_field_id: int = 954029
    utm_map: Dict = {
        'utm_source': 954543,
        'utm_medium': 954545,
        'utm_campaign': 954547,
        'utm_content': 968677,
        'utm_term': 956715,
        'referer': 954029,
        'ym_cid': 1102815,
        'lead_url': 1102817
    }
    sync_controller_class: TSyncController = SMSyncController

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
