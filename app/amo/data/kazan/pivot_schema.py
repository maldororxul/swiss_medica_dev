""" Схема данных для сводной таблицы """
__author__ = 'ke.mizonov'
from dataclasses import dataclass
from app.amo.data.base.data_schema import TO
from app.amo.data.kazan.data_schema import LeadGrata as Lead
from utils.excel import ExcelClient

DEFAULT_PIPELINES = ['Воронка']


@dataclass()
class PivotGeneral(ExcelClient.PivotData):
    """ Сводная таблица: общая """
    sheet = 'General'
    rows = [Lead.CreatedAt.Key, Lead.Tags.Key]
    filters = [
        ExcelClient.PivotFilter(key=Lead.PipelineName.Key, selected=DEFAULT_PIPELINES),
        ExcelClient.PivotFilter(key=Lead.StatusName.Key)
    ]
    values = [
        ExcelClient.PivotField(
            source=Lead.Stage.Lead,
            conditional_formatting=ExcelClient.ConditionalFormatting.Bars
        ),
        ExcelClient.PivotField(
            key=f'{Lead.Stage.Lead.DisplayName}{TO}{Lead.Stage.FirstContact.DisplayName}',
            calculated=f"= {Lead.Stage.FirstContact.Key} / {Lead.Stage.Lead.Key}",
            number_format=ExcelClient.NumberFormat.Percent,
            conditional_formatting=ExcelClient.ConditionalFormatting.MaxIsGreen
        ),
        ExcelClient.PivotField(
            source=Lead.Stage.FirstContact,
            conditional_formatting=ExcelClient.ConditionalFormatting.Bars
        ),
        ExcelClient.PivotField(
            key=f'{Lead.Stage.FirstContact.DisplayName}{TO}{Lead.Stage.Call.DisplayName}',
            calculated=f"= {Lead.Stage.Call.Key} / {Lead.Stage.FirstContact.Key}",
            number_format=ExcelClient.NumberFormat.Percent
        ),
        ExcelClient.PivotField(source=Lead.Stage.Call),
        ExcelClient.PivotField(
            key=f'{Lead.Stage.Call.DisplayName}{TO}{Lead.Stage.Decision.DisplayName}',
            calculated=f"= {Lead.Stage.Decision.Key} / {Lead.Stage.Call.Key}",
            number_format=ExcelClient.NumberFormat.Percent,
            conditional_formatting=ExcelClient.ConditionalFormatting.MaxIsGreen
        ),
        ExcelClient.PivotField(source=Lead.Stage.Decision),
        ExcelClient.PivotField(
            key=f'{Lead.Stage.Decision.DisplayName}{TO}{Lead.Stage.Meeting.DisplayName}',
            calculated=f"= {Lead.Stage.Meeting.Key} / {Lead.Stage.Decision.Key}",
            number_format=ExcelClient.NumberFormat.Percent,
            conditional_formatting=ExcelClient.ConditionalFormatting.MaxIsGreen
        ),
        ExcelClient.PivotField(source=Lead.Stage.Meeting),
        ExcelClient.PivotField(
            key=f'{Lead.Stage.Meeting.DisplayName}{TO}{Lead.Stage.Agreement.DisplayName}',
            calculated=f"= {Lead.Stage.Agreement.Key} / {Lead.Stage.Meeting.Key}",
            number_format=ExcelClient.NumberFormat.Percent,
            conditional_formatting=ExcelClient.ConditionalFormatting.MaxIsGreen
        ),
        ExcelClient.PivotField(source=Lead.Stage.Agreement),
        ExcelClient.PivotField(
            key=f'{Lead.Stage.Agreement.DisplayName}{TO}{Lead.Stage.Success.DisplayName}',
            calculated=f"= {Lead.Stage.Success.Key} / {Lead.Stage.Agreement.Key}",
            number_format=ExcelClient.NumberFormat.Percent,
            conditional_formatting=ExcelClient.ConditionalFormatting.MaxIsGreen
        ),
        ExcelClient.PivotField(source=Lead.Stage.Success),
        ExcelClient.PivotField(
            key=Lead.Stage.Success.Price,
            number_format=ExcelClient.NumberFormat.Rub,
            displayed_name=f'Выручка ({Lead.Stage.Success.DisplayName})'
        ),
        ExcelClient.PivotField(
            key=Lead.Stage.Success.Price,
            number_format=ExcelClient.NumberFormat.Rub,
            displayed_name=f'Средний чек ({Lead.Stage.Success.DisplayName})',
            consolidation_function=ExcelClient.ConsolidationFunction.Average
        ),
        ExcelClient.PivotField(source=Lead.Meeting28Days),
    ]
    group_function = ExcelClient.GroupFunction.by_months
    col_width = (
        13.86,
        10.29,
        13,
        10.86,
        13,
        6.71,
        13,
        10.71,
        13,
        7.43,
        13,
        8,
        13,
        13,
        13,
        13,
        9.86,
    )


