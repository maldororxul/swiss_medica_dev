""" Постобработчик данных, полученных из AMO """
__author__ = 'ke.mizonov'

import time

from memory_profiler import profile     # pip install memory-profiler
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Union, Type, Optional, Tuple, Callable, Any
from amo.api.constants import AmoEvent, AmoNote
from amo.data.base.countries import CONTRY_REPLACEMENTS
from amo.data.base.data_schema import Lead, LeadField, CLUSTER_SUBJECT, StageItem
# from amo.data.base.pivot_schema import PivotLeads, PivotPriorConsent, PivotDateOfSale, PivotTreatment, \
#     PivotGeneral, PivotSuccess, PivotManagers
# from amo.data.base.pivot_schema import PivotClusterTags
from amo.data.base.pivot_schema import PivotCrew
from amo.data.base.communication import CommunicationBase
from amo.data.base.utm_controller import build_final_utm
from constants.constants import CLOSE_REASON_FAILED, CLOSE_REASON_SUCCESS, GoogleSheets
from constants.utils import Tools
from google_api.client import GoogleAPIClient
from utils.country_codes import get_country_codes, get_country_by_code
from utils.excel import ExcelClient
from utils.functions import clear_phone, get_current_timeshift
from utils.serializer import PklSerializer
from utils.word import WordClient
from voip.constants import CallType
from voip.processor import VOIPDataProcessor
from worker.worker import Worker

# TDataClient = Union[Type[DrvorobjevClient], Type[SwissmedicaClient]]
_ID = None


