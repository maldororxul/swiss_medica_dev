""" Схема данных для сводной таблицы """
__author__ = 'ke.mizonov'
from dataclasses import dataclass
from app.amo.data.base.data_schema import PRICE
from app.amo.data.base.pivot_schema import (
    PivotReactionTime as PivotReactionTimeBase
)
# from amo.data.base.reaction_time import ReactionTimeBase
from app.amo.data.cdv.data_schema import LeadCDV as Lead, LeadMT
from utils.excel import ExcelClient

DEFAULT_PIPELINES = [
    'New_patients_general_SE',
    'New_patients_ENG',
    'New_patients_FR',
    'New_patients_IT',
    'New_patients_GE',
    'New_patients_SP',
    'New_patients_RU',
    'New_patients_RO'
]


@dataclass()
class PivotCrew(ExcelClient.PivotData):
    """ Сводная таблица: нагрузка на менеджеров
    (активные лиды на этапах выход на контакт, получение опросника, досбор анамнеза) """
    sheet = 'Crew'
    rows = [
        Lead.CreatedAt.Key
    ]
    cols = [
        ExcelClient.PivotCol(
            key=Lead.Responsible.Key
        )
    ]
    filters = [
        ExcelClient.PivotFilter(key=Lead.PipelineName.Key)
    ]
    values = [
        ExcelClient.PivotField(source=Lead.AtWorkAnyPipeline),
    ]
    group_function = ExcelClient.GroupFunction.by_weeks
    col_width = (
        ExcelClient.ColWidth.WeeksInterval,
    )


@dataclass()
class PivotReactionTime(PivotReactionTimeBase):
    """ Сводная таблица: время реакции """
    filters = [
        ExcelClient.PivotFilter(key=Lead.ReactionType.Key, selected=['outgoing_call']),
        ExcelClient.PivotFilter(key=Lead.CreationSource.Key, selected=['(blank)']),
        ExcelClient.PivotFilter(key=Lead.PipelineName.Key, selected=DEFAULT_PIPELINES),
        ExcelClient.PivotFilter(key=Lead.FirstSuccessfulIncomingCall.Key, selected=['(blank)']),
        ExcelClient.PivotFilter(key=Lead.Jivo.Key, selected=['(blank)']),
    ]


# @dataclass()
# class PivotCallbackTime(PivotCallbackTimeBase):
#     """ Сводная таблица: время реакции (обратные звонки) """
#     filters = [
#         ExcelClient.PivotFilter(key=Lead.ReactionType.Key, selected=[ReactionTimeBase.Field.OutgoingCall.value]),
#         ExcelClient.PivotFilter(key=Lead.PipelineName.Key, selected=DEFAULT_PIPELINES),
#         ExcelClient.PivotFilter(key=Lead.FirstSuccessfulIncomingCall.Key, selected=['(blank)']),
#     ]


@dataclass()
class PivotLeads(ExcelClient.PivotData):
    """ Сводная таблица: лиды """
    sheet = Lead.Stage.Lead.DisplayName
    rows = [Lead.CreatedAt.Key]
    values = [
        ExcelClient.PivotField(source=Lead.Stage.Lead),
        ExcelClient.PivotField(
            conversion_from=Lead.Stage.Lead,
            conversion_to=Lead.Stage.Target,
            conditional_formatting=ExcelClient.ConditionalFormatting.MaxIsGreen,
        ),
        ExcelClient.PivotField(source=Lead.Stage.Target),
        ExcelClient.PivotField(
            conversion_from=Lead.Stage.Target,
            conversion_to=Lead.Stage.Qualification,
            conditional_formatting=ExcelClient.ConditionalFormatting.MaxIsGreen,
        ),
        ExcelClient.PivotField(conversion_from=Lead.Stage.Lead, conversion_to=Lead.Stage.Qualification),
        ExcelClient.PivotField(source=Lead.Stage.Qualification),
        ExcelClient.PivotField(conversion_from=Lead.Stage.Qualification, conversion_to=Lead.Stage.PriorConsent),
        ExcelClient.PivotField(source=Lead.Stage.PriorConsent),
    ]
    filters = [
        ExcelClient.PivotFilter(key=Lead.LossReason.Key),
        ExcelClient.PivotFilter(key=Lead.Utm.Medium.Key),
        ExcelClient.PivotFilter(key=Lead.PipelineName.Key, selected=DEFAULT_PIPELINES)
    ]
    group_function = ExcelClient.GroupFunction.by_weeks
    col_width = (
        ExcelClient.ColWidth.WeeksInterval,
        8,
        8,
        8,
        8,
        8,
        8,
        8
    )


