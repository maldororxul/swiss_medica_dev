""" Схема данных для сводной таблицы """
__author__ = 'ke.mizonov'

from dataclasses import dataclass
from app.amo.data.base.pivot_schema import (
    PivotReactionTime as PivotReactionTimeBase
)
from app.amo.data.sm.data_schema import LeadSM as Lead, LeadHA, LeadDiabetes
from utils.excel import ExcelClient

DEFAULT_AVERAGE_DEVIATION = (-0.1, 0.1)
DEFAULT_PIPELINES = ['French', 'German', 'Italian', 'Italy', 'Новые Клиенты']
BURN_OUT_USERS = ['Alex Hitch', 'Alexandra Newman', 'Darya Zorra', 'Ellen Bayliss', 'Helen Abra', 'Juli Manzetti',
                  'Karen Young', 'Manas', 'Nikola Djokovic', 'Olga Gelfer', 'Ollie Skomoroshko', 'Serg Proto',
                  'Tanya Blanchet', 'Victoria Bah', 'Василий Админ']
ALL_TREAMENT_EXCEPT_AUTISM = [
    "Amyotrophic Lateral Sclerosis / ALS",
    "Anti Aging",
    "Arterial Hypertension",
    "Arthritis / Arthrosis / Osteochondrosis",
    "Asthma / Allergies / Sinusitis",
    "Ataxia",
    "Bronchial asthma",
    "Cerebral Palsy",
    "Chronic back pain",
    "Chronic fatigue syndrome",
    "Chronic Kidney Failure (CKF)",
    "Conjunctive tissue",
    "COPD",
    "Crohn's Disease",
    "Dementia / Alzheimer Disease",
    "Diabetes Type 1",
    "Diabetes Type 2",
    "Eye problems",
    "Hair loss",
    "Hashimoto's disease",
    "Injury of CNS (brain, spinal cord)",
    "Liver Disease / Cirrhosis",
    "Lupus",
    "Lyme",
    "Male / Female infertility",
    "Motor Neurone Disease (MND)",
    "Multiple Sclerosis",
    "Obesity",
    "Other",
    "Parkinson Disease Treatment",
    "Peyronie’s disease",
    "Psoriasis",
    "Stroke",
    "Tinnitus",
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


@dataclass()
class PivotWeeklyBO(ExcelClient.PivotData):
    """ Сводная таблица: по неделям, burn out """
    sheet = 'BO'
    rows = [
        LeadHA.CreatedAt.Key,
        LeadHA.Tags.Key,
        LeadHA.Id.Key,
    ]
    filters = [
        ExcelClient.PivotFilter(key=LeadHA.Responsible.Key, selected=BURN_OUT_USERS),
        ExcelClient.PivotFilter(key=LeadHA.LossReason.Key),
        ExcelClient.PivotFilter(key=LeadHA.PipelineName.Key, selected=['Отель Александр']),
    ]
    values = [
        ExcelClient.PivotField(source=LeadHA.Stage.RawLead),
        ExcelClient.PivotField(source=LeadHA.Stage.Lead),
        # lead -> target
        ExcelClient.PivotField(conversion_from=LeadHA.Stage.Lead, conversion_to=LeadHA.Stage.Target),
        ExcelClient.PivotField(source=LeadHA.Stage.Target),
        # lead -> qual
        ExcelClient.PivotField(conversion_from=LeadHA.Stage.Lead, conversion_to=LeadHA.Stage.Qualification),
        ExcelClient.PivotField(source=LeadHA.Stage.Qualification),
        # qual -> consultation
        ExcelClient.PivotField(conversion_from=LeadHA.Stage.Qualification, conversion_to=LeadHA.Stage.SchedulingConsultation),
        ExcelClient.PivotField(source=LeadHA.Stage.SchedulingConsultation),
        # consultation -> treatment preparations
        ExcelClient.PivotField(conversion_from=LeadHA.Stage.SchedulingConsultation, conversion_to=LeadHA.Stage.TreatmentPreparation),
        ExcelClient.PivotField(source=LeadHA.Stage.TreatmentPreparation),
        ExcelClient.PivotField(source=LeadHA.Stage.WaitingForReservation),
        # reservation -> arrival
        ExcelClient.PivotField(conversion_from=LeadHA.Stage.WaitingForReservation, conversion_to=LeadHA.Stage.WaitingForArrival),
        ExcelClient.PivotField(source=LeadHA.Stage.WaitingForArrival),
        # arrival -> treatment
        ExcelClient.PivotField(conversion_from=LeadHA.Stage.WaitingForArrival, conversion_to=LeadHA.Stage.Treatment),
        ExcelClient.PivotField(source=LeadHA.Stage.Treatment),
        ExcelClient.PivotField(source=LeadHA.Stage.Purchase),
        ExcelClient.PivotField(
            key=LeadHA.Stage.Purchase.Price,
            displayed_name=f'{LeadHA.Stage.Purchase.DisplayName} price',
            number_format=ExcelClient.NumberFormat.Euro
        ),

    ]
    group_function = ExcelClient.GroupFunction.by_weeks
    col_width = (
        ExcelClient.ColWidth.WeeksInterval,
        9.14,
        5.71,
        13.86,
        5.71,
        13.86,
        5.71,
        18.43,
        13,
        18.14,
        9.29,
        18.29,
        7.86
    )


@dataclass()
class PivotWeeklyDiabetes(ExcelClient.PivotData):
    """ Сводная таблица: по неделям, диабет """
    sheet = 'Diabetes'
    rows = [
        LeadDiabetes.CreatedAt.Key,
        LeadDiabetes.Tags.Key,
        LeadDiabetes.Id.Key,
    ]
    filters = [
        ExcelClient.PivotFilter(key=LeadDiabetes.Responsible.Key),
        ExcelClient.PivotFilter(key=LeadDiabetes.LossReason.Key),
        ExcelClient.PivotFilter(key=LeadDiabetes.PipelineName.Key, selected=['Диабет']),
        ExcelClient.PivotFilter(key=LeadDiabetes.Country.Key),
    ]
    values = [
        ExcelClient.PivotField(source=LeadDiabetes.Stage.RawLead),
        ExcelClient.PivotField(source=LeadDiabetes.Stage.Lead),
        # lead -> target
        ExcelClient.PivotField(conversion_from=LeadDiabetes.Stage.Lead, conversion_to=LeadDiabetes.Stage.Target),
        ExcelClient.PivotField(source=LeadDiabetes.Stage.Target),
        # lead -> qual
        ExcelClient.PivotField(
            conversion_from=LeadDiabetes.Stage.Target,
            conversion_to=LeadDiabetes.Stage.Qualification
        ),
        ExcelClient.PivotField(conversion_from=LeadDiabetes.Stage.Lead, conversion_to=LeadDiabetes.Stage.Qualification),
        ExcelClient.PivotField(source=LeadDiabetes.Stage.Qualification),
        # qual -> consultation
        ExcelClient.PivotField(
            conversion_from=LeadDiabetes.Stage.Qualification,
            conversion_to=LeadDiabetes.Stage.SchedulingConsultation
        ),
        ExcelClient.PivotField(source=LeadDiabetes.Stage.SchedulingConsultation),
        # consultation -> consultation analysis
        ExcelClient.PivotField(
            conversion_from=LeadDiabetes.Stage.SchedulingConsultation,
            conversion_to=LeadDiabetes.Stage.ConsultationAnalysis
        ),
        ExcelClient.PivotField(source=LeadDiabetes.Stage.ConsultationAnalysis),
        # consultation analysis -> treatment discussion
        ExcelClient.PivotField(
            conversion_from=LeadDiabetes.Stage.ConsultationAnalysis,
            conversion_to=LeadDiabetes.Stage.TreatmentDiscussion
        ),
        ExcelClient.PivotField(source=LeadDiabetes.Stage.TreatmentDiscussion),
        # treatment discussion -> waiting for reservation
        ExcelClient.PivotField(
            conversion_from=LeadDiabetes.Stage.TreatmentDiscussion,
            conversion_to=LeadDiabetes.Stage.WaitingForReservation
        ),
        ExcelClient.PivotField(source=LeadDiabetes.Stage.WaitingForReservation),
        # waiting for reservation -> waiting for arrival
        ExcelClient.PivotField(
            conversion_from=LeadDiabetes.Stage.WaitingForReservation,
            conversion_to=LeadDiabetes.Stage.WaitingForArrival
        ),
        ExcelClient.PivotField(source=LeadDiabetes.Stage.WaitingForArrival),
        # waiting for arrival -> treatment
        ExcelClient.PivotField(
            conversion_from=LeadDiabetes.Stage.WaitingForArrival,
            conversion_to=LeadDiabetes.Stage.Treatment
        ),
        ExcelClient.PivotField(source=LeadDiabetes.Stage.Treatment),
        # qual -> purchase
        ExcelClient.PivotField(
            conversion_from=LeadDiabetes.Stage.Qualification,
            conversion_to=LeadDiabetes.Stage.Purchase,
            target_value=.04,
            conditional_formatting=ExcelClient.ConditionalFormatting.MaxIsGreen
        ),
        ExcelClient.PivotField(source=LeadDiabetes.Stage.Purchase),
        ExcelClient.PivotField(
            key=LeadDiabetes.Stage.Purchase.Price,
            displayed_name=f'{LeadDiabetes.Stage.Purchase.DisplayName} price',
            number_format=ExcelClient.NumberFormat.Euro
        ),

    ]
    group_function = ExcelClient.GroupFunction.by_weeks
    col_width = (
        ExcelClient.ColWidth.WeeksInterval,
        9.14,
        5.71,
        13.86,
        5.71,
        13.86,
        5.71,
        18.43,
        13,
        18.14,
        9.29,
        18.29,
        7.86
    )


@dataclass()
class PivotWeeklyAll(ExcelClient.PivotData):
    """ Сводная таблица: по неделям, все """
    sheet = 'SM All (week)'
    rows = [
        Lead.CreatedAt.Key,
    ]
    filters = [
        ExcelClient.PivotFilter(key=Lead.PipelineName.Key, selected=DEFAULT_PIPELINES),
        ExcelClient.PivotFilter(key=Lead.Responsible.Key),
        ExcelClient.PivotFilter(key=Lead.Agent.Key, selected=['(blank)']),
        ExcelClient.PivotFilter(key=Lead.Treatment.Key),
    ]
    values = [
        ExcelClient.PivotField(source=Lead.Stage.RawLead),
        ExcelClient.PivotField(source=Lead.Stage.Lead),
        # lead -> target
        ExcelClient.PivotField(
            conversion_from=Lead.Stage.Lead,
            conversion_to=Lead.Stage.Target,
            analysis=ExcelClient.Analysis(
                average_deviation=DEFAULT_AVERAGE_DEVIATION,
                line_num=-1
            )
        ),
        ExcelClient.PivotField(source=Lead.Stage.Target),
        # lead -> qual
        ExcelClient.PivotField(conversion_from=Lead.Stage.Lead, conversion_to=Lead.Stage.Qualification),
        ExcelClient.PivotField(source=Lead.Stage.Qualification),
        # qual -> quest
        ExcelClient.PivotField(
            conversion_from=Lead.Stage.Qualification,
            conversion_to=Lead.QuestionnaireRecieved7Days,
            # target_value='all: 25%, autism: 20%',
            conditional_formatting=ExcelClient.ConditionalFormatting.MaxIsGreen,
            analysis=ExcelClient.Analysis(
                average_deviation=DEFAULT_AVERAGE_DEVIATION,
                line_num=-2
            )
        ),
        ExcelClient.PivotField(source=Lead.QuestionnaireRecieved7Days),
        # qual -> offer
        ExcelClient.PivotField(
            conversion_from=Lead.Stage.Qualification,
            conversion_to=Lead.OfferSent14Days,
            # target_value='all: 8%',
            conditional_formatting=ExcelClient.ConditionalFormatting.MaxIsGreen
        ),
        ExcelClient.PivotField(source=Lead.OfferSent14Days),
        ExcelClient.PivotField(
            source=Lead.OfferSendingSpeed,
            consolidation_function=ExcelClient.ConsolidationFunction.Average,
            number_format=ExcelClient.NumberFormat.Number
        ),
        # qual -> prior
        ExcelClient.PivotField(
            conversion_from=Lead.Stage.Qualification,
            conversion_to=Lead.PriorConsent28Days,
            # target_value='all: 1.4%, autism: 3.8%',
            conditional_formatting=ExcelClient.ConditionalFormatting.MaxIsGreen
        ),
        ExcelClient.PivotField(source=Lead.PriorConsent28Days),
    ]
    group_function = ExcelClient.GroupFunction.by_weeks
    col_width = (
        ExcelClient.ColWidth.WeeksInterval,
        9.14,
        5.71,
        13.86,
        5.71,
        13.86,
        5.71,
        18.43,
        13,
        18.14,
        9.29,
        18.29,
        7.86
    )


@dataclass()
class PivotOfferSendingSpeed(ExcelClient.PivotData):
    """ Скорость отправки оффера, все """
    sheet = 'Offer'
    rows = [
        Lead.DateOfOffer.Key,
    ]
    filters = [
        ExcelClient.PivotFilter(key=Lead.PipelineName.Key, selected=DEFAULT_PIPELINES),
        ExcelClient.PivotFilter(key=Lead.Responsible.Key),
        ExcelClient.PivotFilter(key=Lead.Agent.Key, selected=['(blank)']),
        ExcelClient.PivotFilter(key=Lead.Treatment.Key),
    ]
    values = [
        # ExcelClient.PivotField(source=Lead.Stage.GettingQuestionnaire),
        # # quest -> offer
        # ExcelClient.PivotField(
        #     conversion_from=Lead.Stage.GettingQuestionnaire,
        #     conversion_to=Lead.Stage.TreatmentDiscussion
        # ),
        ExcelClient.PivotField(source=Lead.Stage.TreatmentDiscussion),
        ExcelClient.PivotField(
            source=Lead.OfferSendingSpeed,
            consolidation_function=ExcelClient.ConsolidationFunction.Average,
            number_format=ExcelClient.NumberFormat.Number
        ),
    ]
    group_function = ExcelClient.GroupFunction.by_months
    col_width = (
        ExcelClient.ColWidth.WeeksInterval,
        9.14,
        14.14,
        21.86,
        19.57,
        18.57,
    )


@dataclass()
class PivotWeeklyAutism(ExcelClient.PivotData):
    """ Сводная таблица: по неделям, аутизм """
    sheet = 'SM Autism (week)'
    rows = [
        Lead.CreatedAt.Key,
    ]
    filters = [
        ExcelClient.PivotFilter(key=Lead.PipelineName.Key, selected=DEFAULT_PIPELINES),
        ExcelClient.PivotFilter(key=Lead.Responsible.Key),
        ExcelClient.PivotFilter(key=Lead.Agent.Key, selected=['(blank)']),
        ExcelClient.PivotFilter(key=Lead.Treatment.Key, selected=['Autism Treatment']),
    ]
    values = [
        ExcelClient.PivotField(source=Lead.Stage.RawLead),
        ExcelClient.PivotField(source=Lead.Stage.Lead),
        # lead -> target
        ExcelClient.PivotField(
            conversion_from=Lead.Stage.Lead,
            conversion_to=Lead.Stage.Target,
            analysis=ExcelClient.Analysis(
                average_deviation=DEFAULT_AVERAGE_DEVIATION,
                line_num=-1
            )
        ),
        ExcelClient.PivotField(source=Lead.Stage.Target),
        # lead -> qual
        ExcelClient.PivotField(conversion_from=Lead.Stage.Lead, conversion_to=Lead.Stage.Qualification),
        ExcelClient.PivotField(source=Lead.Stage.Qualification),
        # qual -> quest
        ExcelClient.PivotField(
            conversion_from=Lead.Stage.Qualification,
            conversion_to=Lead.QuestionnaireRecieved7Days,
            target_value=.2,
            conditional_formatting=ExcelClient.ConditionalFormatting.MaxIsGreen,
            analysis=ExcelClient.Analysis(
                average_deviation=DEFAULT_AVERAGE_DEVIATION,
                line_num=-2
            )
        ),
        ExcelClient.PivotField(source=Lead.QuestionnaireRecieved7Days),
        # qual -> offer
        ExcelClient.PivotField(
            conversion_from=Lead.Stage.Qualification,
            conversion_to=Lead.OfferSent14Days,
            target_value=.08,
            conditional_formatting=ExcelClient.ConditionalFormatting.MaxIsGreen
        ),
        ExcelClient.PivotField(source=Lead.OfferSent14Days),
        ExcelClient.PivotField(
            source=Lead.OfferSendingSpeed,
            consolidation_function=ExcelClient.ConsolidationFunction.Average,
            number_format=ExcelClient.NumberFormat.Number
        ),
        # qual -> prior
        ExcelClient.PivotField(
            conversion_from=Lead.Stage.Qualification,
            conversion_to=Lead.PriorConsent28Days,
            target_value=.038,
            conditional_formatting=ExcelClient.ConditionalFormatting.MaxIsGreen
        ),
        ExcelClient.PivotField(source=Lead.PriorConsent28Days),
    ]
    group_function = ExcelClient.GroupFunction.by_weeks
    col_width = (
        ExcelClient.ColWidth.WeeksInterval,
        9.14,
        5.71,
        13.86,
        5.71,
        13.86,
        5.71,
        18.43,
        13,
        18.14,
        9.29,
        18.29,
        7.86
    )


@dataclass()
class PivotWeeklyAllExceptAutism(ExcelClient.PivotData):
    """ Сводная таблица: по неделям, все, кроме аутизма """
    sheet = 'SM All Except Autism (week)'
    rows = [
        Lead.CreatedAt.Key,
    ]
    filters = [
        ExcelClient.PivotFilter(key=Lead.PipelineName.Key, selected=DEFAULT_PIPELINES),
        ExcelClient.PivotFilter(key=Lead.Responsible.Key),
        ExcelClient.PivotFilter(key=Lead.Agent.Key, selected=['(blank)']),
        ExcelClient.PivotFilter(key=Lead.Treatment.Key, selected=ALL_TREAMENT_EXCEPT_AUTISM),
    ]
    values = [
        ExcelClient.PivotField(source=Lead.Stage.RawLead),
        ExcelClient.PivotField(source=Lead.Stage.Lead),
        # lead -> target
        ExcelClient.PivotField(
            conversion_from=Lead.Stage.Lead,
            conversion_to=Lead.Stage.Target,
            analysis=ExcelClient.Analysis(
                average_deviation=DEFAULT_AVERAGE_DEVIATION,
                line_num=-1
            )
        ),
        ExcelClient.PivotField(source=Lead.Stage.Target),
        # lead -> qual
        ExcelClient.PivotField(conversion_from=Lead.Stage.Lead, conversion_to=Lead.Stage.Qualification),
        ExcelClient.PivotField(source=Lead.Stage.Qualification),
        # qual -> quest
        ExcelClient.PivotField(
            conversion_from=Lead.Stage.Qualification,
            conversion_to=Lead.QuestionnaireRecieved7Days,
            target_value=.25,
            conditional_formatting=ExcelClient.ConditionalFormatting.MaxIsGreen,
            analysis=ExcelClient.Analysis(
                average_deviation=DEFAULT_AVERAGE_DEVIATION,
                line_num=-2
            )
        ),
        ExcelClient.PivotField(source=Lead.QuestionnaireRecieved7Days),
        # qual -> offer
        ExcelClient.PivotField(
            conversion_from=Lead.Stage.Qualification,
            conversion_to=Lead.OfferSent14Days,
            target_value=.08,
            conditional_formatting=ExcelClient.ConditionalFormatting.MaxIsGreen
        ),
        ExcelClient.PivotField(source=Lead.OfferSent14Days),
        ExcelClient.PivotField(
            source=Lead.OfferSendingSpeed,
            consolidation_function=ExcelClient.ConsolidationFunction.Average,
            number_format=ExcelClient.NumberFormat.Number
        ),
        # qual -> prior
        ExcelClient.PivotField(
            conversion_from=Lead.Stage.Qualification,
            conversion_to=Lead.PriorConsent28Days,
            target_value=.018,
            conditional_formatting=ExcelClient.ConditionalFormatting.MaxIsGreen
        ),
        ExcelClient.PivotField(source=Lead.PriorConsent28Days),
    ]
    group_function = ExcelClient.GroupFunction.by_weeks
    col_width = (
        ExcelClient.ColWidth.WeeksInterval,
        9.14,
        5.71,
        13.86,
        5.71,
        13.86,
        5.71,
        18.43,
        13,
        18.14,
        9.29,
        18.29,
        7.86
    )


@dataclass()
class PivotWeeklyEN(PivotWeeklyAll):
    """ Сводная таблица: по неделям, английская зона """
    sheet = 'SM En (week)'
    filters = [
        ExcelClient.PivotFilter(key=Lead.PipelineName.Key, selected=['Новые Клиенты']),
        ExcelClient.PivotFilter(key=Lead.Responsible.Key),
        ExcelClient.PivotFilter(key=Lead.Agent.Key, selected=['(blank)']),
        ExcelClient.PivotFilter(key=Lead.Treatment.Key),
    ]


@dataclass()
class PivotWeeklyIT(PivotWeeklyAll):
    """ Сводная таблица: по неделям, итальянская зона """
    sheet = 'SM It (week)'
    filters = [
        ExcelClient.PivotFilter(key=Lead.PipelineName.Key, selected=['Italy', 'Italian']),
        ExcelClient.PivotFilter(key=Lead.Responsible.Key),
        ExcelClient.PivotFilter(key=Lead.Agent.Key, selected=['(blank)']),
        ExcelClient.PivotFilter(key=Lead.Treatment.Key),
    ]
    values = [
        ExcelClient.PivotField(source=Lead.Stage.RawLead),
        ExcelClient.PivotField(source=Lead.Stage.Lead),
        # lead -> target
        ExcelClient.PivotField(
            conversion_from=Lead.Stage.Lead,
            conversion_to=Lead.Stage.Target,
            analysis=ExcelClient.Analysis(
                average_deviation=DEFAULT_AVERAGE_DEVIATION,
                line_num=-1
            )
        ),
        ExcelClient.PivotField(source=Lead.Stage.Target),
        # lead -> qual
        ExcelClient.PivotField(conversion_from=Lead.Stage.Lead, conversion_to=Lead.Stage.Qualification),
        ExcelClient.PivotField(source=Lead.Stage.Qualification),
        # qual -> quest
        ExcelClient.PivotField(
            conversion_from=Lead.Stage.Qualification,
            conversion_to=Lead.QuestionnaireRecieved14Days,
            # target_value='all: 25%, autism: 20%',
            conditional_formatting=ExcelClient.ConditionalFormatting.MaxIsGreen,
            analysis=ExcelClient.Analysis(
                average_deviation=DEFAULT_AVERAGE_DEVIATION,
                line_num=-2
            )
        ),
        ExcelClient.PivotField(source=Lead.QuestionnaireRecieved14Days),
        # qual -> offer
        ExcelClient.PivotField(
            conversion_from=Lead.Stage.Qualification,
            conversion_to=Lead.OfferSent21Days,
            # target_value='all: 8%',
            conditional_formatting=ExcelClient.ConditionalFormatting.MaxIsGreen
        ),
        ExcelClient.PivotField(source=Lead.OfferSent21Days),
        ExcelClient.PivotField(
            source=Lead.OfferSendingSpeed,
            consolidation_function=ExcelClient.ConsolidationFunction.Average,
            number_format=ExcelClient.NumberFormat.Number
        ),
        # qual -> prior
        ExcelClient.PivotField(
            conversion_from=Lead.Stage.Qualification,
            conversion_to=Lead.PriorConsent35Days,
            # target_value='all: 1.4%, autism: 3.8%',
            conditional_formatting=ExcelClient.ConditionalFormatting.MaxIsGreen
        ),
        ExcelClient.PivotField(source=Lead.PriorConsent35Days),
    ]


@dataclass()
class PivotWeeklyGE(PivotWeeklyAll):
    """ Сводная таблица: по неделям, немецкая зона """
    sheet = 'SM Ge (week)'
    filters = [
        ExcelClient.PivotFilter(key=Lead.PipelineName.Key, selected=['German']),
        ExcelClient.PivotFilter(key=Lead.Responsible.Key),
        ExcelClient.PivotFilter(key=Lead.Agent.Key, selected=['(blank)']),
        ExcelClient.PivotFilter(key=Lead.Treatment.Key),
    ]


@dataclass()
class PivotWeeklyFR(PivotWeeklyAll):
    """ Сводная таблица: по неделям, французская зона """
    sheet = 'SM Fr (week)'
    filters = [
        ExcelClient.PivotFilter(key=Lead.PipelineName.Key, selected=['French']),
        ExcelClient.PivotFilter(key=Lead.Responsible.Key),
        ExcelClient.PivotFilter(key=Lead.Agent.Key, selected=['(blank)']),
        ExcelClient.PivotFilter(key=Lead.Treatment.Key),
    ]


@dataclass()
class PivotMonthlyFull(ExcelClient.PivotData):
    """ Сводная таблица: по месяцам, полные когорты """
    sheet = 'SM полные когорты'
    rows = [
        Lead.CreatedAt.Key,
        Lead.LossReason.Key,
    ]
    filters = [
        ExcelClient.PivotFilter(key=Lead.PipelineName.Key, selected=DEFAULT_PIPELINES),
        ExcelClient.PivotFilter(key=Lead.Responsible.Key),
        ExcelClient.PivotFilter(key=Lead.Agent.Key, selected=['(blank)']),
        ExcelClient.PivotFilter(key=Lead.Treatment.Key),
    ]
    values = [
        ExcelClient.PivotField(source=Lead.Stage.RawLead),
        ExcelClient.PivotField(source=Lead.Stage.Lead),
        ExcelClient.PivotField(source=Lead.Stage.Target),
        # target -> qual
        ExcelClient.PivotField(conversion_from=Lead.Stage.Target, conversion_to=Lead.Stage.Qualification),
        # lead -> qual
        ExcelClient.PivotField(conversion_from=Lead.Stage.Lead, conversion_to=Lead.Stage.Qualification),
        ExcelClient.PivotField(source=Lead.Stage.Qualification),
        # qual -> опросник
        ExcelClient.PivotField(
            conversion_from=Lead.Stage.Qualification,
            conversion_to=Lead.Stage.SchedulingConsultation,
            # target_value='all: 40%, autism: 33%',
            conditional_formatting=ExcelClient.ConditionalFormatting.MaxIsGreen
        ),
        ExcelClient.PivotField(source=Lead.Stage.SchedulingConsultation),
        # # qual -> anamnesis
        # ExcelClient.PivotField(conversion_from=Lead.Stage.Qualification, conversion_to=Lead.Stage.AnamnesisGathering),
        # ExcelClient.PivotField(source=Lead.Stage.AnamnesisGathering),
        # qual -> offer
        ExcelClient.PivotField(conversion_from=Lead.Stage.Qualification, conversion_to=Lead.Stage.TreatmentDiscussion),
        # опросник -> offer
        ExcelClient.PivotField(
            conversion_from=Lead.Stage.SchedulingConsultation,
            conversion_to=Lead.Stage.TreatmentDiscussion,
            # target_value='all: 55%, autism: 60%',
            conditional_formatting=ExcelClient.ConditionalFormatting.MaxIsGreen
        ),
        # anamnesis -> offer
        # ExcelClient.PivotField(conversion_from=Lead.Stage.AnamnesisGathering, conversion_to=Lead.Stage.TreatmentDiscussion),
        ExcelClient.PivotField(source=Lead.Stage.TreatmentDiscussion),
        ExcelClient.PivotField(
            source=Lead.OfferSendingSpeed,
            consolidation_function=ExcelClient.ConsolidationFunction.Average,
            number_format=ExcelClient.NumberFormat.Number
        ),
        ExcelClient.PivotField(
            key=Lead.Stage.TreatmentDiscussion.Alive,
            displayed_name=f'{Lead.Stage.TreatmentDiscussion.DisplayName} (alive)'
        ),
        # lead -> prior
        ExcelClient.PivotField(conversion_from=Lead.Stage.Lead, conversion_to=Lead.Stage.PriorConsent),
        # target -> prior
        ExcelClient.PivotField(conversion_from=Lead.Stage.Target, conversion_to=Lead.Stage.PriorConsent),
        # qual -> prior
        ExcelClient.PivotField(conversion_from=Lead.Stage.Qualification, conversion_to=Lead.Stage.PriorConsent),
        # offer -> prior
        ExcelClient.PivotField(
            conversion_from=Lead.Stage.TreatmentDiscussion,
            conversion_to=Lead.Stage.PriorConsent,
            # target_value='all: 20%, autism: 40%',
            conditional_formatting=ExcelClient.ConditionalFormatting.MaxIsGreen
        ),
        ExcelClient.PivotField(source=Lead.Stage.PriorConsent),
        ExcelClient.PivotField(
            key=Lead.Stage.PriorConsent.Alive,
            displayed_name=f'{Lead.Stage.PriorConsent.DisplayName} (alive)'
        ),
        # qual -> waiting
        ExcelClient.PivotField(conversion_from=Lead.Stage.Qualification, conversion_to=Lead.Stage.WaitingForArrival),
        # prior -> waiting
        ExcelClient.PivotField(
            conversion_from=Lead.Stage.PriorConsent,
            conversion_to=Lead.Stage.WaitingForArrival,
            # target_value='all: 55%, autism: 65%',
            conditional_formatting=ExcelClient.ConditionalFormatting.MaxIsGreen
        ),
        ExcelClient.PivotField(source=Lead.Stage.WaitingForArrival),
        ExcelClient.PivotField(
            key=Lead.Stage.WaitingForArrival.Alive,
            displayed_name=f'{Lead.Stage.WaitingForArrival.DisplayName} (alive)'
        ),
        # qual -> purchase
        ExcelClient.PivotField(
            conversion_from=Lead.Stage.Qualification,
            conversion_to=Lead.Stage.Purchase,
            # target_value='all: 2.13%, autism: 4.38%',
            conditional_formatting=ExcelClient.ConditionalFormatting.MaxIsGreen
        ),
        # waiting -> purchase
        ExcelClient.PivotField(
            conversion_from=Lead.Stage.WaitingForArrival,
            conversion_to=Lead.Stage.Purchase,
            # target_value='all: 88%, autism: 85%',
            conditional_formatting=ExcelClient.ConditionalFormatting.MaxIsGreen
        ),
        # fixme включая выписан из клиники?
        ExcelClient.PivotField(source=Lead.PurchaseExtended),
        ExcelClient.PivotField(
            key=Lead.PurchaseExtendedPrice.Key,
            displayed_name=f'Sum of {Lead.PurchaseExtended.DisplayName}',
            number_format=ExcelClient.NumberFormat.Euro
        ),
        # ExcelClient.PivotField(
        #     key=f'Avrg of {Lead.Stage.Purchase.DisplayName}',
        #     calculated=f"= 'Sum of {Lead.Stage.Purchase.DisplayName}' / '{Lead.Stage.Purchase.Key}'",
        #     number_format=ExcelClient.NumberFormat.Euro
        # ),
        ExcelClient.PivotField(
            key=Lead.PurchaseExtendedPrice.Key,
            number_format=ExcelClient.NumberFormat.Euro,
            displayed_name=f'Avrg. {Lead.PurchaseExtended.DisplayName}',
            consolidation_function=ExcelClient.ConsolidationFunction.Average
        ),
        ExcelClient.PivotField(
            key=Lead.Stage.Treatment.Alive,
            displayed_name=f'{Lead.Stage.Treatment.DisplayName} (alive)'
        ),
        ExcelClient.PivotField(
            key=Lead.Stage.Audit.Alive,
            displayed_name=f'{Lead.Stage.Audit.DisplayName} (alive)'
        ),
        #  %, квал->потенциал продажа
        #  Потенциал продаж, шт
        #  Потенциал продаж, сумма
        #  Ср чек прогноза
        #  Потенциал доп пациентов
        #  Потенциал доп выручки
        # Sum of %, offer -> продажа
    ]
    group_function = ExcelClient.GroupFunction.by_months
    col_width = (
        ExcelClient.ColWidth.WeeksInterval,
        9.14,
        5.71,
        13.86,
        5.71,
        13.86,
        5.71,
        18.43,
        13,
        18.14,
        9.29,
        18.29,
        7.86
    )


@dataclass()
class PivotMonthlyFullExceptAutism(ExcelClient.PivotData):
    """ Сводная таблица: по месяцам, полные когорты (все, кроме аутизма) """
    sheet = 'SM полные когорты (ex. autism)'
    rows = [
        Lead.CreatedAt.Key,
        Lead.LossReason.Key,
    ]
    filters = [
        ExcelClient.PivotFilter(key=Lead.PipelineName.Key, selected=DEFAULT_PIPELINES),
        ExcelClient.PivotFilter(key=Lead.Responsible.Key),
        ExcelClient.PivotFilter(key=Lead.Agent.Key, selected=['(blank)']),
        ExcelClient.PivotFilter(key=Lead.Treatment.Key, selected=ALL_TREAMENT_EXCEPT_AUTISM),
    ]
    values = [
        ExcelClient.PivotField(source=Lead.Stage.RawLead),
        ExcelClient.PivotField(source=Lead.Stage.Lead),
        ExcelClient.PivotField(source=Lead.Stage.Target),
        # target -> qual
        ExcelClient.PivotField(conversion_from=Lead.Stage.Target, conversion_to=Lead.Stage.Qualification),
        # lead -> qual
        ExcelClient.PivotField(conversion_from=Lead.Stage.Lead, conversion_to=Lead.Stage.Qualification),
        ExcelClient.PivotField(source=Lead.Stage.Qualification),
        # qual -> опросник
        ExcelClient.PivotField(
            conversion_from=Lead.Stage.Qualification,
            conversion_to=Lead.Stage.SchedulingConsultation,
            target_value=.4,
            conditional_formatting=ExcelClient.ConditionalFormatting.MaxIsGreen
        ),
        ExcelClient.PivotField(source=Lead.Stage.SchedulingConsultation),
        # # qual -> anamnesis
        # ExcelClient.PivotField(conversion_from=Lead.Stage.Qualification, conversion_to=Lead.Stage.AnamnesisGathering),
        # ExcelClient.PivotField(source=Lead.Stage.AnamnesisGathering),
        # qual -> offer
        ExcelClient.PivotField(conversion_from=Lead.Stage.Qualification, conversion_to=Lead.Stage.TreatmentDiscussion),
        # опросник -> offer
        ExcelClient.PivotField(
            conversion_from=Lead.Stage.SchedulingConsultation,
            conversion_to=Lead.Stage.TreatmentDiscussion,
            target_value=.55,
            conditional_formatting=ExcelClient.ConditionalFormatting.MaxIsGreen
        ),
        # anamnesis -> offer
        # ExcelClient.PivotField(conversion_from=Lead.Stage.AnamnesisGathering, conversion_to=Lead.Stage.TreatmentDiscussion),
        ExcelClient.PivotField(source=Lead.Stage.TreatmentDiscussion),
        ExcelClient.PivotField(
            source=Lead.OfferSendingSpeed,
            consolidation_function=ExcelClient.ConsolidationFunction.Average,
            number_format=ExcelClient.NumberFormat.Number
        ),
        ExcelClient.PivotField(
            key=Lead.Stage.TreatmentDiscussion.Alive,
            displayed_name=f'{Lead.Stage.TreatmentDiscussion.DisplayName} (alive)'
        ),
        # lead -> prior
        ExcelClient.PivotField(conversion_from=Lead.Stage.Lead, conversion_to=Lead.Stage.PriorConsent),
        # target -> prior
        ExcelClient.PivotField(conversion_from=Lead.Stage.Target, conversion_to=Lead.Stage.PriorConsent),
        # qual -> prior
        ExcelClient.PivotField(conversion_from=Lead.Stage.Qualification, conversion_to=Lead.Stage.PriorConsent),
        # offer -> prior
        ExcelClient.PivotField(
            conversion_from=Lead.Stage.TreatmentDiscussion,
            conversion_to=Lead.Stage.PriorConsent,
            target_value=.3,
            conditional_formatting=ExcelClient.ConditionalFormatting.MaxIsGreen
        ),
        ExcelClient.PivotField(source=Lead.Stage.PriorConsent),
        ExcelClient.PivotField(
            key=Lead.Stage.PriorConsent.Alive,
            displayed_name=f'{Lead.Stage.PriorConsent.DisplayName} (alive)'
        ),
        # qual -> waiting
        ExcelClient.PivotField(conversion_from=Lead.Stage.Qualification, conversion_to=Lead.Stage.WaitingForArrival),
        # prior -> waiting
        ExcelClient.PivotField(
            conversion_from=Lead.Stage.PriorConsent,
            conversion_to=Lead.Stage.WaitingForArrival,
            target_value=.55,
            conditional_formatting=ExcelClient.ConditionalFormatting.MaxIsGreen
        ),
        ExcelClient.PivotField(source=Lead.Stage.WaitingForArrival),
        ExcelClient.PivotField(
            key=Lead.Stage.WaitingForArrival.Alive,
            displayed_name=f'{Lead.Stage.WaitingForArrival.DisplayName} (alive)'
        ),
        # qual -> purchase
        ExcelClient.PivotField(
            conversion_from=Lead.Stage.Qualification,
            conversion_to=Lead.Stage.Purchase,
            target_value=.0319,
            conditional_formatting=ExcelClient.ConditionalFormatting.MaxIsGreen
        ),
        # waiting -> purchase
        ExcelClient.PivotField(
            conversion_from=Lead.Stage.WaitingForArrival,
            conversion_to=Lead.Stage.Purchase,
            target_value=.88,
            conditional_formatting=ExcelClient.ConditionalFormatting.MaxIsGreen
        ),
        # fixme включая выписан из клиники?
        ExcelClient.PivotField(source=Lead.PurchaseExtended),
        ExcelClient.PivotField(
            key=Lead.PurchaseExtendedPrice.Key,
            displayed_name=f'Sum of {Lead.PurchaseExtended.DisplayName}',
            number_format=ExcelClient.NumberFormat.Euro
        ),
        # ExcelClient.PivotField(
        #     key=f'Avrg of {Lead.Stage.Purchase.DisplayName}',
        #     calculated=f"= 'Sum of {Lead.Stage.Purchase.DisplayName}' / '{Lead.Stage.Purchase.Key}'",
        #     number_format=ExcelClient.NumberFormat.Euro
        # ),
        ExcelClient.PivotField(
            key=Lead.PurchaseExtendedPrice.Key,
            number_format=ExcelClient.NumberFormat.Euro,
            displayed_name=f'Avrg. {Lead.PurchaseExtended.DisplayName}',
            consolidation_function=ExcelClient.ConsolidationFunction.Average
        ),
        ExcelClient.PivotField(
            key=Lead.Stage.Treatment.Alive,
            displayed_name=f'{Lead.Stage.Treatment.DisplayName} (alive)'
        ),
        ExcelClient.PivotField(
            key=Lead.Stage.Audit.Alive,
            displayed_name=f'{Lead.Stage.Audit.DisplayName} (alive)'
        ),
        #  %, квал->потенциал продажа
        #  Потенциал продаж, шт
        #  Потенциал продаж, сумма
        #  Ср чек прогноза
        #  Потенциал доп пациентов
        #  Потенциал доп выручки
        # Sum of %, offer -> продажа
    ]
    group_function = ExcelClient.GroupFunction.by_months
    col_width = (
        ExcelClient.ColWidth.WeeksInterval,
        9.14,
        5.71,
        13.86,
        5.71,
        13.86,
        5.71,
        18.43,
        13,
        18.14,
        9.29,
        18.29,
        7.86
    )


@dataclass()
class PivotMonthlyFullAutism(ExcelClient.PivotData):
    """ Сводная таблица: по месяцам, полные когорты (аутизм) """
    sheet = 'SM полные когорты (аутизм)'
    rows = [
        Lead.CreatedAt.Key,
        Lead.LossReason.Key,
    ]
    filters = [
        ExcelClient.PivotFilter(key=Lead.PipelineName.Key, selected=DEFAULT_PIPELINES),
        ExcelClient.PivotFilter(key=Lead.Responsible.Key),
        ExcelClient.PivotFilter(key=Lead.Agent.Key, selected=['(blank)']),
        ExcelClient.PivotFilter(key=Lead.Treatment.Key, selected=['Autism Treatment']),
    ]
    values = [
        ExcelClient.PivotField(source=Lead.Stage.RawLead),
        ExcelClient.PivotField(source=Lead.Stage.Lead),
        ExcelClient.PivotField(source=Lead.Stage.Target),
        # target -> qual
        ExcelClient.PivotField(conversion_from=Lead.Stage.Target, conversion_to=Lead.Stage.Qualification),
        # lead -> qual
        ExcelClient.PivotField(conversion_from=Lead.Stage.Lead, conversion_to=Lead.Stage.Qualification),
        ExcelClient.PivotField(source=Lead.Stage.Qualification),
        # qual -> опросник
        ExcelClient.PivotField(
            conversion_from=Lead.Stage.Qualification,
            conversion_to=Lead.Stage.SchedulingConsultation,
            target_value=.33,
            conditional_formatting=ExcelClient.ConditionalFormatting.MaxIsGreen
        ),
        ExcelClient.PivotField(source=Lead.Stage.SchedulingConsultation),
        # # qual -> anamnesis
        # ExcelClient.PivotField(conversion_from=Lead.Stage.Qualification, conversion_to=Lead.Stage.AnamnesisGathering),
        # ExcelClient.PivotField(source=Lead.Stage.AnamnesisGathering),
        # qual -> offer
        ExcelClient.PivotField(conversion_from=Lead.Stage.Qualification, conversion_to=Lead.Stage.TreatmentDiscussion),
        # опросник -> offer
        ExcelClient.PivotField(
            conversion_from=Lead.Stage.SchedulingConsultation,
            conversion_to=Lead.Stage.TreatmentDiscussion,
            target_value=.6,
            conditional_formatting=ExcelClient.ConditionalFormatting.MaxIsGreen
        ),
        # anamnesis -> offer
        # ExcelClient.PivotField(conversion_from=Lead.Stage.AnamnesisGathering, conversion_to=Lead.Stage.TreatmentDiscussion),
        ExcelClient.PivotField(source=Lead.Stage.TreatmentDiscussion),
        ExcelClient.PivotField(
            source=Lead.OfferSendingSpeed,
            consolidation_function=ExcelClient.ConsolidationFunction.Average,
            number_format=ExcelClient.NumberFormat.Number
        ),
        ExcelClient.PivotField(
            key=Lead.Stage.TreatmentDiscussion.Alive,
            displayed_name=f'{Lead.Stage.TreatmentDiscussion.DisplayName} (alive)'
        ),
        # lead -> prior
        ExcelClient.PivotField(conversion_from=Lead.Stage.Lead, conversion_to=Lead.Stage.PriorConsent),
        # target -> prior
        ExcelClient.PivotField(conversion_from=Lead.Stage.Target, conversion_to=Lead.Stage.PriorConsent),
        # qual -> prior
        ExcelClient.PivotField(conversion_from=Lead.Stage.Qualification, conversion_to=Lead.Stage.PriorConsent),
        # offer -> prior
        ExcelClient.PivotField(
            conversion_from=Lead.Stage.TreatmentDiscussion,
            conversion_to=Lead.Stage.PriorConsent,
            target_value=.4,
            conditional_formatting=ExcelClient.ConditionalFormatting.MaxIsGreen
        ),
        ExcelClient.PivotField(source=Lead.Stage.PriorConsent),
        ExcelClient.PivotField(
            key=Lead.Stage.PriorConsent.Alive,
            displayed_name=f'{Lead.Stage.PriorConsent.DisplayName} (alive)'
        ),
        # qual -> waiting
        ExcelClient.PivotField(conversion_from=Lead.Stage.Qualification, conversion_to=Lead.Stage.WaitingForArrival),
        # prior -> waiting
        ExcelClient.PivotField(
            conversion_from=Lead.Stage.PriorConsent,
            conversion_to=Lead.Stage.WaitingForArrival,
            target_value=.65,
            conditional_formatting=ExcelClient.ConditionalFormatting.MaxIsGreen
        ),
        ExcelClient.PivotField(source=Lead.Stage.WaitingForArrival),
        ExcelClient.PivotField(
            key=Lead.Stage.WaitingForArrival.Alive,
            displayed_name=f'{Lead.Stage.WaitingForArrival.DisplayName} (alive)'
        ),
        # qual -> purchase
        ExcelClient.PivotField(
            conversion_from=Lead.Stage.Qualification,
            conversion_to=Lead.Stage.Purchase,
            target_value=.0438,
            conditional_formatting=ExcelClient.ConditionalFormatting.MaxIsGreen
        ),
        # waiting -> purchase
        ExcelClient.PivotField(
            conversion_from=Lead.Stage.WaitingForArrival,
            conversion_to=Lead.Stage.Purchase,
            target_value=.85,
            conditional_formatting=ExcelClient.ConditionalFormatting.MaxIsGreen
        ),
        # fixme включая выписан из клиники?
        ExcelClient.PivotField(source=Lead.PurchaseExtended),
        ExcelClient.PivotField(
            key=Lead.PurchaseExtendedPrice.Key,
            displayed_name=f'Sum of {Lead.PurchaseExtended.DisplayName}',
            number_format=ExcelClient.NumberFormat.Euro
        ),
        # ExcelClient.PivotField(
        #     key=f'Avrg of {Lead.Stage.Purchase.DisplayName}',
        #     calculated=f"= 'Sum of {Lead.Stage.Purchase.DisplayName}' / '{Lead.Stage.Purchase.Key}'",
        #     number_format=ExcelClient.NumberFormat.Euro
        # ),
        ExcelClient.PivotField(
            key=Lead.PurchaseExtendedPrice.Key,
            number_format=ExcelClient.NumberFormat.Euro,
            displayed_name=f'Avrg. {Lead.PurchaseExtended.DisplayName}',
            consolidation_function=ExcelClient.ConsolidationFunction.Average
        ),
        ExcelClient.PivotField(
            key=Lead.Stage.Treatment.Alive,
            displayed_name=f'{Lead.Stage.Treatment.DisplayName} (alive)'
        ),
        ExcelClient.PivotField(
            key=Lead.Stage.Audit.Alive,
            displayed_name=f'{Lead.Stage.Audit.DisplayName} (alive)'
        ),
        #  %, квал->потенциал продажа
        #  Потенциал продаж, шт
        #  Потенциал продаж, сумма
        #  Ср чек прогноза
        #  Потенциал доп пациентов
        #  Потенциал доп выручки
        # Sum of %, offer -> продажа
    ]
    group_function = ExcelClient.GroupFunction.by_months
    col_width = (
        ExcelClient.ColWidth.WeeksInterval,
        9.14,
        5.71,
        13.86,
        5.71,
        13.86,
        5.71,
        18.43,
        13,
        18.14,
        9.29,
        18.29,
        7.86
    )


@dataclass()
class PivotMonthlyIntermediate(ExcelClient.PivotData):
    """ Сводная таблица: по месяцам, промежуточные когорты """
    sheet = 'SM промежуточные когорты'
    rows = [
        Lead.CreatedAt.Key
    ]
    filters = [
        ExcelClient.PivotFilter(key=Lead.PipelineName.Key, selected=['Новые Клиенты']),
        ExcelClient.PivotFilter(key=Lead.Responsible.Key)
    ]
    values = [
        ExcelClient.PivotField(source=Lead.Stage.RawLead),
        ExcelClient.PivotField(source=Lead.Stage.Lead),
        # lead -> target
        ExcelClient.PivotField(conversion_from=Lead.Stage.Lead, conversion_to=Lead.Stage.Target),
        ExcelClient.PivotField(source=Lead.Stage.Target),
        # target -> qual
        ExcelClient.PivotField(conversion_from=Lead.Stage.Target, conversion_to=Lead.Stage.Qualification),
        # lead -> qual
        ExcelClient.PivotField(conversion_from=Lead.Stage.Lead, conversion_to=Lead.Stage.Qualification),
        ExcelClient.PivotField(source=Lead.Stage.Qualification),
        # qual -> quest
        ExcelClient.PivotField(conversion_from=Lead.Stage.Qualification, conversion_to=Lead.QuestionnaireRecieved7Days),
        ExcelClient.PivotField(source=Lead.QuestionnaireRecieved7Days),
        # qual -> offer
        ExcelClient.PivotField(conversion_from=Lead.Stage.Qualification, conversion_to=Lead.OfferSent14Days),
        ExcelClient.PivotField(source=Lead.OfferSent14Days),
        # qual -> prior
        ExcelClient.PivotField(conversion_from=Lead.Stage.Qualification, conversion_to=Lead.PriorConsent28Days),
        ExcelClient.PivotField(source=Lead.PriorConsent28Days),
    ]
    group_function = ExcelClient.GroupFunction.by_months
    col_width = (
        ExcelClient.ColWidth.WeeksInterval,
        9.14,
        5.71,
        13.86,
        5.71,
        13.86,
        5.71,
        18.43,
        13,
        18.14,
        9.29,
        18.29,
        7.86
    )


@dataclass()
class PivotMonthlyForecast(ExcelClient.PivotData):
    """ Сводная таблица: по месяцам, прогноз выручки """
    sheet = 'SM прогноз выручки'
    rows = [
        Lead.CreatedAt.Key
    ]
    filters = [
        ExcelClient.PivotFilter(key=Lead.PipelineName.Key),
        ExcelClient.PivotFilter(key=Lead.Responsible.Key),
        ExcelClient.PivotFilter(key=Lead.Agent.Key),
    ]
    values = [
        # ExcelClient.PivotField(source=Lead.AllAlive),
        # обсуждение лечения (отправлен оффер)
        ExcelClient.PivotField(key=Lead.Stage.TreatmentDiscussion.Alive),
        ExcelClient.PivotField(
            key=Lead.Stage.TreatmentDiscussion.PlannedIncome,
            number_format=ExcelClient.NumberFormat.Euro
        ),
        ExcelClient.PivotField(
            key=Lead.Stage.TreatmentDiscussion.PlannedIncomeFull,
            number_format=ExcelClient.NumberFormat.Euro
        ),
        # предварительное согласие
        ExcelClient.PivotField(key=Lead.Stage.PriorConsent.Alive),
        ExcelClient.PivotField(key=Lead.Stage.PriorConsent.PlannedIncome, number_format=ExcelClient.NumberFormat.Euro),
        ExcelClient.PivotField(
            key=Lead.Stage.PriorConsent.PlannedIncomeFull,
            number_format=ExcelClient.NumberFormat.Euro
        ),
        # ожидаем приезда
        ExcelClient.PivotField(key=Lead.Stage.WaitingForArrival.Alive),
        ExcelClient.PivotField(
            key=Lead.Stage.WaitingForArrival.PlannedIncome,
            number_format=ExcelClient.NumberFormat.Euro
        ),
        ExcelClient.PivotField(
            key=Lead.Stage.WaitingForArrival.PlannedIncomeFull,
            number_format=ExcelClient.NumberFormat.Euro
        ),
        # в клинике
        ExcelClient.PivotField(key=Lead.Stage.Treatment.Alive),
        ExcelClient.PivotField(key=Lead.Stage.Treatment.PlannedIncome, number_format=ExcelClient.NumberFormat.Euro),
        # выписан
        ExcelClient.PivotField(key=Lead.Stage.Audit.Alive),
        ExcelClient.PivotField(key=Lead.Stage.Audit.PlannedIncome, number_format=ExcelClient.NumberFormat.Euro),
    ]
    group_function = ExcelClient.GroupFunction.by_months
    col_width = (
        ExcelClient.ColWidth.WeeksInterval,
        9.14,
        5.71,
        13.86,
        5.71,
        13.86,
        5.71,
        18.43,
        13,
        18.14,
        9.29,
        18.29,
        7.86
    )


@dataclass()
class PivotMonthlyInvestigation(ExcelClient.PivotData):
    """ Сводная таблица: по месяцам, исследование """
    sheet = 'SM исследование'
    rows = [
        Lead.CreatedAt.Key
    ]
    filters = [
        # fixme city from jivo?
        ExcelClient.PivotFilter(key=Lead.PipelineName.Key, selected=['Новые Клиенты'])
    ]
    values = [
        # lead -> qual
        ExcelClient.PivotField(conversion_from=Lead.Stage.Lead, conversion_to=Lead.Stage.Qualification),
        ExcelClient.PivotField(source=Lead.Stage.Qualification),

    ]
    group_function = ExcelClient.GroupFunction.by_months
    col_width = (
        ExcelClient.ColWidth.WeeksInterval,
        9.14,
        5.71,
        13.86,
        5.71,
        13.86,
        5.71,
        18.43,
        13,
        18.14,
        9.29,
        18.29,
        7.86
    )


@dataclass()
class PivotClusterTags(ExcelClient.PivotData):
    """ Сводная таблица: теги """
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
