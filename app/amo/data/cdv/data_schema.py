""" Схема данных для сводных отчетов CDV """
__author__ = 'ke.mizonov'
from dataclasses import dataclass, field
from enum import Enum
from app.amo.data.base.data_schema import Lead, LeadField, StageBase, StageItem


@dataclass()
class StageCDV(StageBase):
    """ Стадия воронки """
    RawLead: StageItem = field(default_factory=lambda: StageItem(
        DisplayName='Raw leads',
        Documentation="""Сырой лид, потенциальный клиент - этап сделки, через который проходят все заявки.""",
        IncludeStages=[],
        IncludeFields=[],
        Key='raw_lead',
        Priority=0
    ))
    Lead: StageItem = field(default_factory=lambda: StageItem(
        DisplayName='Leads',
        Documentation="""
            Лид, потенциальный клиент
            
            Исключения:
            - имеющие причину закрытия 'Duplicate Lead' (дубликаты) и 'SPAM'
            - удаленные (в том числе в результате объединения)
            
            Удаленные сделки выявляются по событиям в Amo.
        """,
        IncludeStages=[
            '01. NEW LEAD',
            '02. CONTINUE TO  WORK',
            '1. TRYING TO GET IN TOUCH',
        ],
        IncludeFields=['1. Tring_get_in_touch'],
        Key='lead',
        Priority=1
    ))
    Target: StageItem = field(default_factory=lambda: StageItem(
        DisplayName='Target leads',
        Documentation="""Целевой лид (контакт верный, человек нуждается в услугах клиники)""",
        IncludeStages=[],  # целевой лид определяется по другой логике, тут оставляем пустой список
        IncludeFields=[
            'tselevoj',
            'tselevoj!',
            'Целевой!'
        ],
        Key='target',
        Priority=2
    ))
    SchedulingConsultation: StageItem = field(default_factory=lambda: StageItem(
        DisplayName='Scheduling consultation',
        Documentation="""Планирование консультации""",
        IncludeStages=[
            '2.1. SCHEDULING CONSULTATION',
        ],
        IncludeFields=[
            '2.1. SCHEDULING CONSULTATION',
        ],
        Key='scheduling_consultation',
        Priority=3
    ))
    WaitingForConsultation: StageItem = field(default_factory=lambda: StageItem(
        DisplayName='Waiting for consultation',
        Documentation="""Ожидание консультации""",
        IncludeStages=[
            '2.2. WAITING FOR CONSULTATION',
        ],
        IncludeFields=[
            '2.2. WAITING FOR CONSULTATION',
        ],
        Key='waiting_for_consultation',
        Priority=4
    ))
    DiscussionOfTreatment: StageItem = field(default_factory=lambda: StageItem(
        DisplayName='Discussion of treatment',
        Documentation="""Обсуждение лечения""",
        IncludeStages=[
            '3.1. DISCUSSION OF TREATMENT',
        ],
        IncludeFields=[
            '3.1. DISCUSSION OF TREATMENT',
        ],
        Key='discussion_of_treatment',
        Priority=5
    ))
    LongNegotiations: StageItem = field(default_factory=lambda: StageItem(
        DisplayName='Long negotiations',
        Documentation="""Обсуждение лечения""",
        IncludeStages=[
            '3.2. LONG NEGOTIATIONS',
        ],
        IncludeFields=[
            '3.2. LONG NEGOTIATIONS',
        ],
        Key='long_negotiations',
        Priority=6
    ))
    Qualification: StageItem = field(default_factory=lambda: StageItem(
        DisplayName='Qual leads',
        Documentation="""Квалифицированный лид (получил консультацию, готов вести иалог дальше)""",
        IncludeStages=[],
        IncludeFields=[
            '1 Квалификация',
            'Qualification',
            '1_kvalifikatsija'
        ],
        Key='qualification',
        Priority=7
    ))
    PriorConsent: StageItem = field(default_factory=lambda: StageItem(
        DisplayName='Prior consent',
        Documentation="""Предварительное согласие на лечение""",
        IncludeStages=[
            '4. PRIOR CONSENT',
        ],
        IncludeFields=[
            '4. PRIOR CONSENT'
        ],
        Key='prior_consent',
        Priority=8
    ))
    WaitingAtClinic: StageItem = field(default_factory=lambda: StageItem(
        DisplayName='Waiting at the clinic',
        Documentation="""Ожидание лечения""",
        IncludeStages=[
            '5. WAITING FOR ADMISSION',
        ],
        IncludeFields=[
            '5. WAITING AT THE CLINIC',
        ],
        Key='waiting_at_the_clinic',
        Priority=9
    ))
    Treatment: StageItem = field(default_factory=lambda: StageItem(
        DisplayName='Treatment',
        Documentation="""Лечение""",
        IncludeStages=[
            '6. TREATMENT',
        ],
        IncludeFields=[
            '6. TREATMENT',
        ],
        Key='treatment',
        Priority=10
    ))
    Purchase: StageItem = field(default_factory=lambda: StageItem(
        DisplayName='Purchase',
        Documentation="""Покупка""",
        IncludeStages=[
            '7. LEAD AUDIT'
        ],
        IncludeFields=[
            '7. LEAD AUDIT',
        ],
        Key='purchase',
        AtWork=False,
        Priority=11
    ))

    def __post_init__(self):
        super().__init__()


