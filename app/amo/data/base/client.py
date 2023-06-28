""" Базовый клиент для отдельных бизнесов для работы с данными из различных источников: AMO, телефония и проч. """
__author__ = 'ke.mizonov'
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Tuple
# from amo.api.client import DrvorobjevAPIClient, SwissmedicaAPIClient
from utils.functions import get_current_timeshift
from utils.serializer import PklSerializer
from worker.worker import Worker

# TApiClient = Union[DrvorobjevAPIClient, SwissmedicaAPIClient]


class Client:
    """ Базовый клиент для работы с данными """
    api_client: Callable = NotImplemented
    time_shift: int = 0

    @property
    def alive_leads_file_name(self) -> str:
        return f'{self.api_client.sub_domain}_alive_leads'

    @property
    def deleted_leads_file_name(self) -> str:
        return f'{self.api_client.sub_domain}_deleted_leads'

    @property
    def leads_file_name(self) -> str:
        return f'{self.api_client.sub_domain}_leads'

    def get_deleted_leads(self, worker: Optional[Worker] = None) -> List[Dict]:
        """ Получить список удаленных сделок + Обновить инфу об удалении в сделках """
        result = []
        # считываем сделки из файла
        serializer = PklSerializer(file_name=self.leads_file_name)
        leads = serializer.load()
        # получаем события удаления
        events = self.api_client().get_deleted_events(worker=worker)
        events_dict = {
            event['entity_id']: {'user': event['user'], 'date': event['created_at'] + self.time_shift}
            for event in events
        }
        # ищем подходящие под события лиды
        has_changes = False
        for lead in leads:
            event: Dict = events_dict.get(lead['id'])
            if not event:
                # нет события удаления
                continue
            has_changes = True
            lead['deleted'] = event
            result.append(lead)
        # сохраняем список лидов
        if has_changes:
            serializer.save(leads)
        return result

    @classmethod
    def get_lead_url_by_id(cls, lead_id: int) -> str:
        """ Получение ссылки на сделку по идентификатору """
        return cls.api_client.get_lead_url_by_id(lead_id=lead_id)

    def get_leads(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        forced_load: bool = False,
        worker: Optional[Worker] = None,
        date_key: str = 'updated_at',
        mixin_notes: bool = True,
        ids: Optional[List[int]] = None
    ) -> List[Dict]:
        """ Получить список сделок

        Args:
            date_from: дата с
            date_to: дата по
            forced_load: True - принудительная загрузка из AMO
            worker: экземпляр воркера фонового процесса
            date_key: поле даты (updated_at / created_at)
            mixin_notes: True - подмешивать примечания
            ids: явно переданные идентификаторы лидов

        Returns:
            список сделок
        """
        serializer = PklSerializer(file_name=self.leads_file_name)
        leads_from_file: List[Dict] = []
        # делаем поправку на часовой пояс:
        #   get_current_timeshift - часовой пояс машины, с которой запускается скрипт
        #   self.time_shift - часовой пояс клиента, взятый из настроек Amo
        date_from_stamp, date_to_stamp = None, None
        if date_from and date_to:
            date_from += timedelta(hours=get_current_timeshift() - self.time_shift)
            date_to += timedelta(hours=get_current_timeshift() - self.time_shift)
            date_from_stamp, date_to_stamp = date_from.timestamp(), date_to.timestamp()
        # попытка считать сделки из файла (если не заявлена принудительная загрузка из AMO)
        if not forced_load:
            if worker:
                worker.emit({'msg': f'Reading leads from file "{self.leads_file_name}.pkl"'})
            leads = serializer.load() or []
            total = len(leads)
            for num, lead in enumerate(leads, 1):

                # if num % 10000 == 0:
                #     print(f'{num} of {total}')

                # # fixme del
                # if lead['id'] == 33836633:
                #     print(lead)

                # if lead['id'] == 22782321:
                #     for k, v in lead.items():
                #         print(k, '::', v)

                if worker and num % 100 == 0:
                    worker.emit({'num': num, 'total': total})
                # пропускам лиды, выходящие за пределы диапазона дат или не относящиеся к текущему домену
                if not ids and date_from_stamp and date_to_stamp and \
                        (not lead[date_key] or not (date_from_stamp <= lead[date_key] <= date_to_stamp)):
                    continue
                if ids and lead['id'] not in ids:
                    continue
                if lead['sub_domain'] != self.api_client.sub_domain:
                    continue
                # # преобразование времени лида
                # for k, v in lead.items():
                #     print(k, '::', v)
                # print()
                leads_from_file.append(lead)
        # сделки из файла получены - вернем их
        if leads_from_file:
            if mixin_notes:
                print('mixin_notes...')
                self._mixin_notes(leads=leads_from_file)
                print('mixin_events...')
                self._mixin_events(leads=leads_from_file)
            return leads_from_file
        print('Loading leads from AMO')
        if worker:
            worker.emit({'msg': f'Loading leads from AMO into "{self.leads_file_name}.pkl"', 'num': 0, 'total': 0})
        # загрузка сделок из AMO
        if not date_from or not date_to:
            if worker:
                worker.emit({'msg': f'Unable to load leads from AMO without specified period of time'})
            return []
        api_client = self.api_client()
        leads_from_amo: List[Dict] = api_client.get_leads(date_from=date_from, date_to=date_to, worker=worker)
        # добавление отсутствующих сделок в файл
        leads_from_file: List[Dict] = serializer.load() or []
        leads_from_file_dict = {lead['id']: lead for lead in leads_from_file}
        total = len(leads_from_amo)
        for num, lead in enumerate(leads_from_amo, 1):
            # if lead['is_deleted']:
            # print('>>>', lead)
            _id = lead['id']
            # такого лида в файлах нет - добавим
            # if _id not in leads_from_file_dict.keys():
            #     # print('appending')
            if worker and num % 1000 == 0:
                worker.emit({'msg': f'Обновление файла сделок', 'num': num, 'total': total})
            # дата обновления лида отличается - перезапишем его
            if leads_from_file_dict.get(_id):
                leads_from_file_dict[_id] = lead
            else:
                leads_from_file_dict[_id] = lead
                leads_from_file.append(lead)
        # тут обязательно переписываем лид, т.к. выше мы меняли по ссылке другой объект (!)
        leads_from_file = [lead for lead in leads_from_file_dict.values()]
        total = len(leads_from_file)
        # подмешиваем события удаления сделок, попутно сохраняем те из них, для которых не нашлось лидов
        deleted_events = api_client.get_deleted_events(date_from=date_from, date_to=date_to, worker=worker)
        for num, lead in enumerate(leads_from_file, 1):
            if worker and num % 1000 == 0:
                worker.emit({'msg': 'Подмешиваем события удаления сделок к лидам', 'num': num, 'total': total})
            deleted_event = deleted_events.get(lead['id'])
            if not deleted_event:
                continue
            lead['deleted'] = deleted_event
            deleted_events.pop(lead['id'])
        # сохраняем события удаления, для которых не нашлось лидов, в файл
        if worker:
            worker.emit({'msg': 'Сохраняем события удаления сделок'})
        if deleted_events:
            deleted_serializer = PklSerializer(file_name=self.deleted_leads_file_name)
            deleted_events_from_file = deleted_serializer.load() or {}
            deleted_events_from_file.update(deleted_events)
            if deleted_events_from_file:
                deleted_serializer.save(deleted_events_from_file)
        # сортировка и сохранение лидов
        if worker:
            worker.emit({'msg': 'Сохраняем список сделок'})
        leads_from_file = sorted(leads_from_file, key=lambda x: x['created_at'])
        serializer.save(leads_from_file)
        if mixin_notes:
            print('mixin_notes...')
            self._mixin_notes(leads=leads_from_file)
            print('mixin_events...')
            self._mixin_events(leads=leads_from_file)
        return leads_from_amo

    # def update_alive_leads(self, leads: List[Dict]):
    #     """ Обновить стату по менеджерам (активные лиды, срез по датам)
    #
    #     Args:
    #         leads: все имеющиеся на данный момент лиды, загруженные из амо
    #     """
    #     serializer = PklSerializer(file_name=self.alive_leads_file_name)
    #     # вычитываем общий список живых лидов
    #     alive_leads: List = serializer.load() or []
    #     # удаляем прежние записи за текущую дату
    #     current_date = datetime.now().date()
    #     to_delete = [num for num, lead in enumerate(alive_leads) if lead['date'] == current_date]
    #     for num in to_delete:
    #         alive_leads.pop(num)
    #     # аккумулируем активные лиды за весь период в словарик по менеджерам и воронкам
    #     unique_leads = {}
    #     for lead in leads:
    #         if lead['at_work_any_pipeline'] != 1:
    #             continue
    #         key = (lead['pipeline_name'], lead['responsible_user_name'])
    #         if key not in unique_leads:
    #             unique_leads[key] = 0
    #         unique_leads[key] += 1
    #     # из словарика данные переносим в общий список живых лидов
    #     for lead, at_work_any_pipeline in unique_leads.items():
    #         alive_leads.append({
    #             'date': current_date,
    #             'pipeline_name': lead[0],
    #             'responsible_user_name': lead[1],
    #             'at_work_any_pipeline': at_work_any_pipeline
    #         })
    #     serializer.save(alive_leads)
    #     for lead in alive_leads:
    #         print(lead)

    def load_additional_events(
        self,
        date_from: datetime,
        date_to: datetime,
        event_types: List[str],
        worker: Optional[Worker] = None
    ):
        """ Догрузить список событий определенных типов для всех сделок

        Args:
            date_from: дата с
            date_to: дата по
            event_types: типы событий
            worker: экземпляр воркера фонового процесса

        Returns:
            список событий
        """
        serializer = PklSerializer(file_name=self.leads_file_name)
        leads = serializer.load()
        # делаем поправку на часовой пояс:
        date_from += timedelta(hours=get_current_timeshift() - self.time_shift)
        date_to += timedelta(hours=get_current_timeshift() - self.time_shift)
        date_from_stamp, date_to_stamp = date_from.timestamp(), date_to.timestamp()
        lead_ids = [lead['id'] for lead in leads if date_from_stamp <= lead['created_at'] <= date_to_stamp]
        events = self.api_client().load_events(
            lead_ids=lead_ids,
            event_types=event_types,
            worker=worker
        )
        events_data_dict = {_id: [] for _id in lead_ids}
        for event in events:
            events_data_dict[event['entity_id']].append(event)
        # подмиксовываем догруженные события к лидам, не забываем о повторах и сортировке
        for lead in leads:
            if not (date_from_stamp <= lead['created_at'] <= date_to_stamp):
                continue
            new_events = lead.get('events')
            events_ids = tuple(event['id'] for event in lead.get('events') or [])
            for event in events_data_dict.get(lead['id']) or []:
                # if lead['id'] == 22734727:
                #     print(event)
                if event['id'] in events_ids:
                    continue
                new_events.append(event)
            lead['events'] = sorted(new_events, key=lambda x: x['created_at'])
            # if lead['id'] == 22734727:
            #     print('new_events', new_events)
            #     print('events', lead['events'])
        # обновляем файл с лидами
        serializer.save(leads)

    def _mixin_notes(self, leads: List[Dict]):
        """ Примешать примечания

        Args:
            leads: список лидов, к которым относятся примечания
        """
        # идентификаторы контактов
        contact_ids = []
        for lead in leads:
            for contact in lead.get('contacts') or []:
                contact_ids.append(contact['id'])
        # считываем примечания для лидов и контактов (в виде словарей)
        leads_notes_dict = self.__read_notes(entity='leads', entity_ids=tuple(lead['id'] for lead in leads))
        contacts_notes_dict = self.__read_notes(entity='contacts', entity_ids=tuple(contact for contact in contact_ids))
        if not leads_notes_dict and not contacts_notes_dict:
            return
        # подмешиваем примечания к лидам, используя словари примечаний
        for lead in leads:
            # if lead['id'] == 22782321:
            #     print(lead.get('tasks'))
            #     print(contacts_notes_dict.get(27611103))
            lead['notes'] = leads_notes_dict.get(lead['id']) or []
            for contact in lead.get('contacts') or []:
                for note in contacts_notes_dict.get(contact['id']) or []:
                    # if lead['id'] == 22782321:
                    #     print(note)
                    lead['notes'].append(note)

    def __read_notes(self, entity: str, entity_ids: Tuple) -> Dict:
        """ Считывает примечания для указанной сущности

        Args:
            entity: сущность
            entity_ids: кортеж идентификаторов сущности

        Returns:
            словарь вида { entity_id: [notes_list] }
        """
        notes = PklSerializer(file_name=f'{self.api_client.sub_domain}_{entity}_notes').load() or []
        if not notes:
            return {}
        notes = sorted(notes, key=lambda x: x['created_at'])
        notes_dict = {note['entity_id']: [] for note in notes if note['entity_id'] in entity_ids}
        for note in notes:
            if note['entity_id'] not in entity_ids:
                continue
            # # подмешиваем пользователей к примечаниям
            # note['user'] = users_dict.get(note['created_by'])
            notes_dict[note['entity_id']].append(note)
        return notes_dict

    def _mixin_events(self, leads: List[Dict]):
        """ Примешать события

        Args:
            leads: список лидов, к которым относятся события
        """
        # считываем примечания для лидов и контактов (в виде словарей)
        leads_events_dict = self.read_events(entity='leads', entity_ids=tuple(lead['id'] for lead in leads))
        # print('::::::')
        # for k, v in leads_events_dict.items():
        #     print(k, '::', v)
        #     break
        if not leads_events_dict:
            return
        for lead in leads:
            lead['events'] = leads_events_dict.get(lead['id']) or []
            # print(lead['events'])

    def read_events(self, entity: str, entity_ids: Tuple) -> Dict:
        """ Считывает события для указанной сущности

        Args:
            entity: сущность
            entity_ids: кортеж идентификаторов сущности

        Returns:
            словарь вида { entity_id: [events_list] }
        """
        events = PklSerializer(file_name=f'{self.api_client.sub_domain}_{entity}_events').load() or []
        if not events:
            return {}
        events = sorted(events, key=lambda x: x['created_at'])
        events_dict = {event['entity_id']: [] for event in events if event['entity_id'] in entity_ids}
        for note in events:
            if note['entity_id'] not in entity_ids:
                continue
            events_dict[note['entity_id']].append(note)
        return events_dict