# @dataclass()
# class PivotReactionTimeIncoming(ExcelClient.PivotData):
#     """ Сводная таблица: время реакции """
#     sheet = 'Incoming'
#     rows = [Lead.CreatedAt.Key, Lead.Language.Key]
#     values = [
#         # сырые лиды
#         ExcelClient.PivotField(source=Lead.Stage.RawLead),
#         ExcelClient.PivotField(source=Lead.Stage.Lead),
#         # время реакции (+ %)
#         ExcelClient.PivotField(source=Lead.NoInteraction),
#         ExcelClient.PivotField(source=Lead.Outgoing),
#         ExcelClient.PivotField(source=Lead.Incoming),
#         ExcelClient.PivotField(
#             conversion_from=Lead.Incoming,
#             conversion_to=Lead.SlowReaction,
#             conditional_formatting=ExcelClient.ConditionalFormatting.MaxIsRed,
#         ),
#         ExcelClient.PivotField(source=Lead.SlowReaction),
#         ExcelClient.PivotField(
#             conversion_from=Lead.Incoming,
#             conversion_to=Lead.FastReaction,
#             conditional_formatting=ExcelClient.ConditionalFormatting.MaxIsGreen,
#         ),
#         ExcelClient.PivotField(source=Lead.FastReaction),
#         # время реакции в рабочее время (+ %)
#         ExcelClient.PivotField(source=Lead.IncomingOnDuty),
#         ExcelClient.PivotField(
#             conversion_from=Lead.IncomingOnDuty,
#             conversion_to=Lead.SlowReactionOnDuty,
#             conditional_formatting=ExcelClient.ConditionalFormatting.MaxIsRed,
#         ),
#         ExcelClient.PivotField(source=Lead.SlowReactionOnDuty),
#         ExcelClient.PivotField(
#             conversion_from=Lead.IncomingOnDuty,
#             conversion_to=Lead.FastReactionOnDuty,
#             conditional_formatting=ExcelClient.ConditionalFormatting.MaxIsGreen,
#         ),
#         ExcelClient.PivotField(source=Lead.FastReactionOnDuty),
#         # без реакции
#         ExcelClient.PivotField(
#             conversion_from=Lead.Incoming,
#             conversion_to=Lead.NoReaction,
#             conditional_formatting=ExcelClient.ConditionalFormatting.MaxIsRed,
#         ),
#         ExcelClient.PivotField(source=Lead.NoReaction),
#         ExcelClient.PivotField(
#             conversion_from=Lead.IncomingOnDuty,
#             conversion_to=Lead.NoReactionOnDuty,
#             conditional_formatting=ExcelClient.ConditionalFormatting.MaxIsRed,
#         ),
#         ExcelClient.PivotField(source=Lead.NoReactionOnDuty),
#     ]
#     filters = [
#         ExcelClient.PivotFilter(key=Lead.LossReason.Key),
#         ExcelClient.PivotFilter(key=Lead.Utm.Medium.Key),
#         ExcelClient.PivotFilter(key=Lead.PipelineName.Key, selected=DEFAULT_PIPELINES)
#     ]
#     group_function = ExcelClient.GroupFunction.by_weeks
#     col_width = (
#         ExcelClient.ColWidth.WeeksInterval,
#         5.43,
#         5.29,
#         10,
#         8.24,
#         8.71,
#         10.71,
#         8,
#         10.71,
#         8,
#         8.43,
#         12.71,
#         9.29,
#         12.71,
#         9.29,
#         10.57,
#         8,
#         15,
#         8,
#     )
#
#
# @dataclass()
# class PivotReactionTimeOutgoing(ExcelClient.PivotData):
#     """ Сводная таблица: время реакции """
#     sheet = 'Outgoing'
#     rows = [Lead.CreatedAt.Key, Lead.Language.Key]
#     values = [
#         # сырые лиды
#         ExcelClient.PivotField(source=Lead.Stage.RawLead),
#         ExcelClient.PivotField(source=Lead.Stage.Lead),
#         # время реакции
#         # ExcelClient.PivotField(source=Lead.NoInteraction),
#         # ExcelClient.PivotField(source=Lead.Outgoing),
#         # ExcelClient.PivotField(source=Lead.Incoming),
#         # ExcelClient.PivotField(
#         #     conversion_from=Lead.Outgoing,
#         #     conversion_to=Lead.SlowOutgoingReaction,
#         #     conditional_formatting=ExcelClient.ConditionalFormatting.MaxIsRed,
#         # ),
#         # ExcelClient.PivotField(source=Lead.SlowOutgoingReaction),
#         # ExcelClient.PivotField(
#         #     conversion_from=Lead.Outgoing,
#         #     conversion_to=Lead.FastOutgoingReaction,
#         #     conditional_formatting=ExcelClient.ConditionalFormatting.MaxIsGreen,
#         # ),
#         # ExcelClient.PivotField(source=Lead.FastOutgoingReaction),
#         # # ExcelClient.PivotField(
#         # #     conversion_from=Lead.Outgoing,
#         # #     conversion_to=Lead.OutgoingProblem,
#         # #     conditional_formatting=ExcelClient.ConditionalFormatting.MaxIsRed,
#         # # ),
#         # # ExcelClient.PivotField(source=Lead.OutgoingProblem),
#         # # 2 минуты
#         # ExcelClient.PivotField(
#         #     conversion_from=Lead.Outgoing,
#         #     conversion_to=Lead.SlowOutgoingReactionVOIP2,
#         #     conditional_formatting=ExcelClient.ConditionalFormatting.MaxIsRed,
#         # ),
#         # ExcelClient.PivotField(source=Lead.SlowOutgoingReactionVOIP2),
#         # ExcelClient.PivotField(
#         #     conversion_from=Lead.Outgoing,
#         #     conversion_to=Lead.FastOutgoingReactionVOIP2,
#         #     conditional_formatting=ExcelClient.ConditionalFormatting.MaxIsGreen,
#         # ),
#         # ExcelClient.PivotField(source=Lead.FastOutgoingReactionVOIP2),
#         # # 5 минут
#         # ExcelClient.PivotField(
#         #     conversion_from=Lead.Outgoing,
#         #     conversion_to=Lead.SlowOutgoingReactionVOIP5,
#         #     conditional_formatting=ExcelClient.ConditionalFormatting.MaxIsRed,
#         # ),
#         # ExcelClient.PivotField(source=Lead.SlowOutgoingReactionVOIP5),
#         # ExcelClient.PivotField(
#         #     conversion_from=Lead.Outgoing,
#         #     conversion_to=Lead.FastOutgoingReactionVOIP5,
#         #     conditional_formatting=ExcelClient.ConditionalFormatting.MaxIsGreen,
#         # ),
#         # ExcelClient.PivotField(source=Lead.FastOutgoingReactionVOIP5),
#         # # 60 минут
#         # ExcelClient.PivotField(
#         #     conversion_from=Lead.Outgoing,
#         #     conversion_to=Lead.SlowOutgoingReactionVOIP60,
#         #     conditional_formatting=ExcelClient.ConditionalFormatting.MaxIsRed,
#         # ),
#         # ExcelClient.PivotField(source=Lead.SlowOutgoingReactionVOIP60),
#         # ExcelClient.PivotField(
#         #     conversion_from=Lead.Outgoing,
#         #     conversion_to=Lead.FastOutgoingReactionVOIP60,
#         #     conditional_formatting=ExcelClient.ConditionalFormatting.MaxIsGreen,
#         # ),
#         # ExcelClient.PivotField(source=Lead.FastOutgoingReactionVOIP60),
#         # ExcelClient.PivotField(
#         #     conversion_from=Lead.Outgoing,
#         #     conversion_to=Lead.OutgoingProblemVOIP,
#         #     conditional_formatting=ExcelClient.ConditionalFormatting.MaxIsRed,
#         # ),
#         # ExcelClient.PivotField(source=Lead.OutgoingProblemVOIP),
#     ]
#     filters = [
#         ExcelClient.PivotFilter(key=Lead.LossReason.Key),
#         ExcelClient.PivotFilter(key=Lead.Utm.Medium.Key),
#         ExcelClient.PivotFilter(key=Lead.PipelineName.Key, selected=DEFAULT_PIPELINES)
#     ]
#     group_function = ExcelClient.GroupFunction.by_weeks
#     col_width = (
#         ExcelClient.ColWidth.WeeksInterval,
#         5.43,
#         5.29,
#         10,
#         8.24,
#         8.71,
#         10.71,
#         8,
#         10.71,
#         8,
#         8.43,
#         12.71,
#         9.29,
#         12.71,
#         9.29,
#         10.57,
#         8,
#         15,
#         8,
#     )