@dataclass()
class StageItemMT(StageItem):
    def __post_init__(self):
        super().__post_init__(prefix='mt')


@dataclass()
class StageMT(StageBase):
    """ Стадия воронки Mental transformation """
    RawLead: StageItem = field(default_factory=lambda: StageItemMT(
        DisplayName='Raw leads',
        Documentation="""Сырой лид, потенциальный клиент - этап сделки, через который проходят все заявки.""",
        IncludeStages=[],
        IncludeFields=[],
        Key='raw_lead',
        Priority=0
    ))
    Lead: StageItem = field(default_factory=lambda: StageItemMT(
        DisplayName='Leads',
        Documentation="""
            Лид, потенциальный клиент

            Исключения:
            - имеющие причину закрытия 'Duplicate Lead' (дубликаты) и 'SPAM'
            - удаленные (в том числе в результате объединения)

            Удаленные сделки выявляются по событиям в Amo.
        """,
        IncludeStages=[
            'NEW LEAD',
            'TRYING TO GET IN TOUCH'
        ],
        IncludeFields=[],
        Key='lead',
        Priority=1
    ))
    Target: StageItem = field(default_factory=lambda: StageItemMT(
        DisplayName='Target leads',
        Documentation="""Целевой лид (контакт верный, человек нуждается в услугах клиники)""",
        IncludeStages=[],  # целевой лид определяется по другой логике, тут оставляем пустой список
        IncludeFields=[
            'tselevoj',
            'tselevoj!',
            'Целевой!'
        ],
        Key='target',
        Priority=2
    ))
    SchedulingConsultation: StageItem = field(default_factory=lambda: StageItemMT(
        DisplayName='Scheduling consultation',
        Documentation="""Планирование консультации""",
        IncludeStages=[
            'CONSULTATION ASSIGNMENT',
        ],
        IncludeFields=[
            'Qualification',
        ],
        Key='scheduling_consultation',
        Priority=3
    ))
    AfterConsultation: StageItem = field(default_factory=lambda: StageItemMT(
        DisplayName='After consultation',
        Documentation="""После консультации""",
        IncludeStages=[
            'AFTER CONSULTATION',
        ],
        IncludeFields=[
            'After consultation',
        ],
        Key='after_consultation',
        Priority=4
    ))
    PaidConsultationAssignment: StageItem = field(default_factory=lambda: StageItemMT(
        DisplayName='Paid consultation assignment',
        Documentation="""Планирование платной консультации""",
        IncludeStages=[
            'PAID CONSULTATION ASSIGNMENT',
        ],
        IncludeFields=[
            'Scheduled for a paid consultation',
        ],
        Key='paid_consultation_assignment',
        Priority=5
    ))
    AfterPaidConsultation: StageItem = field(default_factory=lambda: StageItemMT(
        DisplayName='After paid consultation',
        Documentation="""После платной консультации""",
        IncludeStages=[
            'AFTER PAID CONSULTATION',
        ],
        IncludeFields=[
            'After paid consultation',
        ],
        Key='after_paid_consultation',
        Priority=6
    ))
    PriorConsent: StageItem = field(default_factory=lambda: StageItemMT(
        DisplayName='Prior consent',
        Documentation="""Предварительное согласие на лечение""",
        IncludeStages=[
            '4. PRIOR CONSENT',
        ],
        IncludeFields=[
            '4. PRIOR CONSENT'
        ],
        Key='prior_consent',
        Priority=7
    ))
    Purchase: StageItem = field(default_factory=lambda: StageItemMT(
        DisplayName='Purchase',
        Documentation="""Покупка""",
        IncludeStages=[
            'Successfully realized',
            'Успешно реализовано'
        ],
        IncludeFields=[],       # todo
        Key='purchase',
        AtWork=False,
        Priority=8
    ))

    def __post_init__(self):
        super().__init__()


