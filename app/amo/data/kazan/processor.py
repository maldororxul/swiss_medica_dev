""" Постобработчик данных, полученных из AMO """
__author__ = 'ke.mizonov'
from datetime import datetime
from typing import Dict, Optional, Callable, List
from app.amo.data.base.data_schema import LeadField
from app.amo.data.base.processor import AmoProcessor
from app.amo.data.kazan.pivot_schema import PivotGeneral, PivotAtWork, PivotAtWork2, PivotAssignmentDuration
from app.amo.data.kazan.client import KazanClient
from app.amo.data.kazan.data_schema import LeadGrata, CloseReasonGrata
from worker.worker import Worker

_ID = None


class KazanAmoProcessor(AmoProcessor):
    """ Grata клиент для работы с данными """
    data_client: Callable = KazanClient
    leads_file_name: str = 'Leads_Grata'
    # fields: Dict[str, str] = KEYS_MAP_SM
    check_by_stages: bool = True
    lead = LeadGrata
    lead_models = [LeadGrata]

    def _build_stages_fields(self, line: Dict):
        for lead_model in self.lead_models:
            stages_priority = lead_model.get_stages_priority()
            # отдельно добавляем поля, относящиеся к этапам сделки
            line.update({stage.Key: '' for stage in stages_priority})
            # fixme пока не используем, но может понадобится
            line.update({stage.KeyByStage: '' for stage in stages_priority})
            line.update({stage.Date: '' for stage in stages_priority})
            line.update({stage.Price: '' for stage in stages_priority})
            # line.update({stage.Alive: '' for stage in stages_priority})

    def _build_lead_base_data(self, lead: Dict, pre_data: Dict) -> Dict:
        # готовим пустой словарь с обязательным списком полей
        line = {field.Key: '' for field in self.lead.get_fields()}
        # добавляем выборочно сырые поля из лида, а также доп. поля (значение по умолчанию - '')
        line.update({field.Key: lead.get(field.Key) for field in self.lead.get_raw_fields()})
        # добавляем поля utm-меток
        line.update({value.Key: '' for value in self.lead.Utm.__dict__.values() if isinstance(value, LeadField)})
        self._build_stages_fields(line=line)
        # причина закрытия
        loss_reason = lead['loss_reason'][0]['name'] if lead['loss_reason'] else ''
        is_lead = 1 if self._is_lead(loss_reason) and not lead.get('deleted') else ''
        line.update({
            self.lead.Stage.RawLead.Key: 1,
            self.lead.Stage.Lead.Key: is_lead,
            self.lead.LossReason.Key: loss_reason,
            self.lead.Link.Key: self._get_lead_url_by_id(lead_id=lead['id']),
            self.lead.Tags.Key: ', '.join([
                tag['name']
                for tag in lead.get('_embedded', {}).get('tags') or []
            ]),
            self.lead.PipelineName.Key: lead['pipeline'],
            self.lead.StatusName.Key: lead['pipeline_status'],
            self.lead.Responsible.Key: lead['user']['name'],
            # удаленные сделки
            self.lead.Deleted.Key: 1 if lead.get('deleted') else '',
            self.lead.DeletedBy.Key: lead['deleted']['user']['name'] if lead.get('deleted') else ''
        })
        return line

    def _process_custom_fields(self, line: Dict, lead: Dict, pre_data: Dict):
        # кастомные поля
        custom_fields = lead.get('custom_fields_values') or []
        lead_custom_fields = pre_data.get('lead_custom_fields')
        # приоритеты стадий воронки
        stages_priority = self.lead.get_stages_priority()
        # значения из доп. полей (без этапов сделки!)
        countries = []
        for field in custom_fields:
            name = field['field_name']
            if name not in pre_data.get('lead_custom_fields').keys():
                if name in (
                        'Страна',
                        'Country_from_Jivo',
                        # 'CLIENTS_COUNTRY'
                ):
                    value = field['values'][0]['value']
                    if str(value).isnumeric() or ':' in value or '.' in value:
                        continue
                    countries.append(value)
                continue
            line[pre_data.get('lead_custom_fields')[name]] = field['values'][0]['value']
        # utm из доп. полей
        for field in custom_fields:
            name = field['field_name'].lower()
            # if name == 'google client id' and field['values'][0]['value']:
            #     print(field['values'][0]['value'])
            is_utm = False
            for val in self.lead.Utm.__dict__.values():
                if not isinstance(val, LeadField):
                    continue
                if val.Key == name:
                    line[val.Key] = field['values'][0]['value']
                    is_utm = True
                    break
            if not is_utm:
                line[name] = field['values'][0]['value']
        # только для лидов (не сырых!)
        if line[self.lead.Stage.Lead.Key]:
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

    def _freeze_stages(self, line: Dict):
        # маркеры скорости прохождения лида по воронке
        created_at = line[self.lead.CreatedAt.Key]
        if line[self.lead.ClosedAt.Key] and line[self.lead.ClosedAt.Key] >= created_at:
            period = (line[self.lead.ClosedAt.Key] - created_at).days
            line[self.lead.Duration30Days.Key] = period // 30 + 1
        if line[self.lead.Stage.Meeting.Date] and line[self.lead.Stage.Meeting.Date] >= created_at:
            period = (line[self.lead.Stage.Meeting.Date] - created_at).days
            line[self.lead.Meeting28Days.Key] = 1 if period <= 28 else ''

    def _build_lead_data(self, lead: Dict, pre_data: Dict, schedule: Optional[Dict] = None):

        # строим словарь с дефолтными значениями полей лида
        line = self._build_lead_base_data(lead=lead, pre_data=pre_data)
        # заполняем доп. поля лида
        self._process_custom_fields(line=line, lead=lead, pre_data=pre_data)

        # строим историю прохождения сделки по этапам
        stages_priority = self.lead.get_stages_priority()
        self._build_lead_history(
            lead_model=self.lead_models[0],
            lead=lead,
            line=line,
            pipelines_dict=pre_data.get('pipelines_dict'),
            stages_priority=stages_priority
        )
        # костыль на успешную реализацию
        if line[self.lead.StatusName.Key] not in self.lead.Stage.Success.IncludeStages:
            line[self.lead.Stage.Success.Key] = ''
            line[self.lead.Stage.Success.Date] = ''
        if line[self.lead.StatusName.Key] not in self.lead.Stage.Failed.IncludeStages:
            line[self.lead.Stage.Failed.Key] = ''
            line[self.lead.Stage.Failed.Date] = ''
        # дозаполняем пропущенные этапы (полученные по доп. полям)
        self._check_stages_priority(line=line, stages_priority=stages_priority, exclude=(self.lead.Stage.Failed.Key,))

        # считаем время реакции (первого контакта)
        # self._process_first_reaction_time(line=line, lead=lead, schedule=schedule)
        # кастинг дат
        self._cast_dates(line=line, pre_data=pre_data)
        # маркеры скорости прохождения лида по воронке
        self._freeze_stages(line=line)
        # прокидываем цены по этапам
        self._process_prices(line=line, lead=lead)

        # особые статусы
        loss_reason = lead['loss_reason'][0]['name'] if lead['loss_reason'] else ''
        if line[self.lead.Stage.Failed.Key] == 1:
            if loss_reason == CloseReasonGrata.FutureInterest.value:
                line[self.lead.FailedAndFutureInterest.Key] = 1
            if loss_reason == CloseReasonGrata.BuiltHouse.value:
                line[self.lead.FailedAndBuiltHouse.Key] = 1

        # костыль на теги
        line[self.lead.Tags.Key] = line[self.lead.Tags.Key].replace('https://', '')
        # сортировка по ключам
        return self._sort_dict(line)

    def _build_leads_data(
        self,
        date_from: datetime,
        date_to: datetime,
        schedule: Optional[Dict] = None,
        worker: Optional[Worker] = None,
        weekly: bool = False
    ) -> List[Dict]:
        """ Получить обработанный список сделок

        Args:
            date_from: дата с
            date_to: дата по
            schedule: расписание работы
            worker: экземпляр воркера
            weekly: подгонка дат по неделям

        Returns:
            обработанный список сделок за период
        """
        result = []
        leads = self._get_leads(date_from=date_from, date_to=date_to, worker=worker)
        total = len(leads)
        pre_data = self._pre_build(date_from=date_from, date_to=date_to)
        for num, lead in enumerate(leads, 1):
            if num % 100 == 0 and worker:
                worker.emit({'num': num, 'total': total})
            result.append(self._build_lead_data(lead=lead, pre_data=pre_data))
        return result

    @staticmethod
    def _is_lead(loss_reason: str) -> bool:
        """ Возвращает кортеж причин закрытия, которые не соответствуют лидам """
        return loss_reason not in ('Duplicate Lead', 'SPAM')

    @staticmethod
    def _pivot_builders() -> List:
        """ "Строители" сводных таблиц """
        return [
            PivotGeneral.build(),
            PivotAtWork.build(),
            PivotAtWork2.build(),
            PivotAssignmentDuration.build(),
        ]