@dataclass()
class PivotPriorConsent(ExcelClient.PivotData):
    """ Сводная таблица: предварительное согласие """
    sheet = Lead.Stage.PriorConsent.DisplayName
    rows = [Lead.DateOfPriorConsent.Key, Lead.Link.Key]
    filters = [
        ExcelClient.PivotFilter(key=Lead.PipelineName.Key, selected=DEFAULT_PIPELINES)
    ]
    values = [
        ExcelClient.PivotField(source=Lead.Stage.PriorConsent),
        ExcelClient.PivotField(
            key=Lead.Stage.PriorConsent.Price,
            conditional_formatting=ExcelClient.ConditionalFormatting.MaxIsGreen,
            number_format=ExcelClient.NumberFormat.Euro,
            displayed_name=PRICE.title()
        )
    ]
    group_function = ExcelClient.GroupFunction.by_weeks
    col_width = (
        ExcelClient.ColWidth.WeeksInterval,
        7.71,
        ExcelClient.ColWidth.Price
    )


@dataclass()
class PivotDateOfSale(ExcelClient.PivotData):
    """ Сводная таблица: даты продаж """
    sheet = 'Date of Sale'
    rows = [Lead.DateOfSale.Key, Lead.Language.Key]
    filters = [
        ExcelClient.PivotFilter(key=Lead.PipelineName.Key, selected=DEFAULT_PIPELINES)
    ]
    values = [
        ExcelClient.PivotField(
            conditional_formatting=ExcelClient.ConditionalFormatting.MaxIsGreen,
            source=Lead.Stage.WaitingAtClinic,
        ),
        ExcelClient.PivotField(
            key=Lead.Stage.WaitingAtClinic.Price,
            number_format=ExcelClient.NumberFormat.Euro,
            displayed_name=PRICE.title()
        )
    ]
    group_function = ExcelClient.GroupFunction.by_weeks
    col_width = (
        ExcelClient.ColWidth.WeeksInterval,
        7.43,
        ExcelClient.ColWidth.Price
    )


@dataclass()
class PivotTreatment(ExcelClient.PivotData):
    """ Сводная таблица: даты лечения """
    sheet = Lead.Stage.Treatment.DisplayName
    rows = [Lead.DateOfAdmission.Key, Lead.Country.Key, Lead.Treatment.Key, Lead.Clinic.Key, Lead.Language.Key]
    filters = [
        ExcelClient.PivotFilter(key=Lead.PipelineName.Key, selected=DEFAULT_PIPELINES)
    ]
    values = [
        ExcelClient.PivotField(
            key=Lead.Stage.Treatment.Key,
            conditional_formatting=ExcelClient.ConditionalFormatting.MaxIsGreen,
            displayed_name=Lead.Stage.Treatment.DisplayName
        ),
        ExcelClient.PivotField(
            key=Lead.Stage.Treatment.Price,
            number_format=ExcelClient.NumberFormat.Euro,
            displayed_name=PRICE.title()
        ),
        ExcelClient.PivotField(
            key=Lead.Stage.Treatment.Price,
            number_format=ExcelClient.NumberFormat.Euro,
            displayed_name='Avrg. price',
            consolidation_function=ExcelClient.ConsolidationFunction.Average
        ),
        ExcelClient.PivotField(
            key=Lead.Upsale.Key,
            number_format=ExcelClient.NumberFormat.Euro,
            displayed_name=Lead.Upsale.DisplayName
        ),
    ]
    group_function = ExcelClient.GroupFunction.by_weeks
    col_width = (
        ExcelClient.ColWidth.WeeksInterval,
        10,
        ExcelClient.ColWidth.Price
    )


