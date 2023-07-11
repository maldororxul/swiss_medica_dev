""" Модуль для расчета скорости реакции менеджеров на появление новой сделки """
__author__ = 'ke.mizonov'
from enum import Enum
from typing import Dict, List, Optional, Callable, Tuple
from app.amo.api.constants import AmoEvent, AmoNote
from app.amo.data.base.data_schema import Lead


class CommunicationBase:
    """ Вычисляет эффективность коммуникации по событиям и примечаниям к сделке,
        в частности считает скорость реакции менеджера
    """
    def __init__(
        self,
        sub_domain: str,
        leads: List[Dict],
        time_shift_function: Callable,
        trying_to_get_in_touch: Optional[Tuple] = None,
        closed: Optional[Tuple] = None,
        schedule: Optional[Dict] = None
    ):
        """
        Args:
            sub_domain: поддомен amo
            leads: список сделок
            time_shift_function: функция преобразования времени к нужному часовому поясу
            trying_to_get_in_touch: стадии воронки amo, обозначающие выход на контакт
            closed: стадии воронки amo, обозначающие закрытие сделки
            schedule: расписание работы менеджеров
        """
        self.sub_domain = sub_domain
        self.leads = leads
        self.schedule = schedule
        self.time_shift_function: Callable = time_shift_function
        self.trying_to_get_in_touch = trying_to_get_in_touch or []
        self.closed = closed or []

    class CallSource(Enum):
        Itgrix = 'itgrix_amo'
        Moizvonki = 'moizvonkiru'

    class Field(Enum):
        """ Поля данных для вычисления скорости реакции """
        CreatedAt = 'created_at'
        CreationSource = 'creation_source'
        OnDuty = 'on_duty'
        FastestReaction = 'fastest_reaction'
        FirstSuccessfulIncomingCall = 'first_successful_incoming_call'
        IncomingCall = 'incoming_call'
        OutgoingCall = 'outgoing_call'
        IncomingEmail = 'incoming_email'
        OutgoingEmail = 'outgoing_email'
        IncomingChat = 'incoming_chat'
        OutgoingChat = 'outgoing_chat'
        CompletedTask = 'completed_task'
        UserNote = 'user_note'
        # переназначения лида на другого ответственного
        Reassignment = 'reassignment'
        TryingToGetInTouch = 'trying_to_get_in_touch'
        Closed = 'closed'

    def process(self):
        """ Подмешивает к списку лидов данные о скорости реакции менеджеров """
        # считываем пользователей
        users = PklSerializer(file_name=f'{self.sub_domain}_users').load() or []
        users_dict = {user['id']: user for user in users}
        # считываем словарь воронок и статусов
        pipelines_dict = PklSerializer(file_name=f'{self.sub_domain}_pipelines').load() or []
        for lead in self.leads:
            # пропускаем удаленные лиды
            if lead.get('deleted') or lead.get('deleted_leads'):
                continue
            lead[Lead.OnDuty.Key] = 'duty time'
            if not lead[Lead.Stage.Lead.Key]:
                continue
            # строим словарь данных с ключевыми событиями и примечаниями
            reaction = self.__build_reaction_data(lead=lead, pipelines_dict=pipelines_dict, users_dict=users_dict)
            # for k, v in reaction.items():
            #     print(k, '::', v)
            # print()
            # считаем время реакции на сделку
            # print(lead['id'])
            reaction_time = self.__calculate_first_reaction_time(reaction=reaction)
            # communication = self.__calculate_communication_process(reaction=reaction)
            # lead.update(communication)

            # if lead['id'] in (23559761, ):
            #     print('>>', lead['id'], lead['created_at'])
            #     for k, v in reaction.items():
            #         print(k, '::', v)
            #     print()
            #     for k, v in reaction_time.items():
            #         print(k, '::', v)
            #     print()

            # if lead['id'] == 23306909:
            #     print('\n=== reaction ===')
            #     for k, v in reaction.items():
            #         print(k, '::', v)
            #     print()
            #     print('\n=== reaction_time ===')
            #     for k, v in reaction_time.items():
            #         print(k, '::', v)
            #     print()
            # записываем время реакции в сделку
            self.__mixin_reaction_to_lead(lead=lead, reaction_time=reaction_time)
            # удаляем временные поля
            for key in ('created_at_ts', 'notes', 'events', 'tasks'):
                lead.pop(key)

    @staticmethod
    def __get_creation_source(
        name: str,
        tags: str,
        input_field: str,
        creation_events: List[Dict],
        creation_notes: List[Dict]
    ) -> str:
        """ Находит событие, совпадающее по времени с созданием лида и определяет его источник

        Args:
            name: имя лида
            tags: строка тегов
            input_field: значение поля INPUT (данные формы захвата)
            creation_events: события, совпадающие по дате с созданием лида
            creation_notes: примечания, совпадающие по дате с созданием лида

        Returns:
            источник лида (входящий звонок, чат и проч.)
        """
        # определяем источник лида по примечаниям создания
        for note in creation_notes:
            # print('note', note)
            params = note.get('params') or {}
            text = params.get('text')
            _type = note.get('note_type')
            if _type == 'call_in':
                source = params.get('source')
                result = 'Incoming call'
                return f'{result} {source}' if source else result
            elif _type == 'call_out':
                source = params.get('source')
                result = 'Outgoing call'
                return f'{result} {source}' if source else result
            elif _type == 'amomail_message':
                return f"Capture form {params.get('subject')}"
            elif text:
                if '?utm' in text or '&utm' in text or '&amp;utm' in text or '.com' in text:
                    return f'Capture form {text}'
                elif text == 'Not available.' or 'lpsecret':
                    return 'Capture form <Other>'
                # print('unknown note >>>', note)
                # return 'Incoming chat Jivo?'
            else:
                pass
                # if note.get('created_at') == 1678860669:
                # print('unknown note >>>', note)
        # определяем источник лида по событиям создания
        for event in creation_events:
            # if event.get('created_at') == 1678860669:
            #     print('event', event)
            # print('event', event)
            if event.get('type') == 'lead_added' and event.get('created_by') > 0:
                return 'Manually created'
            if event.get('type') == 'incoming_chat_message':
                after = event.get('value_after')
                if not after:
                    continue
                msg = after[0].get('message')
                if not msg:
                    continue
                origin = msg.get('origin')
                if origin == 'e-chat.tech':
                    return 'Incoming chat Viber'
                elif origin == 'com.amocrm.amocrmwa':
                    return 'Incoming chat WhatsApp'
                else:
                    return 'Incoming chat'
            elif event.get('type') == 'incoming_call':
                return 'Incoming call'
        if input_field:
            if 'https://' in input_field:
                return f"Capture form {input_field.split('https://')[1].split(' ')[0]}"
            elif 'http://' in input_field:
                return input_field.split('http://')[1].split(' ')[0]
            elif '@' in input_field:
                return 'Capture form <Other>'
        # определяем источник лида по тегам
        tags = tags.lower()
        if 'itgrix' in tags:
            return 'Incoming call Itgrix'
        elif 'jivo' in tags:
            return 'Incoming chat Jivo'
        elif 'sipuni' in tags:
            return 'Incoming call Sipuni'
        elif 'phone' in tags:
            return 'Incoming call Phone'
        elif 'kontact-forma' in tags or 'tilda' in tags or 'contactform' in tags or 'invite' in tags:
            return f'Capture form {tags}'
        name = name.lower()
        if 'исходящий' in name:
            return 'Outgoing call'
        elif 'входящий' in name:
            return 'Incoming call'
        return ''

    def __build_reaction_data(self, lead: Dict, pipelines_dict: Dict, users_dict: Dict) -> Dict:
        """ Строит словарь данных о взаимодействии менеджера с клиентом по событиям и примечаниям к сделке

        Args:
            lead: сделка
            pipelines_dict: словарь воронок и этапов сделки
            users_dict: словарь пользователей amo

        Returns:
            Словарь с историей взаимодействий с клиентом (звонки, сообщения, примечания)
        """
        # здесь используем оригинальный таймстэмп лида
        dt = self.time_shift_function(unix_ts=lead['created_at_ts'])
        reaction = {
            self.Field.CreatedAt.value: dt,
            self.Field.CreationSource.value: '',
            self.Field.IncomingCall.value: [],
            self.Field.OutgoingCall.value: [],
            self.Field.IncomingEmail.value: [],
            self.Field.OutgoingEmail.value: [],
            self.Field.IncomingChat.value: [],
            self.Field.OutgoingChat.value: [],
            self.Field.UserNote.value: [],
            # завершенные задачи
            self.Field.CompletedTask.value: [],
            # переназначения лида на другого ответственного
            self.Field.Reassignment.value: [],
            self.Field.TryingToGetInTouch.value: [],
            self.Field.Closed.value: []
        }

        for call_source in self.CallSource:
            reaction[f'{self.Field.IncomingCall.value}__{call_source.value}'] = []
            reaction[f'{self.Field.OutgoingCall.value}__{call_source.value}'] = []

        # if lead['id'] == 23275907:
        #     print('lead created_at', dt)
        #     for k, v in lead.items():
        #         print(k, '::', v)
        # перебор примечаний
        # for note in lead.get('notes') or []:
        creation_notes = []
        for note in sorted(lead.get('notes') or [], key=lambda x: x['created_at']):
            if abs(note['created_at'] - lead['created_at_ts']) <= 10:
                # print('event', self.time_shift_function(event['created_at']), event['type'], event)
                creation_notes.append(note)
            elif note['note_type'] == 'call_in' \
                    and str(lead['created_at_ts']) in str((note.get('params') or {}).get('uniq')):
                # дата создания лида может лежать в параметре 'uniq' в строковом формате
                #   - при этом дата создания заметки будет отличаться от даты создания лида
                creation_notes.append(note)

            # if lead['id'] == 23559761:
            #     print('note', self.time_shift_function(note['created_at']), note['note_type'], note.get('params'), note)

            dt = self.time_shift_function(unix_ts=note['created_at'])
            _type = note['note_type']
            note_params = note.get('params') or {}
            created_by = note.get('created_by')
            user = (users_dict.get(created_by) or {}).get('name')
            key = None
            extra_key = None
            if _type == AmoNote.Email.value:
                key = self.Field.IncomingEmail.value if note_params.get('income') else self.Field.OutgoingEmail.value
            elif _type == AmoNote.OutcomeCall.value:
                source = note_params.get('source')
                if source and source in ('itgrix_amo', 'moizvonkiru'):
                    key = f'{self.Field.OutgoingCall.value}__{source}'
                else:
                    key = self.Field.OutgoingCall.value
                extra_key = self.Field.OutgoingCall.value
            elif _type == AmoNote.IncomeCall.value:
                source = note_params.get('source')
                if source and source in ('itgrix_amo', 'moizvonkiru'):
                    key = f'{self.Field.IncomingCall.value}__{source}'
                else:
                    key = self.Field.IncomingCall.value
                extra_key = self.Field.IncomingCall.value
            elif _type == AmoNote.Common.value and user:
                key = self.Field.UserNote.value
            if key:
                reaction[key].append({'date': dt, 'user': user, 'params': note_params})
            if extra_key:
                reaction[extra_key].append({'date': dt, 'user': user, 'params': note_params})
        creation_events = []
        # перебор событий
        for event in sorted(lead.get('events') or [], key=lambda x: x['created_at']):

            # if event['created_at'] == lead['created_at']:
            #     print('event', self.time_shift_function(event['created_at']), event['type'], event)

            # if lead['id'] == 23559761:
            if abs(event['created_at'] - lead['created_at_ts']) <= 10:
                # print('event', self.time_shift_function(event['created_at']), event['type'], event)
                creation_events.append(event)

            dt = self.time_shift_function(unix_ts=event['created_at'])
            created_by = event.get('created_by')
            event_params = event.get('params') or {}
            user = (users_dict.get(created_by) or {}).get('name')
            _type = event['type']
            key = None
            if _type == AmoEvent.StageChanged.value:
                value_after = event.get('value_after') or []
                lead_status = value_after[0].get('lead_status') or {}
                pipeline_id = lead_status.get('pipeline_id')
                status_id = lead_status.get('id')
                pipeline = pipelines_dict.get(pipeline_id) or {}
                status = (pipeline.get('status') or {}).get(status_id)
                if status in self.trying_to_get_in_touch:
                    key = self.Field.TryingToGetInTouch.value
                elif status in self.closed:
                    key = self.Field.Closed.value
            elif _type == AmoEvent.ResponsibleChanged.value and user:
                key = self.Field.Reassignment.value
            elif _type == AmoEvent.IncomeChat.value:
                key = self.Field.IncomingChat.value
            elif _type == AmoEvent.OutcomeChat.value:
                key = self.Field.OutgoingChat.value
            if key:
                reaction[key].append({'date': dt, 'user': user, 'params': event_params})
        # перебор задач
        completed_tasks = []
        for task in lead.get('tasks') or []:
            # if lead['id'] == 22782321:
            #     print('task', self.time_shift_function(task['updated_at']), task)
            if not task.get('is_completed'):
                continue
            dt = self.time_shift_function(unix_ts=task['updated_at'])
            responsible_user_id = task.get('responsible_user_id')
            user = (users_dict.get(responsible_user_id) or {}).get('name')
            completed_tasks.append({'date': dt, 'user': user, 'params': {}})
        reaction[self.Field.CompletedTask.value] = sorted(completed_tasks, key=lambda x: x['date'])
        # источник лида
        # print(lead)
        # if lead['id'] in (23582097,):
        reaction[self.Field.CreationSource.value] = self.__get_creation_source(
            name=lead.get('name') or '',
            tags=lead.get('tags') or '',
            input_field=lead.get(Lead.InputField.Key),
            creation_events=creation_events,
            creation_notes=creation_notes
        )
        # if lead['id'] == 23090379:
        #     print(lead['id'])
        #     for k, v in reaction.items():
        #         print(k, '::', v)
        #     print()

        return reaction

    # def __extract_events_and_notes(self, lead: Dict, users_dict: Dict) -> List:
    #     """ Вытаскивает все события и примечания лида
    #
    #     Args:
    #         lead: сделка
    #         users_dict: словарь пользователей amo
    #
    #     Returns:
    #         Список событий и примечаний лида
    #     """
    #     actions = []
    #     # перебор примечаний
    #     for note in lead.get('notes') or []:
    #         actions.append({
    #             'date': self.time_shift_function(unix_ts=note['created_at']),
    #             'entity': 'note',
    #             'type': note['note_type'],
    #             'user': (users_dict.get(note.get('created_by')) or {}).get('name'),
    #             'params': note.get('params') or {}
    #         })
    #     # перебор событий
    #     for event in lead.get('events') or []:
    #         actions.append({
    #             'date': self.time_shift_function(unix_ts=event['created_at']),
    #             'entity': 'event',
    #             'type': event['type'],
    #             'user': (users_dict.get(event.get('created_by')) or {}).get('name'),
    #             'params': event.get('params') or {}
    #         })
    #     return actions
    #
    # def __calculate_user_activity(self, actions: List):
    #     {
    #         'date': self.time_shift_function(unix_ts=note['created_at']),
    #         'entity': 'note',
    #         'type': note['note_type'],
    #         'user': (users_dict.get(note.get('created_by')) or {}).get('name'),
    #         'params': note.get('params') or {}
    #     }

    def __calculate_communication_process(self, reaction: Dict) -> Dict:
        """ Вычисляет процесс коммуникации: сколько было звонков, сообщений и проч.?

        Args:
            reaction: см. build_reaction_data

        Returns:
            ...
        """
        result = {
            f'{self.Field.IncomingCall.value}_attempt': 0,
            f'{self.Field.IncomingCall.value}_duration': 0,
            f'{self.Field.OutgoingCall.value}_attempt': 0,
            f'{self.Field.OutgoingCall.value}_quantity': 0,
            f'{self.Field.OutgoingCall.value}_duration': 0,
            f'{self.Field.IncomingChat.value}_quantity': 0,
            f'{self.Field.OutgoingChat.value}_quantity': 0,
            f'{self.Field.IncomingEmail.value}_quantity': 0,
            f'{self.Field.OutgoingEmail.value}_quantity': 0,
        }
        # сколько было значимых (2 мин - 2.5 часа) успешных входящих звонков?
        for call_source in self.CallSource:
            for call in reaction[f'{self.Field.IncomingCall.value}__{call_source.value}']:
                result[f'{self.Field.IncomingCall.value}_attempt'] += 1
                params = call.get('params')
                if not params:
                    continue
                duration = params.get('duration')
                if duration < 120 or duration > 2.5 * 3600:
                    continue
                result[f'{self.Field.IncomingCall.value}_duration'] += duration
            # сколько было значимых (2 мин - 2.5 часа) успешных исходящих звонков?
            for call in reaction[f'{self.Field.OutgoingCall.value}__{call_source.value}']:
                result[f'{self.Field.OutgoingCall.value}_attempt'] += 1
                params = call.get('params')
                if not params:
                    continue
                duration = params.get('duration')
                if duration < 120 or duration > 2.5 * 3600:
                    continue
                result[f'{self.Field.OutgoingCall.value}_quantity'] += 1
                result[f'{self.Field.OutgoingCall.value}_duration'] += duration
        # сколько было писем и чатов
        for key in (
            self.Field.IncomingChat.value,
            self.Field.OutgoingChat.value,
            self.Field.IncomingEmail.value,
            self.Field.OutgoingEmail.value
        ):
            result[f'{key}_quantity'] = len(reaction[key])
        # убираем нули
        for key, value in result.items():
            if value > 0:
                continue
            result[key] = ''
        return result

    def __calculate_first_reaction_time(self, reaction: Dict) -> Dict:
        """ Считает время реакции по каждому типу взаимодействия (звонки, сообщения и проч.)

        Args:
            reaction: см. build_reaction_data

        Returns:
            Словарь с типами взаимодействия и скорейшей скоростью реакции по ним
        """
        # todo можно считать с даты переназначения, но как быть с множественными переназначениями?
        start_dt = reaction[self.Field.CreatedAt.value]
        # строим словарь с видами и скоростью реакций
        reaction_types = (
            # self.Field.IncomingCall.value,
            self.Field.OutgoingCall.value,
            self.Field.OutgoingEmail.value,
            self.Field.OutgoingChat.value,
            self.Field.UserNote.value,
            self.Field.CompletedTask.value
        )
        reaction_time = {key: None for key in reaction_types}
        reaction_time[self.Field.CreationSource.value] = reaction[self.Field.CreationSource.value]
        fastest_reaction = None
        for key in reaction_types:
            item = reaction.get(key)
            if not item:
                continue
            reaction_speed = int(
                (item[0]['date'] - start_dt).total_seconds()
            )
            reaction_time[key] = reaction_speed
            if not fastest_reaction or reaction_speed < fastest_reaction[0]:
                fastest_reaction = (reaction_speed, key)
        # если нашли самую быструю из всех осуществленных реакций - запишем ее
        if fastest_reaction:
            reaction_time[self.Field.FastestReaction.value] = fastest_reaction[1]
        # дописываем "косвенные реакции" в виде смены статусов
        statuses = (self.Field.TryingToGetInTouch.value, self.Field.Closed.value)
        fastest_secondary_reaction = None
        for key in statuses:
            item = reaction.get(key)
            if not item:
                continue
            reaction_speed = int(
                (item[0]['date'] - start_dt).total_seconds()
            )
            reaction_time[key] = reaction_speed
            if not fastest_secondary_reaction or reaction_speed < fastest_secondary_reaction[0]:
                fastest_secondary_reaction = (reaction_speed, key)
        # косвенной реакцией также может быть выполнение задачи, связанной с лидом
        fastest_completed_task_reaction = None
        completed_tasks = reaction.get(self.Field.CompletedTask.value)
        if not fastest_reaction and completed_tasks:
            reaction_speed = int(
                (completed_tasks[0]['date'] - start_dt).total_seconds()
            )
            fastest_completed_task_reaction = (reaction_speed, self.Field.CompletedTask.value)
        # если прямой быстрой реакции не было, учтем "косвенную" реакцию
        if not fastest_reaction and fastest_secondary_reaction:
            reaction_time[self.Field.FastestReaction.value] = fastest_secondary_reaction[1]
            fastest_reaction = fastest_secondary_reaction[1]
        # реакция в виде выполненной задачи по лиду
        if not fastest_reaction and fastest_completed_task_reaction:
            reaction_time[self.Field.FastestReaction.value] = fastest_completed_task_reaction[1]
        # сравним скорости "косвенной" реакции и реакции в виде выполнения задачи по лиду
        if fastest_secondary_reaction and fastest_completed_task_reaction:
            if fastest_secondary_reaction[0] < fastest_completed_task_reaction[0]:
                reaction_time[self.Field.FastestReaction.value] = fastest_secondary_reaction[1]
            else:
                reaction_time[self.Field.FastestReaction.value] = fastest_completed_task_reaction[1]
                reaction_time[self.Field.CompletedTask.value] = fastest_completed_task_reaction[0]
        # находим время, прошедшее от даты создания лида до первого состоявшегося входящего звонка
        first_incoming_call_speed = -1
        flag = False
        for call_type in self.CallSource:
            for incoming_call in reaction[f'{self.Field.IncomingCall.value}__{call_type.value}'] or []:
                duration = incoming_call['params'].get('duration') or 0
                if duration == '':
                    duration = 0
                if isinstance(duration, str):
                    if duration.isnumeric():
                        duration = int(duration)
                    else:
                        # print('duration', duration)
                        continue
                if duration > 0:
                    first_incoming_call_speed = int(
                        (incoming_call['date'] - start_dt).total_seconds()
                    )
                    flag = True
                    break
            if flag:
                break
        fastest_reaction = reaction_time.get(self.Field.FastestReaction.value)
        fastest_time = reaction_time.get(fastest_reaction) or 0
        # print(first_incoming_call_speed, fastest_time)
        if -1 < first_incoming_call_speed < fastest_time:
            # print('!!!')
            # если был успешный входящий звонок раньше первой реакции - не ожидаем реакцию
            reaction_time[self.Field.FirstSuccessfulIncomingCall.value] = 1
        else:
            reaction_time[self.Field.FirstSuccessfulIncomingCall.value] = ''
        # проверка on_duty
        reaction_time[self.Field.OnDuty.value] = False
        if self.schedule:
            duty_time = self.schedule.get(start_dt.weekday())
            reaction_time[self.Field.OnDuty.value] = duty_time[0] < start_dt.time() < duty_time[1]
        return reaction_time

    def __mixin_reaction_to_lead(self, lead: Dict, reaction_time: Dict):
        """ Подмешивает к сделке данные о скорости реакции менеджеров

        Args:
            lead: сделка
            reaction_time: данные о скорости реакции
        """
        fastest_reaction = reaction_time.get(self.Field.FastestReaction.value)
        fastest_time = reaction_time.get(fastest_reaction)
        fastest_call = reaction_time.get(self.Field.OutgoingCall.value)
        lead[Lead.CreationSource.Key] = reaction_time.get(self.Field.CreationSource.value)
        # print(lead['id'], fastest_reaction, reaction_time[self.Field.OnDuty.value], )
        # способ самой быстрой реакции
        lead[Lead.ReactionType.Key] = fastest_reaction
        lead[Lead.FirstSuccessfulIncomingCall.Key] = reaction_time[self.Field.FirstSuccessfulIncomingCall.value]
        # время самой быстрой реакции
        if reaction_time[self.Field.OnDuty.value]:
            lead[Lead.OnDuty.Key] = 'duty time'
            lead[Lead.ReactionTimeOnDuty.Key] = fastest_time or ''
            # любая реакция
            key_reaction_missed = Lead.ReactionTimeOnDutyMissed.Key
            key_reaction_less_300 = Lead.ReactionTimeOnDutyLess300.Key
            key_reaction_greater_300 = Lead.ReactionTimeOnDutyGreater300.Key
            # звонки
            key_call_missed = Lead.CallbackTimeOnDutyMissed.Key
            key_call_less_300 = Lead.CallbackTimeOnDutyLess300.Key
            key_call_greater_300 = Lead.CallbackTimeOnDutyGreater300.Key
        else:
            lead[Lead.OnDuty.Key] = 'off time'
            lead[Lead.ReactionTimeOffDuty.Key] = fastest_time or ''
            # любая реакция
            key_reaction_missed = Lead.ReactionTimeOffDutyMissed.Key
            key_reaction_less_300 = Lead.ReactionTimeOffDutyLess300.Key
            key_reaction_greater_300 = Lead.ReactionTimeOffDutyGreater300.Key
            # звонки
            key_call_missed = Lead.CallbackTimeOffDutyMissed.Key
            key_call_less_300 = Lead.CallbackTimeOffDutyLess300.Key
            key_call_greater_300 = Lead.CallbackTimeOffDutyGreater300.Key
        # все типы реакций
        if fastest_time is None:
            lead[key_reaction_missed] = 1
            lead[Lead.ReactionTimeMissed.Key] = 1
        elif fastest_time <= 300:
            lead[key_reaction_less_300] = 1
            lead[Lead.ReactionTimeLess300.Key] = 1
        else:
            lead[key_reaction_greater_300] = 1
            lead[Lead.ReactionTimeGreater300.Key] = 1
        # только звонки
        if not fastest_call:
            lead[key_call_missed] = 1
            lead[Lead.CallbackTimeMissed.Key] = 1
        elif fastest_call <= 300:
            lead[key_call_less_300] = 1
            lead[Lead.CallbackTimeLess300.Key] = 1
        else:
            lead[key_call_greater_300] = 1
            lead[Lead.CallbackTimeGreater300.Key] = 1