class CloseReasonCDV(Enum):
    """ Причины потери лида, позволяющие квалифицировать его как целевого """
    Undefined = 'Undefined reason'
    Expensive = 'Expensive'
    Location = 'Location'
    ChangedTheMind = 'Changed the mind'
    DontWantTreatment = "Don't want to be treated"
    # WeDoNotCure = 'We do not cure'
    CalledCompetitor = 'Call to competitor'
    Stuttering = 'Stuttering'
    Other = 'Other'
    ChangedTheMind2 = 'Changed the mind / Disappeared'
    CalledCompetitor2 = 'Call to Drajzerova'
    CalledCompetitor3 = 'Call to competitor (Direct)'
    ProgramNotSuitable = 'Program not suitable'
    NoReason = 'Без причины'


@dataclass()
class LeadCDV(Lead):
    """ Данные лида """
    Pipelines = [
        'New_patients_general_SE',
        'New_patients_IT',
        'New_patients_FR',
        'New_patients_SP',
        'Repeated patients',
        'New_patients_ENG',
        'New_patients_GE',
        'New_patients_RU',
        'New_patients_RO',
    ]
    CloseReason = CloseReasonCDV
    Stage = StageCDV
    AutodocsSheet = 'CDV'

    Admission7Days: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='7 days admission',
        Documentation="""Порядковый номер недели, в которую пациент посетил клинику""",
        Key='7_days_admission'
    ))
    Admission14Days: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='14 days admission',
        Documentation="""
            1 - если пациент посетил клинику в течение 14 дней с момента создания сделки
        """,
        Key='14_days_admission'
    ))
    Budget: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Budget',
        Documentation="""Бюджет""",
        Key='budget',
        CustomField='Бюджет'
    ))
    CallDuration30: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Call duration 30',
        Documentation="""
            Количество звонков длительностью 0,5 минут и более

            Сверка по отчетам телефонии, номер телефона берется из контактов
        """,
        Key='call_duration_30'
    ))
    CallDuration60: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Call duration 60',
        Documentation="""
            Количество звонков длительностью 1 минута и более

            Сверка по отчетам телефонии, номер телефона берется из контактов
        """,
        Key='call_duration_60'
    ))
    CallDuration120: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Call duration 120',
        Documentation="""
            Количество звонков длительностью 2 минуты и более

            Сверка по отчетам телефонии, номер телефона берется из контактов
        """,
        Key='call_duration_120'
    ))
    CallDuration180: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Call duration 180',
        Documentation="""
            Количество звонков длительностью 3 минуты и более

            Сверка по отчетам телефонии, номер телефона берется из контактов
        """,
        Key='call_duration_180'
    ))
    CallDuration240: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Call duration 240',
        Documentation="""
            Количество звонков длительностью 4 минуты и более

            Сверка по отчетам телефонии, номер телефона берется из контактов
        """,
        Key='call_duration_240'
    ))
    CallDuration300: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Call duration 300',
        Documentation="""
            Количество звонков длительностью 5 минут и более

            Сверка по отчетам телефонии, номер телефона берется из контактов
        """,
        Key='call_duration_300'
    ))
    CallDurationSummary30: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Call duration summary 30',
        Documentation="""
            Длительность звонков длительностью 0,5 минут и более

            Сверка по отчетам телефонии, номер телефона берется из контактов
        """,
        Key='call_duration_summary_30'
    ))
    CallDurationSummary60: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Call duration summary 60',
        Documentation="""
            Длительность звонков длительностью 1 минута и более

            Сверка по отчетам телефонии, номер телефона берется из контактов
        """,
        Key='call_duration_summary_60'
    ))
    CallDurationSummary120: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Call duration summary 120',
        Documentation="""
            Длительность звонков длительностью 2 минуты и более

            Сверка по отчетам телефонии, номер телефона берется из контактов
        """,
        Key='call_duration_summary_120'
    ))
    CallDurationSummary180: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Call duration summary 180',
        Documentation="""
            Длительность звонков длительностью 3 минуты и более

            Сверка по отчетам телефонии, номер телефона берется из контактов
        """,
        Key='call_duration_summary_180'
    ))
    CallDurationSummary240: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Call duration summary 240',
        Documentation="""
            Длительность звонков длительностью 4 минуты и более

            Сверка по отчетам телефонии, номер телефона берется из контактов
        """,
        Key='call_duration_summary_240'
    ))
    CallDurationSummary300: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Call duration summary 300',
        Documentation="""
            Длительность звонков длительностью 5 минут и более

            Сверка по отчетам телефонии, номер телефона берется из контактов
        """,
        Key='call_duration_summary_300'
    ))
    CallDobrica45: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Call Dobrica 45 sec+',
        Documentation="""
            Количество звонков Добрицы длительностью 45 секунд и выше

            Сверка по отчетам телефонии, номер телефона берется из контактов
        """,
        Key='call_dobrica_45_sec'
    ))
    Calls: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Calls',
        Documentation="""
            Общее количество звонков

            Сверка по отчетам телефонии, номер телефона берется из контактов
        """,
        Key='calls'
    ))
    Clinic: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Clinic',
        Documentation="""Клиника""",
        Key='clinic',
        CustomField='Clinic'
    ))
    ConsultingDoctor: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Consulting doctor',
        Documentation="""Консультирующий врач""",
        Key='consulting_doctor',
        CustomField='Consulting doctor'
    ))
    Contact: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Contact',
        Documentation="""Контакт: сам пациент или его близкий""",
        Key='contact',
        CustomField='Contact'
    ))
    Country: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Country',
        Documentation="""
            Предполагаемая страна лида.

            Взято из доп. полей 'Country', 'Country_from_Jivo', 'CLIENTS_COUNTRY'.
            В приоритете значение из поля 'Country'.
            IP и MAC-адреса, содержащиеся в этих полях, исключены.
        """,
        Key='country',
        CustomField='Country'
    ))
    DateOfAdmission: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Date of admission',
        Documentation="""Дата посещения""",
        Key='date_of_admission',
        CustomField='Date of admission',
        IsDate=True
    ))
    DateOfDoctorConsultation: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Date doctor consultation',
        Documentation="""Дата консультации с доктором""",
        Key='date_doctor_consultation',
        CustomField='Date doctor consultation',
        IsDate=True
    ))
    DateOfPriorConsent: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Date of prior consent',
        Documentation="""Дата предварительного согласия""",
        Key='date_of_prior_consent',
        CustomField='Date of prior concern',        # не исправлять, написано именно так!
        IsDate=True
    ))
    DateOfSale: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Date of sale',
        Documentation="""Дата продажи""",
        Key='date_of_sale',
        CustomField='Date of sale (get date of treatment))',
        IsDate=True
    ))
    DaysAtTheClinic: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Days at the clinic',
        Documentation="""Количество дней, проведенных в клинике""",
        Key='days_at_the_clinic',
        CustomField='Days at the clinic'
    ))
    DischargeDate: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Discharge date',
        Documentation="""Дата выписки""",
        Key='discharge_date',
        CustomField='Discharge date',
        IsDate=True
    ))
    Discount: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Discount',
        Documentation="""Скидка""",
        Key='discount',
        CustomField='Discount'
    ))
    GoogleID: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Google ID',
        Documentation="""Идентификатор клиента в рекламной системе Google - берем из доп. полей""",
        Key='google_id',
        CustomField='google_client_id'
    ))
    # FacebookID: LeadField = LeadField(
    #     DisplayName='Facebook ID',
    #     Documentation="""Идентификатор клиента в рекламной системе Facebook - берем из доп. полей""",
    #     Key='facebook_id',
    #     CustomField='face_client_id'        # todo
    # )
    RuleNum: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Rule Num',
        Documentation="""
            Порядковый номер правила постобработки, примененного к utm-меткам
            См. https://docs.google.com/spreadsheets/d/1blEKCs2rkNVlo7E61xvAwgrGeW3H_du-3nblbJCn6rs/edit#gid=1151972685
        """,
        Key='final_rule_num'
    ))
    Language: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Language',
        Documentation="""Язык лида - берем из доп. полей""",
        Key='language',
        CustomField='Language'
    ))
    PriorConsent14Days: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='14 days prior consent',
        Documentation="""
            1 - если пациент дал предварительное согласие на лечение в течение 14 дней с момента создания сделки
        """,
        Key='14_days_prior_consent'
    ))
    Recomendation: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Recomendation',
        Documentation="""По рекомендации""",
        Key='recomendation',
        CustomField='Recomendation'
    ))
    SourceOfInitialContact: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Source of initial contact',
        Documentation="""Источник""",
        Key='source_of_initial_contact',
        CustomField='Source of initial contact'
    ))
    Treatment: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Treatment',
        Documentation="""Болезнь, диагноз, направление - берем из доп. полей""",
        Key='treatment',
        CustomField='Treatment'
    ))
    Upsale: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Upsale',
        Documentation="""Доп. продажа""",
        Key='upsale',
        CustomField='Upsale'
    ))
    ReachedStage: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Reached stage',
        Documentation="""Максимальный достигнутый этап воронки""",
        Key='reached_stage'
    ))

    def __post_init__(self):
        super().__init__()


@dataclass()
class LeadMT(Lead):
    """ Данные лида """
    Pipelines = ['Mental transformation']
    CloseReason = CloseReasonCDV
    Stage = StageMT
    AutodocsSheet = 'MT'

    ReachedStage: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Reached stage [mt]',
        Documentation="""Максимальный достигнутый этап воронки [MT]""",
        Key='reached_stage_mt'
    ))

    def __post_init__(self):
        super().__init__()