@dataclass()
class PivotGeneral(ExcelClient.PivotData):
    """ Сводная таблица: общая """
    sheet = 'General'
    rows = [Lead.CreatedAt.Key, Lead.Country.Key]
    filters = [
        ExcelClient.PivotFilter(key=Lead.PipelineName.Key, selected=DEFAULT_PIPELINES),
        ExcelClient.PivotFilter(key=Lead.Language.Key),
        ExcelClient.PivotFilter(key=Lead.LossReason.Key),
        ExcelClient.PivotFilter(key=Lead.Treatment.Key)
    ]
    values = [
        ExcelClient.PivotField(source=Lead.Stage.Lead),
        ExcelClient.PivotField(conversion_from=Lead.Stage.Lead, conversion_to=Lead.Stage.Target),
        ExcelClient.PivotField(source=Lead.Stage.Target),
        ExcelClient.PivotField(conversion_from=Lead.Stage.Target, conversion_to=Lead.Stage.Qualification),
        ExcelClient.PivotField(conversion_from=Lead.Stage.Lead, conversion_to=Lead.Stage.Qualification),
        ExcelClient.PivotField(source=Lead.Stage.Qualification),
        ExcelClient.PivotField(conversion_from=Lead.Stage.Qualification, conversion_to=Lead.Stage.PriorConsent),
        ExcelClient.PivotField(source=Lead.Stage.PriorConsent),
        ExcelClient.PivotField(conversion_from=Lead.Stage.PriorConsent, conversion_to=Lead.Stage.Treatment),
        ExcelClient.PivotField(source=Lead.Stage.Treatment),
        ExcelClient.PivotField(
            key=Lead.Stage.Treatment.Price,
            number_format=ExcelClient.NumberFormat.Euro,
            displayed_name=f'{Lead.Stage.Treatment.DisplayName} {PRICE}'
        ),
        ExcelClient.PivotField(conversion_from=Lead.Stage.Lead, conversion_to=Lead.Stage.Treatment),
        ExcelClient.PivotField(conversion_from=Lead.Stage.Qualification, conversion_to=Lead.Stage.Treatment),

        ExcelClient.PivotField(source=Lead.IncomingCallDuration),
        ExcelClient.PivotField(source=Lead.OutgoingCallAttempt),
        ExcelClient.PivotField(source=Lead.OutgoingCallQuantity),
        ExcelClient.PivotField(source=Lead.OutgoingCallDuration),
        ExcelClient.PivotField(source=Lead.IncomingChatQuantity),
        ExcelClient.PivotField(source=Lead.IncomingEmailQuantity),
        ExcelClient.PivotField(source=Lead.OutgoingChatQuantity),
        ExcelClient.PivotField(source=Lead.OutgoingEmailQuantity),

        # ExcelClient.PivotField(conversion_from=Lead.Stage.PriorConsent, conversion_to=Lead.Stage.WaitingAtClinic),
        # ExcelClient.PivotField(source=Lead.Stage.WaitingAtClinic),
        # ExcelClient.PivotField(
        #     key=Lead.Stage.WaitingAtClinic.Price,
        #     number_format=ExcelClient.NumberFormat.Euro,
        #     displayed_name=f'{Lead.Stage.WaitingAtClinic.DisplayName} {PRICE}'
        # ),
        # ExcelClient.PivotField(conversion_from=Lead.Stage.WaitingAtClinic, conversion_to=Lead.Stage.Treatment),
        # ExcelClient.PivotField(conversion_from=Lead.Stage.Qualification, conversion_to=Lead.Stage.Treatment),
        # ExcelClient.PivotField(source=Lead.Stage.Treatment),
        # ExcelClient.PivotField(
        #     key=Lead.Stage.Treatment.Price,
        #     number_format=ExcelClient.NumberFormat.Euro,
        #     displayed_name=f'{Lead.Stage.Treatment.DisplayName} {PRICE}'
        # ),
        # ExcelClient.PivotField(conversion_from=Lead.Stage.Qualification, conversion_to=Lead.Stage.Purchase),
        # ExcelClient.PivotField(source=Lead.Stage.Purchase),
        # ExcelClient.PivotField(
        #     key=Lead.Stage.Purchase.Price,
        #     number_format=ExcelClient.NumberFormat.Euro,
        #     displayed_name=f'{Lead.Stage.Purchase.DisplayName} {PRICE}'
        # ),
    ]
    group_function = ExcelClient.GroupFunction.by_weeks
    col_width = (
        ExcelClient.ColWidth.WeeksInterval,
        6.43,
        7.71,
        5,
        7.86,
        7.43,
        ExcelClient.ColWidth.Price,
        10.14,
        7.29,
        ExcelClient.ColWidth.Price,
        9.57,
        11.43,
        10,
        ExcelClient.ColWidth.Price,
        12.29,
        8.71,
        ExcelClient.ColWidth.Price
    )


