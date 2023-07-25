""" Постобработчик данных, полученных из AMO """
__author__ = 'ke.mizonov'
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, Callable, List

from app.amo.api.constants import AmoNote
from app.amo.data.base.data_schema import LeadField
from app.amo.data.base.processor import AmoProcessor
from app.amo.data.cdv.client import DrvorobjevClient
from app.amo.data.cdv.data_schema import LeadCDV, LeadMT
from app.amo.data.cdv.pivot_schema import PivotLeads, PivotPriorConsent, PivotDateOfSale, PivotGeneral, PivotSuccess, \
    PivotGeneralSE, PivotGeneralEN, PivotGeneralFR, PivotGeneralIT, PivotGeneralGE, PivotTreatment, \
    PivotReactionTime, PivotClusterTags
from constants.constants import GoogleSheets
from utils.excel import ExcelClient
from voip.processor import VOIPDataProcessor
from worker.worker import Worker

_ID = None


class DrvorobjevAmoProcessor(AmoProcessor):
    """ Drvorobjev клиент для работы с данными """
    data_client: Callable = DrvorobjevClient
    leads_file_name: str = 'Leads_CDV'
    voip_processor: Optional[VOIPDataProcessor] = VOIPDataProcessor
    lead = LeadCDV
    lead_models = [LeadCDV, LeadMT]
    utm_rules_book_id = GoogleSheets.UtmRulesCDV.value

    @dataclass()
    class Variable:
        LeadToTarget: str = f'{LeadCDV.Stage.Lead.Key}{" -> "}{LeadCDV.Stage.Target.Key}'
        TargetToPriorConsent: str = f'{LeadCDV.Stage.Target.DisplayName}{" -> "}{LeadCDV.Stage.PriorConsent.DisplayName}'
        TargetToQaulification: str = f'{LeadCDV.Stage.Target.DisplayName}{" -> "}{LeadCDV.Stage.Qualification.DisplayName}'
        TargetToWaitingAtClinic: str = f'{LeadCDV.Stage.Target.Key}{" -> "}{LeadCDV.Stage.WaitingAtClinic.Key}'
        TargetShare: str = f'{LeadCDV.Stage.Target.Key}_share'
        WaitingAtClinicShare: str = f'{LeadCDV.Stage.WaitingAtClinic.Key}_share'

    @staticmethod
    def _pivot_tags_builders() -> List:
        """ "Строители" сводных таблиц (теги) """
        return [PivotClusterTags.build()]

    # @profile
    def build_cluster_data(
        self,
        selected_variable: str,
        selected_subjects: List,
        date_from: datetime,
        date_to: datetime,
        worker: Optional[Worker] = None,
        need_result_by_months: bool = True
    ):
        """ Делает выгрузку данных, относящихся к выбранным субъектам, в Excel

        Args:
            selected_variable: параметр, подпадающий под анализ
            selected_subjects: выбранные субъекты
            date_from: дата с
            date_to: дата по
            worker: экземпляр воркера
            need_result_by_months: True - будет построена консолидация по месяцам
        """
        # исходные данные
        if worker:
            worker.emit({'msg': 'building source data...'})
        src_data = self._build_cluster_data(
            date_from=date_from,
            date_to=date_to,
            worker=worker,
            selected_subjects=selected_subjects
        )
        # combined: считаем суммы таргетов и ожиданий по месяцам
        if worker:
            worker.emit({'msg': 'calculating Target and WaitingAtClinic leads...'})
        total_values = {}
        for line in src_data or []:
            created_at = line[self.lead.CreatedAt.Key]
            if need_result_by_months:
                curr_month = datetime(created_at.year, created_at.month, 1).date()
            else:
                curr_month = created_at
            if curr_month not in total_values:
                total_values[curr_month] = {
                    self.lead.Stage.Target.Key: 0,
                    self.lead.Stage.WaitingAtClinic.Key: 0
                }
            total_values[curr_month][self.lead.Stage.Target.Key] += line[self.lead.Stage.Target.Key] or 0
            total_values[curr_month][self.lead.Stage.WaitingAtClinic.Key] += line[self.lead.Stage.WaitingAtClinic.Key] or 0
        # combined: комбинируем переданные субъекты
        if worker:
            worker.emit({'msg': 'building data combinations...'})
        combined_dict = {}
        keys = [subj.Key for subj in selected_subjects]
        for line in src_data:
            created_at = line[self.lead.CreatedAt.Key]
            if need_result_by_months:
                curr_month = datetime(created_at.year, created_at.month, 1).date()
            else:
                curr_month = created_at
            combination = []
            if self.lead.Tags.Key not in keys:
                # случай без тегов
                for key in keys:
                    combination.append(line[key])
            else:
                # случай с тегами
                for tag in line[self.lead.Tags.Key].split(', '):
                    # for key in keys:
                    #     if key == self.lead.Tags.Key:
                    #         continue
                    #     combination.append(line[key])
                    # fixme это вызовет проблемы с title на этапе очистки
                    if tag:
                        combination.append(tag)
            combination = tuple(combination)
            self.__process_combination(
                combined_dict=combined_dict,
                combination=combination,
                line=line,
                curr_month=curr_month
            )
        # combined: считаем доли таргета и приездов
        if worker:
            worker.emit({'msg': 'calculating shares...'})
        for curr, sub_data in combined_dict.items():
            curr_month = curr[-1]
            target_total = total_values[curr_month][self.lead.Stage.Target.Key]
            waiting_total = total_values[curr_month][self.lead.Stage.WaitingAtClinic.Key]
            if target_total > 0:
                sub_data[self.Variable.TargetShare] = sub_data[self.lead.Stage.Target.Key] / target_total
            if waiting_total > 0:
                sub_data[self.Variable.WaitingAtClinicShare] = \
                    sub_data[self.lead.Stage.WaitingAtClinic.Key] / waiting_total
            if sub_data[self.lead.Stage.Lead.Key]:
                sub_data[self.Variable.LeadToTarget] = \
                    sub_data[self.lead.Stage.Target.Key] / sub_data[self.lead.Stage.Lead.Key]
            if sub_data[self.lead.Stage.Target.Key]:
                sub_data[self.Variable.TargetToQaulification] = \
                    sub_data[self.lead.Stage.Qualification.Key] / sub_data[self.lead.Stage.Target.Key]
                sub_data[self.Variable.TargetToPriorConsent] = \
                    sub_data[self.lead.Stage.PriorConsent.Key] / sub_data[self.lead.Stage.Target.Key]
                sub_data[self.Variable.TargetToWaitingAtClinic] = \
                    sub_data[self.lead.Stage.WaitingAtClinic.Key] / sub_data[self.lead.Stage.Target.Key]
        # combined: result
        if worker:
            worker.emit({'msg': 'building combined result...'})
        combined_result = []
        # print(len(selected_subjects))
        for curr, sub_data in combined_dict.items():
            title, month = curr
            # чистим title
            title_splitted = title.split(' && ')
            title = ''

            # обособленный случай с тегами fixme подружить теги с прочими сущностями
            if selected_subjects[0].Key == 'tags':
                for title in title_splitted:
                    if not title:
                        continue
                    line = {
                        'title': title,
                        'date': month
                    }
                    line.update(sub_data)
                    combined_result.append(line)
            else:
                # все, кроме тегов (с тегами пока не дружит!)
                for x in range(len(selected_subjects)):
                    if title_splitted[x]:
                        title = title_splitted[x] if not title else f'{title} && {title_splitted[x]}'
                    else:
                        val = f'__{selected_subjects[x].DisplayName}__'
                        title = val if not title else f'{title} && {val}'
                line = {
                    'title': title,
                    'date': month
                }
                line.update(sub_data)
                combined_result.append(line)
        # combined: группируем по месяцам
        excel_data = [
            ExcelClient.Data(sheet='data', data=combined_result),
            ExcelClient.Data(sheet='source', data=src_data),
        ]
        if need_result_by_months:
            if worker:
                worker.emit({'msg': 'aggregating combinations by periods...'})
            months = sorted(list({str(x[1])[:7] for x in combined_dict.keys()}))
            titles = list({x['title'] for x in combined_result})
            result_by_months = []
            for title in titles:
                item = {
                    'title': title
                }
                item.update({month: '' for month in months})
                item['avrg'] = 0
                result_by_months.append(item)
            for item in result_by_months:
                for line in combined_result:
                    if line['title'] != item['title']:
                        continue
                    curr_month = str(line['date'])[:7]
                    val = line[selected_variable]
                    item[curr_month] = val if val > 0 else ''
            for item in result_by_months:
                total = [item[month] for month in months if item[month]]
                if not total:
                    continue
                item['avrg'] = sum(total) / len(total)
            result_by_months = sorted(result_by_months, key=lambda x: x['avrg'], reverse=True)
            excel_data.append(ExcelClient.Data(sheet='result_by_months', data=result_by_months))
        if worker:
            worker.emit({'msg': 'saving to excel...'})
        ExcelClient(file_name=self.cluster_file_name).write(data=excel_data)

    def __process_combination(self, combined_dict: Dict, combination: Tuple, line: Dict, curr_month: datetime.date):
        title = ' && '.join(combination)
        curr = (title, curr_month)
        if curr not in combined_dict:
            combined_dict[curr] = {
                self.lead.Id.Key: line[self.lead.Id.Key],
                self.lead.Language.Key: line[self.lead.Language.Key],
                self.lead.Country.Key: line[self.lead.Country.Key],
                self.lead.Treatment.Key: line[self.lead.Treatment.Key],
                self.lead.LossReason.Key: line[self.lead.LossReason.Key],
                self.lead.Responsible.Key: line[self.lead.Responsible.Key],
                self.lead.Stage.Lead.Key: 0,
                self.Variable.LeadToTarget: 0,
                self.lead.Stage.Target.Key: 0,
                self.Variable.TargetToQaulification: 0,
                self.lead.Stage.Qualification.Key: 0,
                self.Variable.TargetToPriorConsent: 0,
                self.lead.Stage.PriorConsent.Key: 0,
                self.Variable.TargetToWaitingAtClinic: 0,
                self.lead.Stage.WaitingAtClinic.Key: 0,
                f'{self.lead.Stage.Target.Key}_share': 0,
                f'{self.lead.Stage.WaitingAtClinic.Key}_share': 0
            }
        combined_dict[curr][self.lead.Stage.Lead.Key] += line[self.lead.Stage.Lead.Key] or 0
        combined_dict[curr][self.lead.Stage.Target.Key] += line[self.lead.Stage.Target.Key] or 0
        combined_dict[curr][self.lead.Stage.Qualification.Key] += line[self.lead.Stage.Qualification.Key] or 0
        combined_dict[curr][self.lead.Stage.PriorConsent.Key] += line[self.lead.Stage.PriorConsent.Key] or 0
        combined_dict[curr][self.lead.Stage.WaitingAtClinic.Key] += line[self.lead.Stage.WaitingAtClinic.Key] or 0

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
        src_data = []
        leads = self._build_leads_data(date_from=date_from, date_to=date_to)
        for lead in leads or []:
            line = {
                self.lead.CreatedAt.Key: lead[self.lead.CreatedAt.Key],

                self.lead.Id.Key: lead[self.lead.Id.Key],
                self.lead.Language.Key: lead[self.lead.Language.Key],
                self.lead.Country.Key: lead[self.lead.Country.Key],
                self.lead.Treatment.Key: lead[self.lead.Treatment.Key],
                self.lead.LossReason.Key: lead[self.lead.LossReason.Key],
                self.lead.Responsible.Key: lead[self.lead.Responsible.Key],

                self.lead.Stage.Lead.Key: lead[self.lead.Stage.Lead.Key],
                self.lead.Stage.Target.Key: lead[self.lead.Stage.Target.Key],
                self.lead.Stage.Qualification.Key: lead[self.lead.Stage.Qualification.Key],
                self.lead.Stage.PriorConsent.Key: lead[self.lead.Stage.PriorConsent.Key],
                self.lead.Stage.WaitingAtClinic.Key: lead[self.lead.Stage.WaitingAtClinic.Key]
            }
            line.update({subj.Key: lead[subj.Key] for subj in selected_subjects})
            src_data.append(line)
        return src_data

    def _calls_duration_deprecated(self, lead: Dict, calls: Dict, line: Dict):
        # длительность разговоров (исходя из телефонии, считается по самому длинному звонку для лида)
        longest_call = self._get_longest_call_duration(lead, calls)
        if longest_call > 30:
            line[self.lead.Calls.Key] = 1
        for key, duration_key, duration in (
            (self.lead.CallDuration30.Key, self.lead.CallDurationSummary30.Key, 30),
            (self.lead.CallDuration60.Key, self.lead.CallDurationSummary60.Key, 60),
            (self.lead.CallDuration120.Key, self.lead.CallDurationSummary120.Key, 120),
            (self.lead.CallDuration180.Key, self.lead.CallDurationSummary180.Key, 180),
            (self.lead.CallDuration240.Key, self.lead.CallDurationSummary240.Key, 240),
            (self.lead.CallDuration300.Key, self.lead.CallDurationSummary300.Key, 300),
        ):
            line[key] = 0
            if longest_call > 30:
                line[key] = 1
                line[duration_key] = longest_call
        # проверка Добрицы
        dobrica_call_duration = self._get_dobrica_call(lead, calls)
        if dobrica_call_duration >= 45:
            line[self.lead.CallDobrica45.Key] = 1
        # время исходящих звонков
        line[self.lead.FirstOutgoingCallDateTime.Key] = self._get_outgoing_call_time(lead=lead, calls=calls)

    def _process_pipelines(self, line: Dict, lead: Dict, pre_data: Dict):
        for lead_model in self.lead_models:
            stages_priority = lead_model.get_stages_priority()
            # if lead_model is not self.lead and self.lead.Stage.Target.Key == lead_model.Stage.Target.Key:
            #     continue
            loss_reason = lead['loss_reason'][0]['name'] if lead['loss_reason'] else ''
            is_lead = 1 if self._is_lead(loss_reason) and not lead.get('deleted') else ''
            is_target = 1 if is_lead and (not loss_reason or loss_reason in lead_model.get_loss_reasons()) else ''
            line[lead_model.Stage.Target.Key] = is_target
            # строим историю прохождения сделки по этапам todo прокинуть lead_model
            self._build_lead_history(
                lead_model=lead_model,
                lead=lead,
                line=line,
                pipelines_dict=pre_data.get('pipelines_dict'),
                stages_priority=stages_priority
            )
            # дозаполняем пропущенные этапы (полученные по доп. полям)
            self._check_stages_priority(line=line, stages_priority=stages_priority)

    def _process_custom_fields(self, line: Dict, lead: Dict, pre_data: Dict):
        # кастомные поля
        custom_fields = lead.get('custom_fields_values') or []
        # приоритеты стадий воронки
        # stages_priority = self.lead.get_stages_priority()
        # значения из доп. полей (без этапов сделки!)
        countries = []
        for field in custom_fields:
            name = field['field_name']
            if name not in pre_data.get('lead_custom_fields').keys():
                if name in (
                        'Country',
                        'Страна',
                        'Country_from_Jivo',
                        # 'CLIENTS_COUNTRY'
                ):
                    value = field['values'][0]['value']
                    if str(value).isnumeric() or ':' in value or '.' in value:
                        continue
                    countries.append(value)
                continue
            line[pre_data.get('lead_custom_fields')[name]] = self._get_cf_values(field=field)       # todo проверить
        # докидываем страну, если ее не удалось заполнить из доп. поля Country
        if not line[self.lead.Country.Key]:
            if countries:
                line[self.lead.Country.Key] = countries[0]
            else:
                for contact in lead.get('contacts') or []:
                    for field in contact.get('custom_fields_values') or []:
                        if field['field_name'] in ('Country by phone', 'Страна по номеру телефона', 'Country by IP'):
                            val = field['values'][0]['value']
                            if not val:
                                continue
                            countries.append(val)
                if countries:
                    line[self.lead.Country.Key] = countries[0]
        # очистка названий стран
        self._clear_country(line=line)
        # utm из доп. полей
        for field in custom_fields:
            name = field['field_name'].lower()
            for val in self.lead.Utm.__dict__.values():
                if not isinstance(val, LeadField):
                    continue
                if val.Key == name:
                    line[val.Key] = field['values'][0]['value']
                    break

        # if line['id'] == 22945867:
        #     print('>>', line[self.lead.ReachedStage.Key])

        # только для лидов (не сырых!)
        for lead_model in self.lead_models:
            if line['pipeline_name'] not in lead_model.Pipelines:
                continue
            # приоритеты стадий воронки
            stages_priority = lead_model.get_stages_priority()
            if not line[lead_model.Stage.Lead.Key]:
                continue
            if line['id'] == 22628905:
                print(line['pipeline_name'], lead_model.Pipelines, line['pipeline_name'] not in lead_model.Pipelines)
                print(f'-{line[lead_model.Stage.Lead.Key]}-', not line[lead_model.Stage.Lead.Key])
            # определяем достигнутые этапы сделки по доп. полям
            for field in custom_fields:
                name = field['field_name']
                # значение по умолчанию для всех None - ''
                value = 1 if field['values'][0]['value'] else ''
                # fixme конструкция чисто для проверки
                # value = field['values'][0]['value']
                # if isinstance(value, str) and value.isnumeric():
                #     value = 1 if value else ''
                # elif isinstance(value, bool):
                #     value = 1 if value else ''
                # else:
                #     value = 1 if value else ''
                for stage in stages_priority:
                    if name not in stage.IncludeFields and name.lower() not in stage.IncludeFields:
                        continue
                    line[stage.Key] = value
                    if value == 1:
                        if line['id'] == 22628905:
                            print(name, value, lead_model.ReachedStage.Key, stage.DisplayName)
                        line[lead_model.ReachedStage.Key] = stage.DisplayName
        if line['id'] == 22628905:
            print('>>', line[self.lead.ReachedStage.Key])

        # # только для лидов (не сырых!)
        # if line[self.lead.Stage.Lead.Key]:
        #     # определяем достигнутые этапы сделки по доп. полям
        #     for field in custom_fields:
        #         name = field['field_name']
        #         # значение по умолчанию для всех None - ''
        #         value = field['values'][0]['value']
        #         if isinstance(value, str) and value.isnumeric():
        #             value = 1 if value else ''
        #         elif isinstance(value, bool):
        #             value = 1 if value else ''
        #         else:
        #             value = 1 if value else ''
        #         for stage in stages_priority:
        #             if name not in stage.IncludeFields and name.lower() not in stage.IncludeFields:
        #                 continue
        #             line[stage.Key] = value
        #     # строим историю прохождения сделки по этапам
        #     self._build_lead_history(
        #         lead_model=self.lead_models[0],
        #         lead=lead,
        #         line=line,
        #         pipelines_dict=pre_data.get('pipelines_dict'),
        #         stages_priority=stages_priority
        #     )
        #     # дозаполняем пропущенные этапы (полученные по доп. полям)
        #     self._check_stages_priority(line=line, stages_priority=stages_priority)

    def _freeze_stages(self, line: Dict):
        created_at = line[self.lead.CreatedAt.Key]
        if line[self.lead.DateOfAdmission.Key] and line[self.lead.DateOfAdmission.Key] >= created_at:
            period = (line[self.lead.DateOfAdmission.Key] - created_at).days
            line[self.lead.Admission7Days.Key] = period // 7 + 1
            line[self.lead.Admission14Days.Key] = 1 if period <= 14 else ''
        if line[self.lead.DateOfPriorConsent.Key] and line[self.lead.DateOfPriorConsent.Key] >= created_at:
            period = (line[self.lead.DateOfPriorConsent.Key] - created_at).days
            line[self.lead.PriorConsent14Days.Key] = 1 if period <= 14 else ''

    def _build_lead_data(self, lead: Dict, pre_data: Dict, schedule: Optional[Dict] = None):
        # строим словарь с дефолтными значениями полей лида
        line = self._build_lead_base_data(lead=lead, pre_data=pre_data)
        # заполняем доп. поля лида
        self._process_custom_fields(line=line, lead=lead, pre_data=pre_data)

        # костыль для дополнительных воронок
        self._process_pipelines(line=line, lead=lead, pre_data=pre_data)

        # длительность звонков
        # self._calls_duration(lead=lead, calls=pre_data.get('calls'), line=line)
        self._calls_duration(lead=lead, line=line)

        # считаем время реакции (первого контакта)
        # self._process_first_reaction_time(line=line, lead=lead, schedule=schedule)
        # кастинг дат
        self._cast_dates(line=line, pre_data=pre_data)
        # маркеры скорости прохождения лида по воронке
        self._freeze_stages(line=line)
        # прокидываем цены по этапам
        self._process_prices(line=line, lead=lead)

        # лиды в работе todo для остальных воронок? системное решение
        # line[self.lead.AtWorkAnyPipeline.Key] = ''
        # for lead_model in self.lead_models:
        #     if line['id'] == 22978323:
        #         print('--', line[lead_model.AtWork.Key])
        #     if line[lead_model.AtWork.Key] != '':
        #         line[self.lead.AtWorkAnyPipeline.Key] = 1
        # if line['id'] == 22978323:
        #     print('AtWorkAnyPipeline', line[self.lead.AtWorkAnyPipeline.Key])

        # телефоны
        line[self.lead.Phone.Key] = self.get_lead_contacts(lead)

        # сортировка по ключам
        return self._sort_dict(line)

    def _calls_duration(self, lead: Dict, line: Dict, duration_from: int = 120):
        # if lead['id'] == 21329007:
        #     for note in lead.get('notes') or []:
        #         _type = note.get('note_type')
        #         if _type not in (AmoNote.IncomeCall.value, AmoNote.OutcomeCall.value):
        #             continue
        #         print(note)
        longest_duration = 0
        longest_call_url = None
        # длительность считаем только для лидов - не для сырых лидов
        for lead_model in self.lead_models:
            if line[lead_model.Stage.Lead.Key] == 1:
                break
        else:
            return
        for note in lead.get('notes') or []:
            _type = note.get('note_type')
            if _type not in (AmoNote.IncomeCall.value, AmoNote.OutcomeCall.value):
                continue
            params = note.get('params')
            duration = params.get('duration')
            # исключим подозрительно долгие "разговоры" с таким результатом звонка
            if params.get('call_result') in ('0 ',):
                continue
            if isinstance(duration, str):
                if not duration.isnumeric():
                    continue
                duration = int(duration)
            if duration == 0:
                continue
            if duration < duration_from:
                continue
            # исключим разговоры длительностью более 2,5 часов
            if duration > 3600 * 2.5:
                continue
            if duration > longest_duration:
                longest_duration = duration
                longest_call_url = params.get('link')
        line[self.lead.LongestCallDuration.Key] = longest_duration if longest_duration > 0 else ''
        line[self.lead.LongestCallLink.Key] = longest_call_url if longest_call_url else ''

    def _weekly_offset(self, weekly: bool, collection: List[Dict]):
        # искуственно смещаем отдельные самые ранние даты для построения адекватной картины по неделям
        if weekly:
            for key in (
                # self.lead.CreatedAt.Key,
                self.lead.DateOfPriorConsent.Key,
                self.lead.DateOfSale.Key,
                self.lead.DateOfAdmission.Key
            ):
                self._smallest_date_offset(collection=collection, key=key)

    # def _build_leads_data(
    #     self,
    #     date_from: datetime,
    #     date_to: datetime,
    #     schedule: Optional[Dict] = None,
    #     worker: Optional[Worker] = None,
    #     weekly: bool = False
    # ) -> List[Dict]:
    #     """ Получить обработанный список сделок
    #
    #     Args:
    #         date_from: дата с
    #         date_to: дата по
    #         schedule: расписание работы
    #         worker: экземпляр воркера
    #         weekly: подгонка дат по неделям
    #
    #     Returns:
    #         обработанный список сделок за период
    #     """
    #     result = []
    #     leads = self._get_leads(date_from=date_from, date_to=date_to, worker=worker)
    #     total = len(leads)
    #     pre_data = self._pre_build(date_from=date_from, date_to=date_to)
    #     for num, lead in enumerate(leads, 1):
    #         if num % 100 == 0 and worker:
    #             worker.emit({'num': num, 'total': total})
    #         result.append(self._build_lead_data(lead=lead, pre_data=pre_data))
    #     self._weekly_offset(weekly=weekly, collection=result)
    #     return result

    @staticmethod
    def _smallest_date_offset(collection: List, key: str):
        """ Смещает самую раннюю дату до ближайшего понедельника (ради адекватного построения пивота по неделям) """
        smallest_date = None
        for line in collection:
            curr_date = line[key]
            if not curr_date or isinstance(curr_date, str):
                continue
            if not smallest_date or curr_date < smallest_date:
                smallest_date = curr_date
        for line in collection:
            curr_date = line[key]
            if isinstance(curr_date, str):
                continue
            if curr_date == smallest_date:
                line[key] -= timedelta(days=curr_date.weekday())

    @staticmethod
    def _is_lead(loss_reason: str) -> bool:
        """ Возвращает кортеж причин закрытия, которые не соответствуют лидам """
        return loss_reason not in ('Duplicate Lead', 'SPAM')

    @staticmethod
    def _pivot_builders() -> List:
        """ "Строители" сводных таблиц """
        return [
            PivotLeads.build(),
            PivotGeneral.build(),
            PivotGeneralSE.build(),
            PivotGeneralEN.build(),
            PivotGeneralFR.build(),
            PivotGeneralIT.build(),
            PivotGeneralGE.build(),
            PivotPriorConsent.build(),
            PivotDateOfSale.build(),
            PivotTreatment.build(),
            PivotSuccess.build(),
            PivotReactionTime.build(),
            # PivotCalls.build(),

            # PivotFunnel.build(),
            # PivotLeadsMT.build(),

            # PivotCommunications.build()

            # PivotCrew.build(),
            # PivotReactionTimeIncoming.build(),
            # PivotReactionTimeOutgoing.build(),
            # PivotManagers.build()
        ]