@dataclass()
class PivotAtWork(ExcelClient.PivotData):
    """ Сводная таблица: в работе """
    sheet = 'В работе'
    rows = [Lead.Responsible.Key]
    cols = [
        ExcelClient.PivotCol(
            key=Lead.StatusName.Key,
            selected=['первичный контакт', 'звонок', 'принимает решение', 'Встреча', 'Смета/договор']
        )
    ]
    filters = [
        ExcelClient.PivotFilter(key=Lead.PipelineName.Key, selected=DEFAULT_PIPELINES),
    ]
    values = [
        ExcelClient.PivotField(
            key=Lead.Id.Key,
            displayed_name='Количество',
            consolidation_function=ExcelClient.ConsolidationFunction.Count
        ),
    ]
    col_width = (
        ExcelClient.ColWidth.WeeksInterval,
    )


@dataclass()
class PivotAtWork2(ExcelClient.PivotData):
    """ Сводная таблица: в работе """
    sheet = 'В работе доп'
    rows = [Lead.Responsible.Key]
    cols = [
        ExcelClient.PivotCol(
            key=Lead.LossReason.Key,
            selected=['Готовый дом', 'Отложенный интерес', 'Риэлтор']
        )
    ]
    filters = [
        ExcelClient.PivotFilter(key=Lead.StatusName.Key, selected=['Закрыто и не реализовано']),
        ExcelClient.PivotFilter(key=Lead.PipelineName.Key, selected=DEFAULT_PIPELINES),
    ]
    values = [
        ExcelClient.PivotField(
            key=Lead.Id.Key,
            displayed_name='Количество',
            consolidation_function=ExcelClient.ConsolidationFunction.Count
        ),
    ]
    col_width = (
        ExcelClient.ColWidth.WeeksInterval,
    )


@dataclass()
class PivotAssignmentDuration(ExcelClient.PivotData):
    """ Сводная таблица: время сделки """
    sheet = 'Время сделки'
    rows = [Lead.Stage.Success.Date, Lead.Id.Key]
    cols = [
        ExcelClient.PivotCol(
            key=Lead.Duration30Days.Key
        )
    ]
    filters = [
        ExcelClient.PivotFilter(key=Lead.StatusName.Key, selected=['Успешно реализовано']),
        ExcelClient.PivotFilter(key=Lead.PipelineName.Key, selected=DEFAULT_PIPELINES),
    ]
    values = [
        ExcelClient.PivotField(source=Lead.Stage.RawLead),
        ExcelClient.PivotField(
            key=Lead.Stage.RawLead.Key,
            displayed_name='Доля сделок',
            number_format=ExcelClient.NumberFormat.Percent_2,
            calculated=ExcelClient.CalculationConstant.PercentOfTotal
        ),
    ]
    col_width = (
        ExcelClient.ColWidth.WeeksInterval,
    )
    group_function = ExcelClient.GroupFunction.by_months
    first_data_row = 7