@dataclass()
class PivotCommunications(ExcelClient.PivotData):
    """ Сводная таблица: коммуникации """
    sheet = 'Communications'
    rows = [Lead.CreatedAt.Key, Lead.Country.Key]
    cols = [ExcelClient.PivotCol(key=Lead.ReachedStage.Key)]
    filters = [
        ExcelClient.PivotFilter(key=Lead.PipelineName.Key, selected=DEFAULT_PIPELINES),
        ExcelClient.PivotFilter(key=Lead.Language.Key),
        ExcelClient.PivotFilter(key=Lead.LossReason.Key),
        ExcelClient.PivotFilter(key=Lead.Treatment.Key)
    ]
    values = [
        ExcelClient.PivotField(source=Lead.IncomingCallDuration),
        ExcelClient.PivotField(source=Lead.OutgoingCallAttempt),
        ExcelClient.PivotField(source=Lead.OutgoingCallQuantity),
        ExcelClient.PivotField(source=Lead.OutgoingCallDuration),
        ExcelClient.PivotField(source=Lead.IncomingChatQuantity),
        ExcelClient.PivotField(source=Lead.IncomingEmailQuantity),
        ExcelClient.PivotField(source=Lead.OutgoingChatQuantity),
        ExcelClient.PivotField(source=Lead.OutgoingEmailQuantity),
    ]
    group_function = ExcelClient.GroupFunction.by_weeks
    col_width = (
        ExcelClient.ColWidth.WeeksInterval,
        6.43,
        7.71,
        5,
        7.86,
        7.43,
        ExcelClient.ColWidth.Price,
        10.14,
        7.29,
        ExcelClient.ColWidth.Price,
        9.57,
        11.43,
        10,
        ExcelClient.ColWidth.Price,
        12.29,
        8.71,
        ExcelClient.ColWidth.Price
    )


@dataclass()
class PivotGeneralSE(PivotGeneral):
    """ Сводная таблица: общая """
    sheet = 'General_SE'
    filters = [
        ExcelClient.PivotFilter(key=Lead.PipelineName.Key, selected=['New_patients_general_SE']),
        ExcelClient.PivotFilter(key=Lead.StatusName.Key)
    ]


@dataclass()
class PivotGeneralEN(PivotGeneral):
    """ Сводная таблица: Английская зона """
    sheet = 'General_EN'
    filters = [
        ExcelClient.PivotFilter(key=Lead.PipelineName.Key, selected=['New_patients_ENG']),
        ExcelClient.PivotFilter(key=Lead.StatusName.Key)
    ]


@dataclass()
class PivotGeneralFR(PivotGeneral):
    """ Сводная таблица: Франция """
    sheet = 'General_FR'
    filters = [
        ExcelClient.PivotFilter(key=Lead.PipelineName.Key, selected=['New_patients_FR']),
        ExcelClient.PivotFilter(key=Lead.StatusName.Key)
    ]


@dataclass()
class PivotGeneralIT(PivotGeneral):
    """ Сводная таблица: Италия """
    sheet = 'General_IT'
    filters = [
        ExcelClient.PivotFilter(key=Lead.PipelineName.Key, selected=['New_patients_IT']),
        ExcelClient.PivotFilter(key=Lead.StatusName.Key)
    ]


@dataclass()
class PivotGeneralGE(PivotGeneral):
    """ Сводная таблица: Германия """
    sheet = 'General_GE'
    filters = [
        ExcelClient.PivotFilter(key=Lead.PipelineName.Key, selected=['New_patients_GE']),
        ExcelClient.PivotFilter(key=Lead.StatusName.Key)
    ]


class PivotFunnel(ExcelClient.PivotData):
    """ Сводная таблица: чистая воронка """
    sheet = 'Funnel'
    rows = [Lead.CreatedAt.Key, Lead.Treatment.Key, Lead.Country.Key, Lead.Responsible.Key]
    filters = [
        ExcelClient.PivotFilter(key=Lead.PipelineName.Key, selected=DEFAULT_PIPELINES),
        ExcelClient.PivotFilter(key=Lead.StatusName.Key)
    ]
    values = [
        ExcelClient.PivotField(source=Lead.Stage.RawLead),
        ExcelClient.PivotField(source=Lead.Stage.Lead),
        ExcelClient.PivotField(source=Lead.Stage.Target),
        ExcelClient.PivotField(source=Lead.Stage.SchedulingConsultation),
        ExcelClient.PivotField(source=Lead.Stage.WaitingForConsultation),
        ExcelClient.PivotField(source=Lead.Stage.DiscussionOfTreatment),
        ExcelClient.PivotField(source=Lead.Stage.LongNegotiations),
        ExcelClient.PivotField(source=Lead.Stage.Qualification),
        ExcelClient.PivotField(source=Lead.Stage.PriorConsent),
        ExcelClient.PivotField(source=Lead.Stage.WaitingAtClinic),
        ExcelClient.PivotField(source=Lead.Stage.Treatment),
        ExcelClient.PivotField(source=Lead.Stage.Purchase),
        # ExcelClient.PivotField(source=Lead.CallDuration30),
        # ExcelClient.PivotField(source=Lead.CallDuration120),
        # ExcelClient.PivotField(source=Lead.CallDuration180),
        # ExcelClient.PivotField(source=Lead.CallDuration240),
        # ExcelClient.PivotField(source=Lead.CallDuration300),
    ]
    group_function = ExcelClient.GroupFunction.by_weeks
    col_width = (
        ExcelClient.ColWidth.WeeksInterval,
        6.43,
        7.71,
        5,
        7.86,
        7.43,
        ExcelClient.ColWidth.Price,
        10.14,
        7.29,
        ExcelClient.ColWidth.Price,
        9.57,
        11.43,
        10,
        ExcelClient.ColWidth.Price,
        12.29,
        8.71,
        ExcelClient.ColWidth.Price
    )