class AmoProcessor:
    """ Базовый клиент для работы с данными """
    data_client: Callable = NotImplemented
    leads_file_name: str = NotImplemented
    fields: Dict[str, str] = NotImplemented
    # close_reason: Tuple = NotImplemented
    voip_processor: Optional[VOIPDataProcessor] = None
    # субъекты, участвующие в построении статистических срезов
    subjects = CLUSTER_SUBJECT
    check_by_stages: bool = False
    lead: Lead = Lead       # todo depricated
    lead_models: List[Lead] = [Lead]
    utm_rules_book_id: str = NotImplemented

    @dataclass()
    class Variable:
        """  """

    class Communication(CommunicationBase):
        """ Вычисляет эффективность коммуникации по событиям и примечаниям к сделке,
            в частности считает скорость реакции менеджера
        """

    @property
    def sub_domain(self) -> str:
        """ Поддомен amo """
        return self.data_client.api_client.sub_domain

    @property
    def cluster_file_name(self) -> str:
        return f'cluster_{self.sub_domain}'

    @classmethod
    def build_autodocs(cls):
        """ Обновление автодокументации """
        for model in cls.lead_models:
            if not model.AutodocsSheet:
                continue
            google_client = GoogleAPIClient(
                book_id=GoogleSheets.Autodocs.value,
                sheet_title=model.AutodocsSheet,
                last_col='HL'
            )
            docs = google_client.get_sheet()
            line = model.get_documentation()
            line['Дата'] = str(datetime.now().date())
            keys = list(line.keys())
            # делаем сверку ключей в существующем файле и в новой строке документации
            for key in docs[0].keys():
                if key in keys:
                    continue
                line[key] = ''
            del_row = None
            for num, doc in enumerate(docs):
                if doc['Дата'] == line['Дата']:
                    del_row = num
                for key in keys:
                    if key in doc.keys():
                        continue
                    doc[key] = ''
            docs.pop(del_row)
            docs.append(line)
            # сортировка ключей
            result = []
            for doc in docs:
                if doc['Дата'] == '':
                    continue
                result_line = {k: doc[k] for k in ('Дата', 'Общий комментарий', 'Фильтрация', 'Процедура обновления')}
                result_line.update(sorted(doc.items()))
                result.append(result_line)
            # for x in result:
            #     print(x)
            # print(list(result[0].keys()))
            google_client.write_titles(list(result[0].keys()))
            google_client.write_data_to_sheet(data=result, rewrite=True)

    def build_tags_report(
        self,
        date_from: datetime,
        date_to: datetime,
        file_name: str,
        worker: Optional[Worker] = None,
    ):
        """ Делает выгрузку данных по тегам

        Args:
            date_from: дата с
            date_to: дата по
            file_name: имя файла
            worker: экземпляр воркера
        """
        # # сохраняем данные, на основе которых будем строить сводный отчет
        self.build_cluster_data(
            selected_variable=f'{self.lead.Stage.Target.DisplayName} -> {self.lead.Stage.PriorConsent.DisplayName}',
            selected_subjects=[self.lead.Tags],
            date_from=date_from,
            date_to=date_to,
            worker=worker,
            need_result_by_months=False
        )
        time.sleep(4)       # жуткий костыль (файл с данными не успевает сохраниться, а мы его уже открываем)
        data = ExcelClient.Data(
            outer_file=self.cluster_file_name,
            pivot=self._pivot_tags_builders()
        )
        ExcelClient(
            file_name=file_name
        ).write_pivot(data=data, worker=worker)

    @staticmethod
    def _pivot_tags_builders() -> List:
        """ "Строители" сводных таблиц (теги) """
        return []

    def _clear_country(self, line: Dict):
        country = line[self.lead.Country.Key]
        if '.' in country or ':' in country or country.lower() in ('-', 'yeah', 'yes', 'yes!', 'alqouz1', 'false'):
            line[self.lead.Country.Key] = ''
            return
        if country.isnumeric():
            return
        if CONTRY_REPLACEMENTS.get(country):
            country = CONTRY_REPLACEMENTS[country]
        line[self.lead.Country.Key] = country

    def get_deleted_leads(self, worker: Optional[Worker] = None):
        deleted_leads = self.data_client().get_deleted_leads(worker=worker)
        # for lead in deleted_leads:
        #     for k, v in lead['deleted'].items():
        #         print(k, '::', v)
        #     print()

    def leads_to_excel(
        self,
        date_from: datetime,
        date_to: datetime,
        build_pivot: bool = True,
        update_excel_data: bool = True,
        schedule: Optional[Dict] = None,
        worker: Optional[Worker] = None
    ):
        """ Сохраняет выгрузку лидов в Excel

        Args:
            date_from: дата с
            date_to: дата по
            build_pivot: True - строить сводные
            update_excel_data: True - обновлять экселевский файл с данными
            schedule: расписание работы
            worker: экземпляр воркера

        Notes:
            данный метод переопределяется, логика построения отчетов для SM и CDV расходится
        """
        # сохраняем файл с данными отдельно
        if update_excel_data:
            self._save_pivot_data_file(date_from=date_from, date_to=date_to, schedule=schedule, worker=worker)
        # бывает так, что сводные строить не нужно
        if not build_pivot:
            return
        data = ExcelClient.Data(
            outer_file=self.leads_file_name,
            pivot=self._pivot_builders()
        )
        ExcelClient(
            file_name=f'{self.leads_file_name}_pivot'
        ).write_pivot(data=data, worker=worker)

    @profile
    def build_cluster_data(
        self,
        selected_variable: str,
        selected_subjects: List,
        date_from: datetime,
        date_to: datetime,
        worker: Optional[Worker] = None
    ):
        """ Делает выгрузку данных, относящихся к выбранным субъектам, в Excel

        Args:
            selected_variable: параметр, подпадающий под анализ
            selected_subjects: выбранные субъекты
            date_from: дата с
            date_to: дата по
            worker: экземпляр воркера
        """
        raise NotImplementedError

    def __process_combination(self, combined_dict: Dict, combination: Tuple, line: Dict, curr_month: datetime.date):
        title = ' && '.join(combination)
        curr = (title, curr_month)
        if curr not in combined_dict:
            combined_dict[curr] = {
                self.lead.Stage.Lead.Key: 0,
                f'{self.lead.Stage.Lead.Key}{" -> "}{self.lead.Stage.Target.Key}': 0,
                self.lead.Stage.Target.Key: 0,
                self.Variable.TargetToPriorConsent: 0,
                self.lead.Stage.PriorConsent.Key: 0,
                f'{self.lead.Stage.Target.Key}{" -> "}{self.lead.Stage.WaitingAtClinic.Key}': 0,
                self.lead.Stage.WaitingAtClinic.Key: 0,
                f'{self.lead.Stage.Target.Key}_share': 0,
                f'{self.lead.Stage.WaitingAtClinic.Key}_share': 0
            }
        combined_dict[curr][self.lead.Stage.Lead.Key] += line[self.lead.Stage.Lead.Key] or 0
        combined_dict[curr][self.lead.Stage.Target.Key] += line[self.lead.Stage.Target.Key] or 0
        combined_dict[curr][self.lead.Stage.PriorConsent.Key] += line[self.lead.Stage.PriorConsent.Key] or 0
        combined_dict[curr][self.lead.Stage.WaitingAtClinic.Key] += line[self.lead.Stage.WaitingAtClinic.Key] or 0

    def _get_leads(
            self,
            date_from: datetime,
            date_to: datetime,
            worker: Optional[Worker] = None,
            mixin_notes: bool = True
    ) -> List[Dict]:
        """ Получить список сделок

        Args:
            date_from: дата с
            date_to: дата по
            worker: экземпляр воркера
            mixin_notes: подмешивать примечания

        Returns:
            список сделок за период
        """
        # лиды тащим по дате создания (!)
        leads = self.data_client().get_leads(
            date_from=date_from,
            date_to=date_to,
            date_key='created_at',
            worker=worker,
            mixin_notes=mixin_notes
        ) or []
        if worker:
            worker.emit({'msg': 'Building leads data...'})
        return leads

    def _build_cluster_data(
        self,
        selected_subjects: List,
        date_from: datetime,
        date_to: datetime,
        worker: Optional[Worker] = None
    ) -> List[Dict]:
        """ Получить обработанный список сделок

        Args:
            selected_subjects: выбранные субъекты
            date_from: дата с
            date_to: дата по
            worker: экземпляр воркера

        Returns:
            обработанный список сделок за период
        """
        raise NotImplementedError

    def _save_pivot_data_file(
        self,
        date_from: datetime,
        date_to: datetime,
        schedule: Optional[Dict] = None,
        worker: Optional[Worker] = None
    ):
        """ Сохраняет данные для выгрузки лидов в Excel. На основе этих данных будет построен пивот.

        Args:
            date_from: дата с
            date_to: дата по
            schedule: расписание работы
            worker: экземпляр воркера
        """
        full_data = self._build_leads_data(
                    worker=worker,
                    date_from=date_from,
                    date_to=date_to,
                    schedule=schedule,
                    weekly=True
                )
        ExcelClient(file_name=self.leads_file_name).write(data=[ExcelClient.Data(data=full_data)])
        # дополнительно - готовим данные для Сергея
        limited_data = []
        limited_keys = (
            'created_at',
            'id',
            'final_base_url',
            'country',
            'stage_07_qualification',
            'final_utm_source',
            'final_utm_medium',
            'final_utm_campaign',
            'final_utm_content',
            'final_utm_creative',
            'final_utm_term',
            'final_utm_channel',
            'reached_stage',
            'price',
            'final_rule_num'
        )
        for lead in full_data:
            keys_to_delete = []
            for key in lead:
                if key not in limited_keys:
                    keys_to_delete.append(key)
            for key in keys_to_delete:
                lead.pop(key)
            limited_data.append(lead)
        ExcelClient(file_name=f'{self.leads_file_name}_limited').write(data=[ExcelClient.Data(data=limited_data)])

    def _get_lead_url_by_id(self, lead_id: int) -> str:
        """ Получение ссылки на сделку по идентификатору """
        return self.data_client.get_lead_url_by_id(lead_id=lead_id)

    def _get_longest_call_duration(self, lead: Dict, calls: Dict) -> Union[int, str]:
        """ Проверка по телефонии, был ли с этим лидом длительный разговор """
        if not calls:
            return ''
        longest = 0
        for phone in self.get_lead_contacts(lead):
            history = calls.get(phone)
            if not history:
                continue
            for event in history:
                if event['status'] == 'answered' and event['duration'] > longest:        # fixme хардкод
                    longest = event['duration']
        return longest

    def _get_outgoing_call_time(self, lead: Dict, calls: Dict) -> Optional[datetime]:
        """ Проверка по телефонии - время исходящего звонка """
        if not calls:
            return None
        for phone in self.get_lead_contacts(lead):
            history = calls.get(phone)
            if not history:
                continue
            for event in history:
                if event['type'] == CallType.Outcome.value:
                    if event['source'] == 'mobile':
                        event['date'] += timedelta(hours=get_current_timeshift())
                    # if '447852525119' in str(phone):
                    #     print('>>', event)
                    return event['date']
        return None

    def _get_dobrica_call(self, lead: Dict, calls: Dict) -> Union[int, str]:
        """ Проверка по телефонии, был ли с этим лидом длительный разговор у Добрицы """
        if not calls:
            return ''
        longest = 0
        for phone in self.get_lead_contacts(lead):
            history = calls.get(phone)
            if not history:
                continue
            for event in history:
                if str(event['manager']) == '38163247777' and event['status'] == 'answered' and event['duration'] > longest:
                    longest = event['duration']
        return longest

    def _convert_date_time_from_unix_timestamp(self, unix_ts: int) -> datetime:
        """ Переводит время из unix-формата в datetime с учетом текущих настроек часового пояса

        Args:
            unix_ts: значение времени в unix-формате

        Returns:
            дату-время с учетом текущих настроек часового пояса
        """
        return datetime.fromtimestamp(unix_ts, timezone(+timedelta(hours=self.data_client().time_shift)))

    @staticmethod
    def get_lead_contacts(lead: Dict, field_code: str = 'PHONE') -> List[str]:
        """ Получить список телефонов / email из контактов лида """
        result = []
        for contact in lead.get('contacts') or []:
            for contact_field in contact.get('custom_fields_values') or []:
                if contact_field['field_code'] != field_code:
                    continue
                for phone in contact_field['values']:
                    result.append(clear_phone(phone['value']))
        return result

    @staticmethod
    def _get_input_field_value(lead: Dict) -> Optional[str]:
        """ Получить значение поля INPUT """
        for _field in lead.get('custom_fields_values') or []:
            if _field['field_code'] != 'INPUT':
                continue
            # print(_field['values'][0]['value'])
            return _field['values'][0]['value']
        return None

    @staticmethod
    def _get_cf_values(field: Dict) -> Any:
        """ Конкатенирует значения доп. поля, либо возвращает единственное значение """
        values = field.get('values') or []
        if len(values) == 1:
            return values[0]['value']
        return ', '.join([str(value['value']) for value in values])

    def _build_lead_history(
        self,
        lead_model: Type[Lead],
        lead: Dict,
        line: Dict,
        pipelines_dict: Dict,
        stages_priority
    ):
        """ Строит историю прохождения сделки по этапам

        Args:
            lead_model: модель лида
            lead: сырые данные лида из Amo
            line: строка данных лида для отчета
            pipelines_dict: справочник этапов и статусов Amo
            stages_priority: ...
        """
        if not lead.get('events'):

            # fixme tmp
            if lead['id'] == _ID:
                print('no events!!!')

            return
        statuses = []
        statuses_after = []
        for event in lead['events']:
            _type = event['type']

            # fixme tmp
            if lead['id'] == _ID:
                print('>>>', _type, event)

            if _type != AmoEvent.StageChanged.value:
                continue
            # событие изменения статуса, следовательно, данные должны быть заполнены всегда
            value_before = event['value_before'][0]['lead_status']
            value_after = event['value_after'][0]['lead_status']
            pipeline_before_id = value_before.get('pipeline_id')
            pipeline_after_id = value_after.get('pipeline_id')
            # если отличаются идентификаторы воронок, значит был перенос лидов между воронками - пропустим
            # fixme нельзя пропускать такие кейсы из-за Италии?
            # if pipeline_id != value_after.get('pipeline_id'):
            #     continue
            # выделяем из справочника воронок и статусов нужную (это странно, но ее может не быть)
            pipeline_before: Dict = pipelines_dict.get(pipeline_before_id)
            pipeline_after: Dict = pipelines_dict.get(pipeline_after_id)
            if not pipeline_before or not pipeline_after:
                # fixme рейзить ошибку?
                continue
            # добавляем все пройденные этапы в общий список
            before = pipeline_before.get('status').get(value_before['id'])
            after = pipeline_after.get('status').get(value_after['id'])
            statuses_after.append({'status': after, 'date': event['created_at']})

            # fixme пригодится для отладки
            # if before is None:
            #     print('~~~', before, value_before, pipeline_before)
            #     print('---', pipelines_dict)
            #     print('lead_id', lead['id'])
            #     print(event)
            #     exit()
            # if after is None:
            #     print('~~~', after, value_after, pipeline_after)
            #     print('---', pipelines_dict)

            for status, time_value in statuses:
                if status == before:
                    break
            else:
                statuses.append((before, ''))
            for status, time_value in statuses:
                if status == after:
                    break
            else:
                statuses.append((after, event['created_at']))

        if _ID and line['id'] == _ID:
            print('statuses:')
            for s in statuses:
                print(s)
            print(lead_model.Stage.get_reached_stages(values=statuses))

        # 'Successfully realized', 'Успешно реализовано'
        statuses_after = sorted(statuses_after, key=lambda x: x['date'])
        close_time = None
        reanimation_time = None
        success_time = None
        for stage in statuses_after:

            if lead['id'] == _ID:
                print(stage)

            if close_time is None and stage['status'] in CLOSE_REASON_FAILED:
                close_time = stage['date']
                if lead['id'] == _ID:
                    print('closed')
                continue
            if close_time is not None and reanimation_time is None:
                reanimation_time = stage['date']
                if lead['id'] == _ID:
                    print('reanimated')
            if reanimation_time is not None and stage['status'] in CLOSE_REASON_SUCCESS:
                success_time = stage['date']
                # if lead['id'] == 21303679:
                #     print('success')
                break

        if success_time:
            line[lead_model.DateUnrealized.Key] = close_time
            line[lead_model.DateReanimated.Key] = reanimation_time
            line[lead_model.DateRealizedAfterReanimation.Key] = success_time

        # print('>>', statuses_after)
        # проверка достигнутых стадий
        if self.check_by_stages:
            for status in statuses_after:
                stage = self.__get_stage_if_reached(stages_priority=stages_priority, status=status['status'])
                if not stage:
                    continue
                stage_time = status['date']
                line[stage.Key] = 1
                line[stage.Date] = self._convert_date_time_from_unix_timestamp(stage_time).date() if stage_time else ''
        # for stage, stage_time in self.lead.Stage.get_reached_stages(values=statuses) or []:
        #     # костыль на длительные переговоры - это атомарная стадия, не зависящая от других
        #     if 'long_negotiations' in stage.Key:
        #         continue
        #     # if _ID and line['id'] == _ID:
        #     #     print('>>>', stage.Key)
        #     # KeyByStage - факт прохождения воронки
        #     line[stage.KeyByStage] = 1
        #     line[stage.Date] = self._convert_date_time_from_unix_timestamp(stage_time).date() if stage_time else ''

    @staticmethod
    def __get_stage_if_reached(stages_priority, status):
        """ Достигнута ли стадия? """
        for stage in stages_priority:
            if status in stage.IncludeStages:
                return stage
        return None

    @staticmethod
    def _check_stages_priority(line: Dict, stages_priority: Tuple, exclude: Tuple = ('long_negotiations', )):       # fixme
        """ Дозаполнение предыдущих этапов воронки, если заполнены последующие """
        for i in range(len(stages_priority) - 1, -1, -1):
            stage = stages_priority[i]
            if stage.Key in exclude:
                continue
            if line[stage.Key] == 1:
                if line['id'] == _ID:
                    print('lead has reached', stage.Key)
                for j in range(i - 1, -1, -1):
                    past_stage = stages_priority[j]
                    # костыль на long_negotiations
                    if past_stage.Key in exclude:
                        continue
                    if line['id'] == _ID:
                        print('_check_stages_priority >>', past_stage.Key)
                    line[past_stage.Key] = 1
            if line['id'] == _ID:
                print()

    # def _calculate_first_touch_time(self, lead: Dict, line: Dict, schedule: Optional[Dict] = None):
    #     """ По событиям сделки вычисляет время первого контакта
    #
    #     Args:
    #         lead: сырые данные лида из Amo
    #         line: строка данных лида для отчета
    #         schedule: расписание работы
    #     """
    #     if not lead['events']:
    #         # if lead['id'] == 22749023:
    #         #     print(5467567)
    #         return
    #     added_time = None
    #     earliest_income_time, earliest_outcome_time = None, None
    #
    #     for event in lead['events']:
    #         _type = event['type']
    #
    #         # # fixme tmp
    #         # if _type == AmoEvent.StageChanged.value:
    #         #     continue
    #         # if lead['id'] == 22770121:
    #         #     print(_type, event['created_at'])
    #
    #         # # смерженные лиды пропускаем
    #         # if _type == AmoEvent.Merged.value:
    #         #     line[self.lead.ReactionTime.Key] = 0
    #         #     return
    #         # deprecated
    #         if _type == AmoEvent.Added.value:
    #             added_time = event['created_at']
    #             continue
    #         # нас интересуют только исходящие звонки и сообщения
    #         if _type in (AmoEvent.StageChanged.value, AmoEvent.Merged.value):
    #             continue
    #         # определяем самое раннее по времени событие (исходящий чат или звонок)
    #         if _type in (AmoEvent.OutcomeChat.value, AmoEvent.OutcomeCall.value):
    #             if not earliest_outcome_time or earliest_outcome_time > event['created_at']:
    #                 earliest_outcome_time = event['created_at']
    #         # определяем самое раннее по времени событие (входящий чат или звонок)
    #         if _type in (AmoEvent.IncomeChat.value, AmoEvent.IncomeCall.value):
    #             if not earliest_income_time or earliest_income_time > event['created_at']:
    #                 earliest_income_time = event['created_at']
    #
    #     # if lead['id'] == 22723863:
    #     #     print(earliest_income_time, earliest_outcome_time)
    #
    #     if not earliest_income_time and not earliest_outcome_time:
    #         line[self.lead.NoInteraction.Key] = 1
    #     elif (not earliest_income_time and earliest_outcome_time) \
    #             or (earliest_income_time and earliest_outcome_time and earliest_income_time > earliest_outcome_time):
    #         line[self.lead.Outgoing.Key] = 1
    #         added_time = lead['created_at']
    #         if added_time > earliest_outcome_time:
    #             line[self.lead.ReactionTime.Key] = ''
    #             return
    #         line[self.lead.ReactionTime.Key] = earliest_outcome_time - added_time
    #         if 0 < line[self.lead.ReactionTime.Key] <= 60 * 60:
    #             line[self.lead.FastOutgoingReaction.Key] = 1
    #         else:
    #             line[self.lead.SlowOutgoingReaction.Key] = 1
    #     elif earliest_income_time and schedule:
    #         time_shift = timedelta(hours=get_current_timeshift() - self.data_client.time_shift)
    #         curr_date = self._convert_date_time_from_unix_timestamp(earliest_income_time) + time_shift
    #         duty_time = schedule.get(curr_date.weekday())
    #         is_duty_time = duty_time[0] < curr_date.time() < duty_time[1]
    #         line[self.lead.Incoming.Key] = 1
    #         line[self.lead.IncomingOnDuty.Key] = 1 if is_duty_time else ''
    #         if not earliest_outcome_time:
    #             line[self.lead.ReactionTime.Key] = ''
    #             line[self.lead.NoReaction.Key] = 1
    #             line[self.lead.NoReactionOnDuty.Key] = 1 if is_duty_time else ''
    #         elif earliest_income_time < earliest_outcome_time:
    #             line[self.lead.ReactionTime.Key] = earliest_outcome_time - earliest_income_time
    #         return
    #     # поскольку added_time из событий порой дает неадекватный результат, явно пропишем значение из created_at
    #     #   было: added_time = added_time or lead['created_at']
    #     # added_time = lead['created_at']
    #     # line[self.lead.ReactionTime.Key] = earliest_outcome_time - added_time if earliest_outcome_time else ''

    @staticmethod
    def _pivot_builders() -> List:
        """ "Строители" сводных таблиц """
        return []

    @staticmethod
    def _sort_dict(_dict: Dict, id_first: bool = True) -> Dict:
        """ Сортировка ключей словаря (id останется на первом месте) """
        if not id_first:
            return dict(sorted(_dict.items()))
        keys = list(_dict.keys())
        keys.remove('id')
        keys = ['id'] + sorted(keys)
        return dict([(f, _dict.get(f)) for f in keys])

    def _pre_build(self, date_from: datetime, date_to: datetime) -> Dict:
        """ Предзагрузка словарей, необходимых для построения данных по лидам

        Args:
            date_from: дата с
            date_to: дата по

        Returns:
            словари, необходимые для построения данных по лидам
        """
        calls = {}
        if self.voip_processor:
            calls = self.voip_processor.build_customer_calls_map(date_from=date_from, date_to=date_to)
        return {
            # данные о воронках и этапах
            'pipelines_dict': PklSerializer(file_name=f'{self.sub_domain}_pipelines').load(),
            # # логика прохождения лида по воронке
            # 'stages_priority': self.lead.get_stages_priority(),
            # схема дополнительных полей
            'lead_custom_fields': {field.CustomField: field.Key for field in self.lead.get_custom_fields()},
            # поля, содержащие даты
            'date_fields': [field.Key for field in self.lead.get_date_fields()],
            # данные по звонкам
            'calls': calls,
            'utm_rules': GoogleAPIClient(book_id=self.utm_rules_book_id, sheet_title='rules').get_sheet()
        }

    @staticmethod
    def _is_lead(loss_reason: str) -> bool:
        """ Возвращает кортеж причин закрытия, которые не соответствуют лидам """
        raise NotImplementedError

    def _build_stages_fields(self, line: Dict):
        for lead_model in self.lead_models:
            stages_priority = lead_model.get_stages_priority()
            # отдельно добавляем поля, относящиеся к этапам сделки
            line.update({stage.Key: '' for stage in stages_priority})
            # fixme пока не используем, но может понадобится
            # line.update({stage.KeyByStage: '' for stage in stages_priority})
            # line.update({stage.Date: '' for stage in stages_priority})
            line.update({stage.Price: '' for stage in stages_priority})
            # line.update({stage.Alive: '' for stage in stages_priority})

    def _check_alive_stages(self, line: Dict):
        status_name = (line.get(self.lead.StatusName.Key) or '').lower()
        line[self.lead.AtWorkAnyPipeline.Key] = ''
        for lead_model in self.lead_models:
            line[lead_model.AllAlive.Key] = 0
            line[lead_model.AtWork.Key] = 0
            for stage in lead_model.get_stages_priority():
                line[stage.Alive] = 1 if status_name in map(lambda x: x.lower(), stage.IncludeStages) else ''
                # # фиксируем последнюю достигнутую стадию воронки
                # line[self.lead.ReachedStage.Key] = stage.DisplayName
                if line[stage.Alive] == 1:
                    line[lead_model.AllAlive.Key] += 1
                    if stage.AtWork:
                        # if line['id'] == 22978323:
                        #     print('!!!')
                        line[lead_model.AtWork.Key] += 1
                        line[self.lead.AtWorkAnyPipeline.Key] = 1
                # if line['id'] == 22978323:
                #     print(stage.Key, '>>', line[stage.Alive])
            if line[lead_model.AllAlive.Key] == 0:
                line[lead_model.AllAlive.Key] = ''
            if line[lead_model.AtWork.Key] == 0:
                line[lead_model.AtWork.Key] = ''
            # if line['id'] == 22978323:
            #     print('~~', line[lead_model.AtWork.Key])

    # def _process_first_reaction_time(self, line: Dict, lead: Dict, schedule: Optional[Dict] = None):
    #     # if lead['id'] == 22749023:
    #     #     print(5467567)
    #     if not line[self.lead.Stage.Lead.Key]:
    #         return
    #     # считаем время реакции (первого контакта)
    #     self._calculate_first_touch_time(lead=lead, line=line, schedule=schedule)
    #     if line[self.lead.Incoming.Key] and line[self.lead.ReactionTime.Key]:
    #         # if line[self.lead.ReactionTime.Key] == 0:
    #         #     line[self.lead.ImmidiateReaction.Key] = 1
    #         # elif line[self.lead.ReactionTime.Key]:
    #         if 0 < line[self.lead.ReactionTime.Key] <= 5 * 60:
    #             line[self.lead.FastReaction.Key] = 1
    #             if line[self.lead.IncomingOnDuty.Key] == 1:
    #                 line[self.lead.FastReactionOnDuty.Key] = 1
    #         else:
    #             line[self.lead.SlowReaction.Key] = 1
    #             if line[self.lead.IncomingOnDuty.Key] == 1:
    #                 line[self.lead.SlowReactionOnDuty.Key] = 1
    #
    #     if line[self.lead.Outgoing.Key] == 1 and \
    #             (not line[self.lead.SlowOutgoingReaction.Key] or not line[self.lead.FastOutgoingReaction.Key]):
    #         line[self.lead.OutgoingProblem.Key] = 1
    #
    #     if line[self.lead.Outgoing.Key] == 1 and line[self.lead.FirstOutgoingCallDateTime.Key]:
    #         diff = line[self.lead.FirstOutgoingCallDateTime.Key].timestamp() - line[self.lead.CreatedAt.Key]
    #         line[self.lead.FirstOutgoingCallReactionTime.Key] = int(diff / 60) - self.data_client.time_shift * 60
    #         self._get_outgoing_voip_reaction(
    #             line=line,
    #             key_fast=self.lead.FastOutgoingReactionVOIP2.Key,
    #             key_slow=self.lead.SlowOutgoingReactionVOIP2.Key,
    #             minutes=2
    #         )
    #         self._get_outgoing_voip_reaction(
    #             line=line,
    #             key_fast=self.lead.FastOutgoingReactionVOIP5.Key,
    #             key_slow=self.lead.SlowOutgoingReactionVOIP5.Key,
    #             minutes=5
    #         )
    #         self._get_outgoing_voip_reaction(
    #             line=line,
    #             key_fast=self.lead.FastOutgoingReactionVOIP60.Key,
    #             key_slow=self.lead.SlowOutgoingReactionVOIP60.Key,
    #             minutes=60
    #         )
    #
    #     if line[self.lead.Outgoing.Key] == 1 and \
    #             (not line[self.lead.SlowOutgoingReactionVOIP60.Key] or not line[self.lead.FastOutgoingReactionVOIP60.Key]):
    #         line[self.lead.OutgoingProblemVOIP.Key] = 1

    # def _get_outgoing_voip_reaction(self, line: Dict, key_fast: str, key_slow: str, minutes: int):
    #     """ Добавляет информацию о скорости реакции на новую заявку (с даты/времени создания) по данным VOIP
    #
    #     Args:
    #         line: данные заявки
    #         key_fast: ключ из схемы данных лида, обозначающий быструю реакцию на исходящий звонок
    #         key_slow: ключ из схемы данных лида, обозначающий медленную реакцию на исходящий звонок
    #         minutes: скорость реакции в минутах
    #     """
    #     diff = line[self.lead.FirstOutgoingCallReactionTime.Key]
    #     if 0 < diff <= minutes:
    #         line[key_fast] = 1
    #     elif diff > minutes:
    #         line[key_slow] = 1

    def _build_lead_base_data(self, lead: Dict, pre_data: Dict) -> Dict:
        # готовим пустой словарь с обязательным списком полей
        line = {field.Key: '' for field in self.lead.get_fields()}
        # добавляем выборочно сырые поля из лида, а также доп. поля (значение по умолчанию - '')
        line.update({field.Key: lead.get(field.Key) for field in self.lead.get_raw_fields()})
        # добавляем поля utm-меток
        line.update({value.Key: '' for value in self.lead.Utm.__dict__.values() if isinstance(value, LeadField)})
        self._build_stages_fields(line=line)
        # добавляем постобработанные utm
        # print(lead['id'])  # 23203305
        line.update(build_final_utm(lead=lead, rules=pre_data['utm_rules']))
        # причина закрытия
        loss_reason = lead['loss_reason'][0]['name'] if lead['loss_reason'] else ''
        # if lead['id'] in (33809887, 33843349):
        #     print(lead['id'], loss_reason, self._is_lead(loss_reason), lead['pipeline_status'])
        # попытка восстановить причину закрытия (удалены 13 октября, восстановлены по данным 5 сентября 2022)
        if not loss_reason and lead['pipeline_status'] in CLOSE_REASON_FAILED:
            restored_loss_reasons = pre_data.get('restore_loss_reasons') or {}
            loss_reason = restored_loss_reasons.get(lead['id']) or ''
        if not loss_reason or loss_reason == '(blank)':
            if lead['pipeline_status'] in CLOSE_REASON_FAILED or lead['pipeline_status'] in CLOSE_REASON_SUCCESS:
                loss_reason = 'closed with no reason'
            else:
                loss_reason = 'active'
        is_lead = 1 if self._is_lead(loss_reason) and not lead.get('deleted') and not lead.get('deleted_leads') else ''
        is_target = 1 if is_lead and (not loss_reason or loss_reason in self.lead.get_loss_reasons()) else ''
        for lead_model in self.lead_models:
            line.update({
                lead_model.Stage.RawLead.Key: 1,
                lead_model.Stage.Lead.Key: is_lead,
                # целевой (нет причины потери лида, либо причины из списка target_loss_reason)
                lead_model.Stage.Target.Key: is_target,
            })
        tags = lead.get('_embedded', {}).get('tags') or []
        is_jivo = ''
        for tag in tags:
            if 'jivo' in tag['name'].lower():
                is_jivo = 1
                break
        line.update({
            self.lead.InputField.Key: self._get_input_field_value(lead) or '',
            self.lead.LossReason.Key: loss_reason,
            self.lead.Link.Key: self._get_lead_url_by_id(lead_id=lead['id']),
            self.lead.Tags.Key: ', '.join([tag['name'] for tag in tags]),
            self.lead.Jivo.Key: is_jivo,
            self.lead.PipelineName.Key: lead['pipeline'],
            self.lead.StatusName.Key: lead['pipeline_status'],
            self.lead.Responsible.Key: lead['user']['name'],
            self.lead.CreatedAtHour.Key: self._convert_date_time_from_unix_timestamp(lead['created_at']).hour,
            # удаленные сделки
            self.lead.Deleted.Key: 1 if lead.get('deleted') else '',
            self.lead.DeletedBy.Key: lead['deleted']['user']['name'] if lead.get('deleted') else ''
        })
        self._check_alive_stages(line=line)
        # временные поля длля подсчета скорости реакции
        #   в том числе, дублируем время создания лида (здесь время не будет очищено)
        line['created_at_ts'] = line['created_at']
        line['notes'] = lead.get('notes')
        line['events'] = lead.get('events')
        line['tasks'] = lead.get('tasks')
        return line

    def _cast_dates(self, line: Dict, pre_data: Dict):
        # кастинг дат
        for key in pre_data.get('date_fields'):
            if line.get(key) is None:
                continue
            value = line[key]
            if isinstance(value, int):
                line[key] = self._convert_date_time_from_unix_timestamp(value).date() if line[key] else ''
            else:
                continue

    def _process_prices(self, line: Dict, lead: Dict):
        for lead_model in self.lead_models:
            stages_priority = lead_model.get_stages_priority()
            price = lead['price'] or 0
            for stage in stages_priority:
                if line.get(stage.Key) is None:
                    continue
                line[stage.Price] = price if line[stage.Key] == 1 and price > 0 else ''
                line[stage.PlannedIncome] = ''
                line[stage.PlannedIncomeFull] = ''
                # планируемый доход (заполняется только для этапов с заданными конверсиями)
                if stage.PurchaseRate > 0 and line.get(stage.Alive) is not None:
                    alive = line[stage.Alive] or 0
                    line[stage.PlannedIncome] = alive * stage.PurchaseRate * price
                    if line[stage.PlannedIncome] == 0:
                        line[stage.PlannedIncome] = ''
                    # else:
                    #     print(stage.Key, line[stage.PlannedIncome])
                    line[stage.PlannedCustomers] = int(alive * stage.PurchaseRate)
                    if line[stage.PlannedCustomers] == 0:
                        line[stage.PlannedCustomers] = ''
                fact = line[stage.Price] if line[stage.Price] != '' else 0
                planned = line[stage.PlannedIncome] if line[stage.PlannedIncome] != '' else 0
                line[stage.PlannedIncomeFull] = fact + planned
                if line[stage.PlannedIncomeFull] == 0:
                    line[stage.PlannedIncomeFull] = ''

    def update_alive_leads(self, schedule: Optional[Dict] = None, worker: Optional[Worker] = None):
        """ Обновить стату по менеджерам (активные лиды, срез по датам) """
        # все имеющиеся на данный момент лиды, загруженные из амо
        file_name = f'alive_{self.data_client.api_client.sub_domain}'
        leads = self._build_leads_data(
            date_from=datetime(2000, 1, 1),
            date_to=datetime.now(),
            worker=worker,
            schedule=schedule,
            mixin_notes=False
        )
        serializer = PklSerializer(file_name=file_name)
        # вычитываем общий список живых лидов
        alive_leads: List = serializer.load() or []
        # удаляем прежние записи за текущую дату
        current_date = datetime.now().date()
        to_delete = [num for num, lead in enumerate(alive_leads) if lead['date'] == current_date]
        for num in to_delete[::-1]:
            alive_leads.pop(num)
        # аккумулируем активные лиды за весь период в словарик по менеджерам и воронкам
        # unique_leads = {}
        for lead in leads:
            if lead['at_work_any_pipeline'] != 1:
                continue
            if not self._is_lead(lead['loss_reason']) or lead.get('deleted_leads'):
                continue
            alive_leads.append({
                'date': current_date,
                'pipeline_name': lead['pipeline_name'],
                'status_name': lead['status_name'],
                'responsible_user_name': lead['responsible_user_name'],
                'at_work_any_pipeline': 1
            })
            # key = lead['responsible_user_name']
            # if key not in unique_leads:
            #     unique_leads[key] = {
            #         'count': 0,
            #         'pipeline_name': lead['pipeline_name'],
            #         'status_name': lead['status_name'],
            #     }
            # unique_leads[key]['count'] += 1
        # # из словарика данные переносим в общий список живых лидов
        # for manager, data in unique_leads.items():
        #     alive_leads.append({
        #         'date': current_date,
        #         'pipeline_name': data['pipeline_name'],
        #         'status_name': data['status_name'],
        #         'responsible_user_name': manager,
        #         'at_work_any_pipeline': data['count']
        #     })
        serializer.save(alive_leads)
        # сохраняем в excel
        # ExcelClient(file_name=file_name).write(data=[
        #     ExcelClient.Data(data=alive_leads)
        # ])
        # сводная таблица
        ExcelClient(file_name=file_name).write_pivot(
            data=ExcelClient.Data(
                data=alive_leads,
                pivot=[PivotCrew.build()]
            )
        )

    def _build_lead_data(self, lead: Dict, pre_data: Dict, schedule: Optional[Dict] = None):
        raise NotImplementedError

    def _weekly_offset(self, weekly: bool, collection: List[Dict]):
        pass

    def _build_leads_data(
        self,
        date_from: datetime,
        date_to: datetime,
        schedule: Optional[Dict] = None,
        worker: Optional[Worker] = None,
        weekly: bool = False,
        mixin_notes: bool = True
    ) -> List[Dict]:
        """ Получить обработанный список сделок

        Args:
            date_from: дата с
            date_to: дата по
            schedule: расписание работы
            worker: экземпляр воркера
            weekly: подгонка дат по неделям
            mixin_notes: подмешивать примечания

        Returns:
            обработанный список сделок за период
        """
        result = []
        leads = self._get_leads(date_from=date_from, date_to=date_to, worker=worker, mixin_notes=mixin_notes)
        total = len(leads)
        pre_data = self._pre_build(date_from=date_from, date_to=date_to)

        # todo добавить фильтрацию! например, фильтрацию лидов по email
        # import csv
        # with open("data/аутизм.csv", "r", encoding='utf-8') as f:
        #     collection = [{k: v for k, v in row.items()} for row in csv.DictReader(f, skipinitialspace=True)]
        # emails = [(item['Email'] or '').lower() for item in collection]

        for num, lead in enumerate(leads, 1):
            if num % 100 == 0 and worker:
                worker.emit({'num': num, 'total': total})

            # if lead['id'] == 22782321:
            #     for k, v in lead.items():
            #         print(k, '::', v)

            # todo добавить фильтрацию! например, фильтрацию лидов по email
            # if not self._filter(lead=lead, emails=emails):
            #     continue

            result.append(self._build_lead_data(lead=lead, pre_data=pre_data, schedule=schedule))
        # created_at_offset: сравнение времени самого раннего события, примечания или задачи с датой создания лида
        self.__fix_created_at(leads=result)
        # подмешиваем время реакции и эффективность коммуникации в целом
        self.Communication(
            sub_domain=self.sub_domain,
            leads=result,
            time_shift_function=self._convert_date_time_from_unix_timestamp,
            trying_to_get_in_touch=('1. TRYING TO GET IN TOUCH',),      # todo хардкод
            closed=CLOSE_REASON_FAILED,
            schedule=schedule
        ).process()
        # todo подмешиваем страны, определенные по номерам телефонов
        self.__process_countries_by_phone_codes(collection=result)
        # смещение по неделям
        self._weekly_offset(weekly=weekly, collection=result)
        return result

    @staticmethod
    def __process_countries_by_phone_codes(collection: List[Dict]):
        print('mixin_country_phone_codes')
        country_codes = get_country_codes()
        for lead in collection:
            if lead.get('country'):
                continue
            phones = lead.get('phone')
            if not phones:
                continue
            phone = phones[0]
            if not phone or len(phone) < 6:
                continue
            lead['country'] = get_country_by_code(country_codes=country_codes, phone=phone) or 'Other'

    # def _calls_duration(self, leads: Dict, duration_from: int = 120):
    #     for lead in leads:
    #         for note in lead.get('notes') or []:
    #             _type = note.get('note_type')
    #             if _type not in (AmoNote.IncomeCall.value, AmoNote.OutcomeCall.value):
    #                 continue
    #             params = note.get('params')
    #             duration = params.get('duration')
    #             if duration < duration_from:
    #                 continue
    #         print()

    @staticmethod
    def __fix_created_at(leads: List[Dict]):
        """ Сравнение времени самого раннего события, примечания или задачи с датой создания лида

        Args:
            leads: список сделок
        """
        # получаем самое раннее событие, примечание или задачу
        for lead in leads:
            created_at = lead.get('created_at_ts')
            earliest_ts = None
            for key in (
                    'events',
                    # 'notes',
                    # 'tasks'
            ):
                collection = sorted(lead.get(key) or [], key=lambda x: x['created_at'])
                if not collection:
                    continue
                current_ts = collection[0]['created_at']
                if not earliest_ts or current_ts < earliest_ts:
                    earliest_ts = current_ts
                    # if lead['id'] == 22797409:
                    #     print('>>', self._convert_date_time_from_unix_timestamp(created_at), self._convert_date_time_from_unix_timestamp(earliest_ts), key)
            lead['created_at_offset'] = 1 if not earliest_ts or earliest_ts - created_at < -3600 * 1 else ''

    @staticmethod
    def _filter(lead: Dict, emails: List[str]) -> bool:
        """ Временно! Фильтрация лидов по адресам электронной почты.

        Args:
            lead: лид
            emails: список email

        Returns:
            True - если email лида содержится в списке адресов
        """
        for contact in lead.get('contacts') or []:
            # перебираем доп. поля в контактах
            for cf in contact.get('custom_fields_values') or []:
                if cf['field_code'] != 'EMAIL':
                    continue
                for value in cf.get('values') or []:
                    email = value['value'] or ''
                    if email.lower() in emails:
                        return True
        return False
