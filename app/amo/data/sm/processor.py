""" Постобработчик данных, полученных из AMO """
__author__ = 'ke.mizonov'
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional, Tuple, Callable, List
from app.amo.data.base.data_schema import LeadField
from app.amo.data.base.processor import AmoProcessor
from app.amo.data.sm.client import SwissmedicaClient
from app.amo.data.sm.data_schema import LeadSM
from app.amo.data.sm.pivot_schema import PivotWeeklyAll, PivotWeeklyIT, PivotClusterTags, PivotWeeklyAllExceptAutism, PivotWeeklyAutism
from constants.constants import GoogleSheets
from google_api.client import GoogleAPIClient
from utils.excel import ExcelClient
from utils.serializer import PklSerializer
from worker.worker import Worker

_ID = None
MAXIMUM_OFFER_SENDING_SPEED = 45


class SwissmedicaAmoProcessor(AmoProcessor):
    """ Swissmedica клиент для работы с данными """
    data_client: Callable = SwissmedicaClient
    leads_file_name: str = 'Leads_SM'
    lead = LeadSM
    lead_models = [LeadSM]
    utm_rules_book_id = GoogleSheets.UtmRulesSM.value

    @dataclass()
    class Variable:
        LeadToTarget: str = f'{LeadSM.Stage.Lead.Key}{" -> "}{LeadSM.Stage.Target.Key}'
        TargetToPriorConsent: str = f'{LeadSM.Stage.Target.DisplayName}{" -> "}{LeadSM.Stage.PriorConsent.DisplayName}'
        TargetToQaulification: str = f'{LeadSM.Stage.Target.DisplayName}{" -> "}{LeadSM.Stage.Qualification.DisplayName}'
        # TargetToWaitingAtClinic: str = f'{self.lead.Stage.Target.Key}{" -> "}{self.lead.Stage.WaitingAtClinic.Key}'
        TargetShare: str = f'{LeadSM.Stage.Target.Key}_share'
        # WaitingAtClinicShare: str = f'{self.lead.Stage.WaitingAtClinic.Key}_share'

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
        worker.emit({'msg': 'building source data...'})
        src_data = self._build_cluster_data(
            date_from=date_from,
            date_to=date_to,
            worker=worker,
            selected_subjects=selected_subjects
        )
        # combined: считаем суммы таргетов и ожиданий по месяцам
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
                    # self.lead.Stage.WaitingAtClinic.Key: 0
                }
            total_values[curr_month][self.lead.Stage.Target.Key] += line[self.lead.Stage.Target.Key] or 0
            # total_values[curr_month][self.lead.Stage.WaitingAtClinic.Key] += line[self.lead.Stage.WaitingAtClinic.Key] or 0
        # combined: комбинируем переданные субъекты
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
        worker.emit({'msg': 'calculating shares...'})
        for curr, sub_data in combined_dict.items():
            curr_month = curr[-1]
            target_total = total_values[curr_month][self.lead.Stage.Target.Key]
            # waiting_total = total_values[curr_month][self.lead.Stage.WaitingAtClinic.Key]
            if target_total > 0:
                sub_data[self.Variable.TargetShare] = sub_data[self.lead.Stage.Target.Key] / target_total
            # if waiting_total > 0:
                # sub_data[self.Variable.WaitingAtClinicShare] = \
                #     sub_data[self.lead.Stage.WaitingAtClinic.Key] / waiting_total
            if sub_data[self.lead.Stage.Lead.Key]:
                sub_data[self.Variable.LeadToTarget] = \
                    sub_data[self.lead.Stage.Target.Key] / sub_data[self.lead.Stage.Lead.Key]
            if sub_data[self.lead.Stage.Target.Key]:
                sub_data[self.Variable.TargetToQaulification] = \
                    sub_data[self.lead.Stage.Qualification.Key] / sub_data[self.lead.Stage.Target.Key]
                sub_data[self.Variable.TargetToPriorConsent] = \
                    sub_data[self.lead.Stage.PriorConsent.Key] / sub_data[self.lead.Stage.Target.Key]
                # sub_data[self.Variable.TargetToWaitingAtClinic] = \
                #     sub_data[self.lead.Stage.WaitingAtClinic.Key] / sub_data[self.lead.Stage.Target.Key]
        # combined: result
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
        excel_data = [
            ExcelClient.Data(sheet='data', data=combined_result),
            ExcelClient.Data(sheet='source', data=src_data),
        ]
        # combined: группируем по месяцам
        if need_result_by_months:
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
        worker.emit({'msg': 'saving to excel...'})
        ExcelClient(file_name=self.cluster_file_name).write(data=excel_data)

    def update_alive_leads(self, schedule: Optional[Dict] = None, worker: Optional[Worker] = None):
        super().update_alive_leads(schedule=schedule, worker=worker)
        alive_leads = PklSerializer(file_name='alive_swissmedica').load() or []
        if not alive_leads:
            return
        users = {x['responsible_user_name']: 0 for x in alive_leads}
        latest_date = alive_leads[-1]['date']
        for lead in alive_leads:
            if lead['date'] != latest_date:
                continue
            users[lead['responsible_user_name']] += 1
        users['date'] = str(datetime.now().date())
        users['wd'] = 'Leads'
        # todo остановился тут - google sheets
        GoogleAPIClient(
            book_id=GoogleSheets.ScheduleSM.value,
            sheet_title='Schedule'
        ).update_leads_quantity(users=users)

    @staticmethod
    def _pivot_tags_builders() -> List:
        """ "Строители" сводных таблиц (теги) """
        return [PivotClusterTags.build()]

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
                # self.Variable.TargetToWaitingAtClinic: 0,
                # self.lead.Stage.WaitingAtClinic.Key: 0,
                f'{self.lead.Stage.Target.Key}_share': 0,
                # f'{self.lead.Stage.WaitingAtClinic.Key}_share': 0
            }
        combined_dict[curr][self.lead.Stage.Lead.Key] += line[self.lead.Stage.Lead.Key] or 0
        combined_dict[curr][self.lead.Stage.Target.Key] += line[self.lead.Stage.Target.Key] or 0
        combined_dict[curr][self.lead.Stage.Qualification.Key] += line[self.lead.Stage.Qualification.Key] or 0
        combined_dict[curr][self.lead.Stage.PriorConsent.Key] += line[self.lead.Stage.PriorConsent.Key] or 0
        # combined_dict[curr][self.lead.Stage.WaitingAtClinic.Key] += line[self.lead.Stage.WaitingAtClinic.Key] or 0

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
                # self.lead.Stage.WaitingAtClinic.Key: lead[self.lead.Stage.WaitingAtClinic.Key]
            }
            line.update({subj.Key: lead[subj.Key] for subj in selected_subjects})
            src_data.append(line)
        return src_data

    def _process_custom_fields(self, line: Dict, lead: Dict, pre_data: Dict):
        # кастомные поля
        custom_fields = lead.get('custom_fields_values') or []
        lead_custom_fields = pre_data.get('lead_custom_fields')
        # значения из доп. полей (без этапов сделки!)
        countries = []
        quest_received = None
        for field in custom_fields:
            name = field['field_name']
            # как быстро отправили оффер после получения опросника
            if name == 'Recieved Questionnair':
                quest_received = field['values'][0]['value']
            if quest_received and name == 'Отправили OFFER Пациенту.':
                value = round((field['values'][0]['value'] - quest_received) / 3600 / 24, 0)
                if value > MAXIMUM_OFFER_SENDING_SPEED:
                    value = MAXIMUM_OFFER_SENDING_SPEED
                line[self.lead.OfferSendingSpeed.Key] = value
            # страны
            if name not in lead_custom_fields.keys():
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
            val = field['values'][0]['value']
            if isinstance(val, bool):
                val = 1 if val else 0
            if name == self.lead.Agent.CustomField:
                val = 1 if val else 0
            line[lead_custom_fields[name]] = val
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
            # if name == 'google client id' and field['values'][0]['value']:
            #     print(field['values'][0]['value'])
            for val in self.lead.Utm.__dict__.values():
                if not isinstance(val, LeadField):
                    continue
                if val.Key == name:
                    line[val.Key] = field['values'][0]['value']
                    break
        # только для лидов (не сырых!)
        for lead_model in self.lead_models:
            # приоритеты стадий воронки
            stages_priority = lead_model.get_stages_priority()
            if not line[lead_model.Stage.Lead.Key]:
                continue
            # определяем достигнутые этапы сделки по доп. полям
            for field in custom_fields:
                name = field['field_name']
                # значение по умолчанию для всех None - ''
                value = field['values'][0]['value']
                if isinstance(value, str) and value.isnumeric():
                    value = 1 if value else ''
                elif isinstance(value, bool):
                    value = 1 if value else ''
                else:
                    value = 1 if value else ''
                for stage in stages_priority:
                    if name not in stage.IncludeFields and name.lower() not in stage.IncludeFields:
                        continue
                    line[stage.Key] = value

    # def _pre_build(self, date_from: datetime, date_to: datetime) -> Dict:
    #     """ Предзагрузка словарей, необходимых для построения данных по лидам
    #
    #     Args:
    #         date_from: дата с
    #         date_to: дата по
    #
    #     Returns:
    #         словари, необходимые для построения данных по лидам
    #     """
    #     pre_data = super()._pre_build(date_from=date_from, date_to=date_to)
    #     pre_data['stages_priority_ha'] = LeadHA.get_stages_priority()
    #     pre_data['stages_priority_diabetes'] = LeadDiabetes.get_stages_priority()
    #     return pre_data

    def _process_pipelines(self, line: Dict, lead: Dict, pre_data: Dict):
        loss_reason = lead['loss_reason'][0]['name'] if lead['loss_reason'] else ''
        is_lead = 1 if self._is_lead(loss_reason) and not lead.get('deleted') else ''
        for lead_model in self.lead_models:
            stages_priority = lead_model.get_stages_priority()
            # if lead_model is not self.lead and self.lead.Stage.Target.Key == lead_model.Stage.Target.Key:
            #     continue
            is_target = 1 if is_lead and (not loss_reason or loss_reason in lead_model.get_loss_reasons()) else ''
            line[lead_model.Stage.Target.Key] = is_target
            # строим историю прохождения сделки по этапам
            self._build_lead_history(
                lead_model=lead_model,
                lead=lead,
                line=line,
                pipelines_dict=pre_data.get('pipelines_dict'),
                stages_priority=stages_priority
            )
            # дозаполняем пропущенные этапы (полученные по доп. полям)
            self._check_stages_priority(line=line, stages_priority=stages_priority)

    # def _build_stages_fields(self, line: Dict, pre_data: Dict):
    #     # отдельно добавляем поля, относящиеся к этапам сделки
    #     stages_priority = pre_data.get('stages_priority')
    #     stages_priority_ha = pre_data.get('stages_priority_ha')
    #     line.update({stage.Key: '' for stage in stages_priority})
    #     line.update({stage.Price: '' for stage in stages_priority})
    #     line.update({stage.Key: '' for stage in stages_priority_ha})
    #     line.update({stage.Price: '' for stage in stages_priority_ha})

    def _freeze_stages(self, line: Dict):
        if not self._is_lead(line[self.lead.LossReason.Key]):
            return
        created_at = line[self.lead.CreatedAt.Key]
        if line[self.lead.ClosedAt.Key] and line[self.lead.ClosedAt.Key] >= created_at:
            period = (line[self.lead.ClosedAt.Key] - created_at).days
            line[self.lead.Duration30Days.Key] = period // 30 + 1
        if line[self.lead.DateOfPriorConsent.Key] and line[self.lead.DateOfPriorConsent.Key] >= created_at:
            period = (line[self.lead.DateOfPriorConsent.Key] - created_at).days
            line[self.lead.PriorConsent28Days.Key] = 1 if period <= 28 else ''
        if line[self.lead.DateOfQuestionnaireRecieved.Key] and line[
            self.lead.DateOfQuestionnaireRecieved.Key] >= created_at:
            period = (line[self.lead.DateOfQuestionnaireRecieved.Key] - created_at).days
            line[self.lead.QuestionnaireRecieved7Days.Key] = 1 if period <= 7 else ''
        if line[self.lead.DateOfOffer.Key] and line[self.lead.DateOfOffer.Key] >= created_at:
            period = (line[self.lead.DateOfOffer.Key] - created_at).days
            line[self.lead.OfferSent14Days.Key] = 1 if period <= 14 else ''

    def _freeze_stages_italy(self, line: Dict):
        if line[self.lead.PipelineName.Key] not in ('Italy', 'Italian'):
            return
        if not self._is_lead(line[self.lead.LossReason.Key]):
            return
        created_at = line[self.lead.CreatedAt.Key]
        if line[self.lead.DateOfPriorConsent.Key] and line[self.lead.DateOfPriorConsent.Key] >= created_at:
            period = (line[self.lead.DateOfPriorConsent.Key] - created_at).days
            line[self.lead.PriorConsent35Days.Key] = 1 if period <= 35 else ''
        if line[self.lead.DateOfQuestionnaireRecieved.Key] and line[
            self.lead.DateOfQuestionnaireRecieved.Key] >= created_at:
            period = (line[self.lead.DateOfQuestionnaireRecieved.Key] - created_at).days
            line[self.lead.QuestionnaireRecieved14Days.Key] = 1 if period <= 14 else ''
        if line[self.lead.DateOfOffer.Key] and line[self.lead.DateOfOffer.Key] >= created_at:
            period = (line[self.lead.DateOfOffer.Key] - created_at).days
            line[self.lead.OfferSent21Days.Key] = 1 if period <= 21 else ''

    def _pre_build(self, date_from: datetime, date_to: datetime) -> Dict:
        """ Предзагрузка словарей, необходимых для построения данных по лидам

        Args:
            date_from: дата с
            date_to: дата по

        Returns:
            словари, необходимые для построения данных по лидам
        """
        data = super()._pre_build(date_from=date_from, date_to=date_to)
        data['restore_loss_reasons'] = PklSerializer('restore_loss_reasons').load() or {}
        data['utm_rules'] = GoogleAPIClient(book_id=self.utm_rules_book_id, sheet_title='rules').get_sheet()
        return data

    def _build_lead_data(self, lead: Dict, pre_data: Dict, schedule: Optional[Dict] = None):

        # строим словарь с дефолтными значениями полей лида
        line = self._build_lead_base_data(lead=lead, pre_data=pre_data)
        # заполняем доп. поля лида
        self._process_custom_fields(line=line, lead=lead, pre_data=pre_data)

        # костыль для дополнительных воронок
        self._process_pipelines(line=line, lead=lead, pre_data=pre_data)

        # считаем время реакции (первого контакта)
        # self._process_first_reaction_time(line=line, lead=lead, schedule=schedule)
        # кастинг дат
        self._cast_dates(line=line, pre_data=pre_data)
        # маркеры скорости прохождения лида по воронке
        self._freeze_stages(line=line)
        # особая скорость для Италии
        self._freeze_stages_italy(line=line)
        # прокидываем цены по этапам
        self._process_prices(line=line, lead=lead)

        # лиды в работе todo для остальных воронок? системное решение
        # line[self.lead.AtWorkAnyPipeline.Key] = ''
        # for lead_model in self.lead_models:
        #     if line[lead_model.AtWork.Key] != '':
        #         line[self.lead.AtWorkAnyPipeline.Key] = 1

        # продажа, включая в клинике и выписан из клиники
        line[self.lead.PurchaseExtended.Key] = line[self.lead.Stage.Purchase.Key]
        line[self.lead.PurchaseExtendedPrice.Key] = line[self.lead.Stage.Purchase.Price]
        if not line[self.lead.PurchaseExtended.Key]:
            line[self.lead.PurchaseExtended.Key] = line[self.lead.Stage.Audit.Key]
            line[self.lead.PurchaseExtendedPrice.Key] = line[self.lead.Stage.Audit.Price]
        if not line[self.lead.PurchaseExtended.Key]:
            line[self.lead.PurchaseExtended.Key] = line[self.lead.Stage.Treatment.Key]
            line[self.lead.PurchaseExtendedPrice.Key] = line[self.lead.Stage.Treatment.Price]

        # телефоны
        line[self.lead.Phone.Key] = self.get_lead_contacts(lead)

        # сортировка по ключам
        return self._sort_dict(line)

    # def _process_prices(self, line: Dict, lead: Dict, pre_data: Dict):
    #     for lead_model in self.lead_models:
    #         stages_priority = lead_model.get_stages_priority()
    #         price = lead['price']
    #         for stage in stages_priority:
    #             if line.get(stage.Key) is None:
    #                 continue
    #             line[stage.Price] = price if line[stage.Key] == 1 else ''

    @staticmethod
    def _is_lead(loss_reason: str) -> bool:
        """ Возвращает кортеж причин закрытия, которые не соответствуют лидам """
        return loss_reason not in (
            'Duplicate Lead',
            'SPAM',
            'СПАМ',
            'Ресерч\Студент\Поиск работы',
            'Тестовая сделка',
            'Неправильные контакты ( неправильный но',
            'Неправильные контакты ( неправильный номер \ нет н',
            'Ресерч\Студент\Поиск работы',
            'Пациент не отправлял заявку'
        )

    @staticmethod
    def _pivot_builders() -> List:
        """ "Строители" сводных таблиц """
        return [
            # PivotLeads.build(),
            # PivotPriorConsent.build(),
            # PivotDateOfSale.build(),
            # PivotGeneral.build(),

            # PivotWeeklyBO.build(),
            # PivotWeeklyDiabetes.build(),
            PivotWeeklyAll.build(),
            PivotWeeklyAllExceptAutism.build(),
            PivotWeeklyAutism.build(),
            PivotWeeklyIT.build(),
            # PivotMonthlyFull.build(),
            # PivotMonthlyFullExceptAutism.build(),
            # PivotMonthlyFullAutism.build(),
            # PivotOfferSendingSpeed.build(),
            # PivotReactionTime.build(),

            # PivotWeeklyEN.build(),
            # PivotWeeklyGE.build(),
            # PivotWeeklyFR.build(),
            # PivotCrew.build(),
            # PivotMonthlyIntermediate.build(),
            # PivotMonthlyForecast.build(),

            # PivotGeneralNew.build(),
            # PivotSuccess.build(),
            # PivotManagers.build()
        ]