class PivotCalls(ExcelClient.PivotData):
    """ Сводная таблица: звонки """
    sheet = 'Calls'
    rows = [Lead.CreatedAt.Key, Lead.LongestCallLink.Key]
    filters = [
        ExcelClient.PivotFilter(key=Lead.PipelineName.Key, selected=DEFAULT_PIPELINES),
        ExcelClient.PivotFilter(key=Lead.StatusName.Key)
    ]
    values = [
        ExcelClient.PivotField(source=Lead.Stage.RawLead),
        ExcelClient.PivotField(source=Lead.Stage.Lead),
        ExcelClient.PivotField(source=Lead.Stage.Target),
        ExcelClient.PivotField(source=Lead.Stage.Qualification),
        ExcelClient.PivotField(conversion_from=Lead.Stage.Qualification, conversion_to=Lead.Stage.PriorConsent),
        ExcelClient.PivotField(source=Lead.Stage.PriorConsent),
        ExcelClient.PivotField(
            source=Lead.LongestCallDuration,
            displayed_name=f'Avrg. {Lead.LongestCallDuration.DisplayName}, sec.',
            consolidation_function=ExcelClient.ConsolidationFunction.Average,
            number_format=ExcelClient.NumberFormat.Number,
            conditional_formatting=ExcelClient.ConditionalFormatting.MaxIsGreen
        ),
        # ExcelClient.PivotField(source=Lead.CallDuration0),
        # ExcelClient.PivotField(source=Lead.CallDuration120),
        # ExcelClient.PivotField(source=Lead.CallDuration180),
        # ExcelClient.PivotField(source=Lead.CallDuration240),
        # ExcelClient.PivotField(source=Lead.CallDuration300),
    ]
    group_function = ExcelClient.GroupFunction.by_weeks
    col_width = (
        ExcelClient.ColWidth.WeeksInterval,
        6.43,
        7.71,
        5,
        7.86,
        7.43,
        ExcelClient.ColWidth.Price,
        10.14,
        7.29,
        ExcelClient.ColWidth.Price,
        9.57,
        11.43,
        10,
        ExcelClient.ColWidth.Price,
        12.29,
        8.71,
        ExcelClient.ColWidth.Price
    )


@dataclass()
class PivotGraphTreatment(ExcelClient.PivotData):
    """ Сводная таблица: график по направлениям лечения """
    sheet = 'gr_treatment'
    rows = [Lead.Treatment.Key, Lead.CreatedAt.Key]
    filters = [
        ExcelClient.PivotFilter(key=Lead.Treatment.Key,),
        ExcelClient.PivotFilter(key=Lead.PipelineName.Key)
    ]
    values = [
        ExcelClient.PivotField(source=Lead.Stage.Lead),
        ExcelClient.PivotField(source=Lead.Stage.Target),
        ExcelClient.PivotField(source=Lead.Stage.Qualification),
        ExcelClient.PivotField(source=Lead.Stage.PriorConsent),
        ExcelClient.PivotField(source=Lead.Stage.WaitingAtClinic),
        ExcelClient.PivotField(source=Lead.Stage.Treatment),
        ExcelClient.PivotField(source=Lead.Stage.Purchase),
    ]
    group_function = ExcelClient.GroupFunction.by_months
    graph = True
    col_width = (
        ExcelClient.ColWidth.WeeksInterval,
        6.43,
        7.71,
        5,
        7.86,
        7.43,
        ExcelClient.ColWidth.Price,
        10.14,
        7.29,
        ExcelClient.ColWidth.Price,
        9.57,
        11.43,
        10,
        ExcelClient.ColWidth.Price,
        12.29,
        8.71,
        ExcelClient.ColWidth.Price
    )


@dataclass()
class PivotGraphResponsible(ExcelClient.PivotData):
    """ Сводная таблица: график по ответственным """
    sheet = 'gr_responsible'
    rows = [Lead.Responsible.Key, Lead.CreatedAt.Key]
    filters = [
        ExcelClient.PivotFilter(key=Lead.Responsible.Key,),
        ExcelClient.PivotFilter(key=Lead.PipelineName.Key)
    ]
    values = [
        ExcelClient.PivotField(source=Lead.Stage.Lead),
        ExcelClient.PivotField(source=Lead.Stage.Target),
        ExcelClient.PivotField(source=Lead.Stage.Qualification),
        ExcelClient.PivotField(source=Lead.Stage.PriorConsent),
        ExcelClient.PivotField(source=Lead.Stage.WaitingAtClinic),
        ExcelClient.PivotField(source=Lead.Stage.Treatment),
        ExcelClient.PivotField(source=Lead.Stage.Purchase),
    ]
    group_function = ExcelClient.GroupFunction.by_months
    graph = True
    col_width = (
        ExcelClient.ColWidth.WeeksInterval,
        6.43,
        7.71,
        5,
        7.86,
        7.43,
        ExcelClient.ColWidth.Price,
        10.14,
        7.29,
        ExcelClient.ColWidth.Price,
        9.57,
        11.43,
        10,
        ExcelClient.ColWidth.Price,
        12.29,
        8.71,
        ExcelClient.ColWidth.Price
    )


