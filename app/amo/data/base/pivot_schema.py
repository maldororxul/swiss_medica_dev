""" Схема данных для сводной таблицы """
__author__ = 'ke.mizonov'
from dataclasses import dataclass
from amo.data.base.data_schema import Lead
from utils.excel import ExcelClient


@dataclass()
class PivotCrew(ExcelClient.PivotData):
    """ Сводная таблица: нагрузка на менеджеров """
    sheet = 'Alive leads'
    filters = [ExcelClient.PivotFilter(key=Lead.PipelineName.Key), ExcelClient.PivotFilter(key=Lead.StatusName.Key)]
    rows = [
        'date'
    ]
    cols = [
        ExcelClient.PivotCol(
            key=Lead.Responsible.Key
        )
    ]
    values = [
        ExcelClient.PivotField(source=Lead.AtWorkAnyPipeline),
    ]
    group_function = ExcelClient.GroupFunction.by_months
    col_width = (
        ExcelClient.ColWidth.WeeksInterval,
    )


@dataclass()
class PivotReactionTime(ExcelClient.PivotData):
    """ Сводная таблица: время реакции """
    sheet = 'Reaction'
    filters = [
        ExcelClient.PivotFilter(key=Lead.ReactionType.Key),
        ExcelClient.PivotFilter(key=Lead.CreationSource.Key, selected=['(blank)']),
        ExcelClient.PivotFilter(key=Lead.PipelineName.Key),
        ExcelClient.PivotFilter(key=Lead.FirstSuccessfulIncomingCall.Key, selected=['(blank)']),
        ExcelClient.PivotFilter(key=Lead.Jivo.Key),
    ]
    rows = [Lead.OnDuty.Key, Lead.CreatedAt.Key]
    values = [
        ExcelClient.PivotField(source=Lead.Stage.Lead),
        # lead -> fast reaction
        ExcelClient.PivotField(
            conversion_from=Lead.Stage.Lead,
            conversion_to=Lead.ReactionTimeLess300,
            conditional_formatting=ExcelClient.ConditionalFormatting.MaxIsGreen,
        ),
        ExcelClient.PivotField(source=Lead.ReactionTimeLess300),
        # lead -> slow reaction
        ExcelClient.PivotField(
            conversion_from=Lead.Stage.Lead,
            conversion_to=Lead.ReactionTimeGreater300,
            conditional_formatting=ExcelClient.ConditionalFormatting.MaxIsRed,
        ),
        ExcelClient.PivotField(source=Lead.ReactionTimeGreater300),
        # lead -> missed
        ExcelClient.PivotField(
            conversion_from=Lead.Stage.Lead,
            conversion_to=Lead.ReactionTimeMissed,
            conditional_formatting=ExcelClient.ConditionalFormatting.MaxIsRed,
        ),
        ExcelClient.PivotField(source=Lead.ReactionTimeMissed),
    ]
    group_function = ExcelClient.GroupFunction.by_weeks
    first_data_row = 9
    collide = False