@dataclass()
class PivotGraphResponsibleRelative(ExcelClient.PivotData):
    """ Сводная таблица: график по ответственным (%) """
    sheet = 'gr_responsible_relative'
    rows = [Lead.Responsible.Key, Lead.CreatedAt.Key]
    filters = [
        ExcelClient.PivotFilter(key=Lead.Responsible.Key,),
        ExcelClient.PivotFilter(key=Lead.PipelineName.Key)
    ]
    values = [
        ExcelClient.PivotField(conversion_from=Lead.Stage.Target, conversion_to=Lead.Stage.Qualification),
        ExcelClient.PivotField(conversion_from=Lead.Stage.Target, conversion_to=Lead.Stage.PriorConsent),
    ]
    group_function = ExcelClient.GroupFunction.by_months
    # first_data_row = 6
    graph = True
    col_width = (
        ExcelClient.ColWidth.WeeksInterval,
        6.43,
        7.71,
        5,
        7.86,
        7.43,
        ExcelClient.ColWidth.Price,
        10.14,
        7.29,
        ExcelClient.ColWidth.Price,
        9.57,
        11.43,
        10,
        ExcelClient.ColWidth.Price,
        12.29,
        8.71,
        ExcelClient.ColWidth.Price
    )


@dataclass()
class PivotGraphCountry(ExcelClient.PivotData):
    """ Сводная таблица: график по странам """
    sheet = 'gr_country'
    rows = [Lead.Country.Key, Lead.CreatedAt.Key]
    filters = [
        ExcelClient.PivotFilter(key=Lead.Country.Key,),
        ExcelClient.PivotFilter(key=Lead.PipelineName.Key)
    ]
    values = [
        ExcelClient.PivotField(source=Lead.Stage.Lead),
        ExcelClient.PivotField(source=Lead.Stage.Target),
        ExcelClient.PivotField(source=Lead.Stage.Qualification),
        ExcelClient.PivotField(source=Lead.Stage.PriorConsent),
        ExcelClient.PivotField(source=Lead.Stage.WaitingAtClinic),
        ExcelClient.PivotField(source=Lead.Stage.Treatment),
        ExcelClient.PivotField(source=Lead.Stage.Purchase),
    ]
    group_function = ExcelClient.GroupFunction.by_months
    graph = True
    col_width = (
        ExcelClient.ColWidth.WeeksInterval,
        6.43,
        7.71,
        5,
        7.86,
        7.43,
        ExcelClient.ColWidth.Price,
        10.14,
        7.29,
        ExcelClient.ColWidth.Price,
        9.57,
        11.43,
        10,
        ExcelClient.ColWidth.Price,
        12.29,
        8.71,
        ExcelClient.ColWidth.Price
    )


@dataclass()
class PivotSuccess(ExcelClient.PivotData):
    """ Сводная таблица: успешные сделки """
    sheet = Lead.Stage.Purchase.DisplayName
    rows = [Lead.DateOfSale.Key, Lead.Responsible.Key]
    filters = [
        ExcelClient.PivotFilter(key=Lead.Stage.Treatment.Key)
    ]
    values = [
        ExcelClient.PivotField(source=Lead.Stage.Lead),
        ExcelClient.PivotField(
            key=Lead.Stage.Purchase.Price,
            number_format=ExcelClient.NumberFormat.Euro,
            displayed_name=f'{Lead.Stage.Purchase.DisplayName} {PRICE}'
        )
    ]
    group_function = ExcelClient.GroupFunction.by_weeks
    col_width = (
        ExcelClient.ColWidth.WeeksInterval,
        6.43,
        ExcelClient.ColWidth.Price
    )


@dataclass()
class PivotManagers(ExcelClient.PivotData):
    """ Сводная таблица: менеджеры """
    sheet = 'Managers'
    rows = [Lead.CreatedAt.Key, Lead.PipelineName.Key, Lead.Country.Key, Lead.Language.Key, Lead.Link.Key]
    cols = [Lead.Responsible.Key]
    values = [
        ExcelClient.PivotField(source=Lead.Stage.Qualification),
        ExcelClient.PivotField(source=Lead.Stage.Lead),
        ExcelClient.PivotField(conversion_from=Lead.Stage.Lead, conversion_to=Lead.Stage.Qualification)
    ]
    group_function = ExcelClient.GroupFunction.by_weeks
    col_width = (
        ExcelClient.ColWidth.WeeksInterval,
    )


@dataclass()
class PivotLeadsMT(ExcelClient.PivotData):
    """ Сводная таблица: лиды Mental transformation """
    sheet = 'Leads MT'
    rows = [LeadMT.CreatedAt.Key]
    values = [
        ExcelClient.PivotField(source=LeadMT.Stage.Lead),
        ExcelClient.PivotField(
            conversion_from=LeadMT.Stage.Lead,
            conversion_to=LeadMT.Stage.Target,
            conditional_formatting=ExcelClient.ConditionalFormatting.MaxIsGreen,
        ),
        ExcelClient.PivotField(source=LeadMT.Stage.Target),
        # target and lead -> consult
        ExcelClient.PivotField(
            conversion_from=LeadMT.Stage.Target,
            conversion_to=LeadMT.Stage.SchedulingConsultation,
            conditional_formatting=ExcelClient.ConditionalFormatting.MaxIsGreen,
        ),
        ExcelClient.PivotField(conversion_from=LeadMT.Stage.Lead, conversion_to=LeadMT.Stage.SchedulingConsultation),
        ExcelClient.PivotField(source=LeadMT.Stage.SchedulingConsultation),
        # consult -> after consult
        ExcelClient.PivotField(
            conversion_from=LeadMT.Stage.SchedulingConsultation,
            conversion_to=LeadMT.Stage.AfterConsultation
        ),
        ExcelClient.PivotField(source=LeadMT.Stage.AfterConsultation),
        # target and lead -> consult
        ExcelClient.PivotField(
            conversion_from=LeadMT.Stage.Target,
            conversion_to=LeadMT.Stage.PaidConsultationAssignment,
            conditional_formatting=ExcelClient.ConditionalFormatting.MaxIsGreen,
        ),
        ExcelClient.PivotField(conversion_from=LeadMT.Stage.Lead, conversion_to=LeadMT.Stage.PaidConsultationAssignment),
        ExcelClient.PivotField(source=LeadMT.Stage.PaidConsultationAssignment),
        # paid consult -> after paid consult
        ExcelClient.PivotField(
            conversion_from=LeadMT.Stage.PaidConsultationAssignment,
            conversion_to=LeadMT.Stage.AfterPaidConsultation
        ),
        ExcelClient.PivotField(source=LeadMT.Stage.AfterPaidConsultation),
        # target -> prior consent
        ExcelClient.PivotField(conversion_from=LeadMT.Stage.Target, conversion_to=LeadMT.Stage.PriorConsent),
        ExcelClient.PivotField(source=Lead.Stage.PriorConsent),
    ]
    filters = [
        ExcelClient.PivotFilter(key=Lead.LossReason.Key),
        ExcelClient.PivotFilter(key=Lead.Utm.Medium.Key),
        ExcelClient.PivotFilter(key=Lead.PipelineName.Key, selected=['Mental transformation'])
    ]
    group_function = ExcelClient.GroupFunction.by_weeks
    col_width = (
        ExcelClient.ColWidth.WeeksInterval,
        8,
        8,
        8,
        8,
        8,
        8,
        8,
        8,
        8,
        8,
        8,
        8,
        8,
        8,
        8,
    )


@dataclass()
class PivotClusterTagsDeprecated(ExcelClient.PivotData):
    """ Сводная таблица: теги todo удалить, если новый отчет работает норм"""
    sheet = 'Tags'
    filters = [
        ExcelClient.PivotFilter(key=Lead.Treatment.Key),
        ExcelClient.PivotFilter(key=Lead.Country.Key),
        ExcelClient.PivotFilter(key=Lead.Language.Key),
        ExcelClient.PivotFilter(key=Lead.LossReason.Key),
        ExcelClient.PivotFilter(key=Lead.Responsible.Key),
    ]
    rows = ['title', 'date']
    values = [
        ExcelClient.PivotField(source=Lead.Stage.Target),
        ExcelClient.PivotField(
            key=f'{Lead.Stage.Target.DisplayName} -> {Lead.Stage.Qualification.DisplayName}',
            consolidation_function=ExcelClient.ConsolidationFunction.Average,
            number_format=ExcelClient.NumberFormat.Percent_2,
            conditional_formatting=ExcelClient.ConditionalFormatting.MaxIsGreen
        ),
        ExcelClient.PivotField(source=Lead.Stage.Qualification),
        ExcelClient.PivotField(
            key=f'{Lead.Stage.Target.DisplayName} -> {Lead.Stage.PriorConsent.DisplayName}',
            consolidation_function=ExcelClient.ConsolidationFunction.Average,
            number_format=ExcelClient.NumberFormat.Percent_2,
            conditional_formatting=ExcelClient.ConditionalFormatting.MaxIsGreen
        ),
        ExcelClient.PivotField(source=Lead.Stage.PriorConsent),
    ]
    group_function = ExcelClient.GroupFunction.by_weeks
    # first_data_row = 3
    col_width = (
        ExcelClient.ColWidth.WeeksInterval,
        8,
        8,
        8,
        8,
        8,
        8,
        8
    )


@dataclass()
class PivotClusterTags(ExcelClient.PivotData):
    """ Сводная таблица: теги """
    sheet = 'Tags'
    rows = ['title']
    cols = [ExcelClient.PivotCol(key='date')]
    values = [
        ExcelClient.PivotField(source=Lead.Stage.Lead),
        ExcelClient.PivotField(conversion_from=Lead.Stage.Lead, conversion_to=Lead.Stage.Qualification),
        ExcelClient.PivotField(source=Lead.Stage.Qualification),
        ExcelClient.PivotField(conversion_from=Lead.Stage.Qualification, conversion_to=Lead.Stage.PriorConsent),
        ExcelClient.PivotField(source=Lead.Stage.PriorConsent),
        ExcelClient.PivotField(source=Lead.Stage.WaitingAtClinic),
        ExcelClient.PivotField(
            conversion_from=Lead.Stage.Target,
            conversion_to=Lead.Stage.PriorConsent,
            consolidation_function=ExcelClient.ConsolidationFunction.Average
        ),
        ExcelClient.PivotField(conversion_from=Lead.Stage.Lead, conversion_to=Lead.Stage.PriorConsent),
    ]
    group_function = ExcelClient.GroupFunction.by_weeks
    # first_data_row = 3
    # col_width = (
    #     ExcelClient.ColWidth.WeeksInterval,
    #     8,
    #     8,
    #     8,
    #     8,
    #     8,
    #     8,
    #     8
    # )
