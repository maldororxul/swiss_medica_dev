""" Схема данных для сводных отчетов Swiss Medica """
__author__ = 'ke.mizonov'
from dataclasses import dataclass, field
from enum import Enum
from app.amo.data.base.data_schema import Lead, StageItem, StageBase, LeadField


@dataclass()
class StageSM(StageBase):
    """ Стадия воронки """
    Lead: StageItem = field(default_factory=lambda: StageItem(
        DisplayName='Leads',
        Documentation="""
            Лид, потенциальный клиент
            
            Исключения:
            - имеющие причину закрытия 'Duplicate Lead' (дубликаты)
            - удаленные (в том числе в результате объединения)
            
            Удаленные сделки выявляются по событиям в Amo.
        """,
        IncludeStages=[
            'НОВЫЕ ЗАЯВКИ',
            'ПРОДОЛЖИТЬ РАБОТУ',
            '0. ВЫХОД НА КОНТАКТ',
        ],
        IncludeFields=[],
        Key='lead',
        Priority=1
    ))
    ContinueToWork: StageItem = field(default_factory=lambda: StageItem(
        DisplayName='Continue to work',
        Documentation="""Продолжить работу""",
        IncludeStages=[],
        IncludeFields=[],
        Key='continue_to_work',
        Priority=2
    ))
    TryingToGetInTouch: StageItem = field(default_factory=lambda: StageItem(
        DisplayName='Trying to get in touch',
        Documentation="""Выход на контакт""",
        IncludeStages=[],
        IncludeFields=[],
        Key='trying_to_get_in_touch',
        Priority=3
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
        Priority=4
    ))
    GettingQuestionnaire: StageItem = field(default_factory=lambda: StageItem(
        DisplayName='Getting questionnaire',
        Documentation="""Получение опросника""",
        IncludeStages=[
            '1. ПОЛУЧЕНИЕ ОПРОСНИКА',
        ],
        IncludeFields=[
            '1 Квалификация',
        ],
        Key='getting_questionnaire',
        Priority=5
    ))
    AnamnesisGathering: StageItem = field(default_factory=lambda: StageItem(
        DisplayName='Anamnesis gathering',
        Documentation="""Досбор анамнеза""",
        IncludeStages=[
            '2. ДОСБОР АНАМНЕЗА',
        ],
        IncludeFields=[],
        Key='anamnesis_gathering',
        Priority=6
    ))
    Qualification: StageItem = field(default_factory=lambda: StageItem(
        DisplayName='Qual leads',
        Documentation="""Квалифицированный лид (получил консультацию, готов вести иалог дальше)""",
        IncludeStages=[
            '3.1. ПЕРЕГОВОРЫ ПО ПРОГРАММЕ',
        ],
        IncludeFields=[
            '1 Квалификация',
            'Qualification',
            '1_kvalifikatsija'
        ],
        Key='qualification',
        # TargetValue='month: all 250, autism 200',
        Priority=7
    ))
    SchedulingConsultation: StageItem = field(default_factory=lambda: StageItem(
        DisplayName='Scheduling consultation (questionnaire was sent)',
        Documentation="""Планирование консультации""",
        IncludeStages=[
            '2.1 СОГЛАСОВЫВАЕМ ДАТУ КОНСУЛЬТАЦИИ',
        ],
        IncludeFields=[
            'Получен опросник',
        ],
        Key='scheduling_consultation',
        Priority=8
    ))
    WaitingForConsultation: StageItem = field(default_factory=lambda: StageItem(
        DisplayName='Waiting for consultation',
        Documentation="""Ожидание консультации""",
        IncludeStages=[
            '3. ОЖИДАЕМ ПРОВЕДЕНИЯ КОНСУЛЬТАЦИИ',
        ],
        IncludeFields=[],
        Key='waiting_for_consultation',
        Priority=9
    ))
    TreatmentDiscussion: StageItem = field(default_factory=lambda: StageItem(
        DisplayName='Treatment discussion (Offer was sent)',
        Documentation="""Переговоры по программе, отправлен offer""",
        IncludeStages=[
            '3.1. ПЕРЕГОВОРЫ ПО ПРОГРАММЕ',
        ],
        IncludeFields=[
            'Отправлен Offer'
        ],
        Key='treatment_discussion',
        PurchaseRate=.12,
        Priority=10
    ))
    PriorConsent: StageItem = field(default_factory=lambda: StageItem(
        DisplayName='Prior consent',
        Documentation="""Предварительное согласие на лечение""",
        IncludeStages=[
            '4. СОГЛАСЕН НА ЛЕЧЕНИЕ',
        ],
        IncludeFields=[
            'Предварительное согласие',
        ],
        Key='prior_consent',
        PurchaseRate=.51,
        Priority=11
    ))
    DiscountRequest: StageItem = field(default_factory=lambda: StageItem(
        DisplayName='Discount request',
        Documentation="""Запрос скидки""",
        IncludeStages=[
            '4.1. ЗАПРОС СКИДКИ',
        ],
        IncludeFields=[
            'Запрос скидки',
        ],
        Key='discount_request',
        PurchaseRate=.51,
        Priority=12
    ))
    PreReserved: StageItem = field(default_factory=lambda: StageItem(
        DisplayName='PreReserved',
        Documentation="""Предварительная бронь""",
        IncludeStages=[
            '4.2. ПРЕДВАРИТЕЛЬНАЯ БРОНЬ',
        ],
        IncludeFields=[
            'Предварительная бронь',
        ],
        Key='pre_reserved',
        PurchaseRate=.51,
        Priority=13
    ))
    PrePaid: StageItem = field(default_factory=lambda: StageItem(
        DisplayName='PrePaid',
        Documentation="""Есть предоплата""",
        IncludeStages=[
            '4.3. ЕСТЬ ПРЕДОПЛАТА',
        ],
        IncludeFields=[
            'Есть предоплата',
        ],
        Key='pre_paid',
        PurchaseRate=.85,
        Priority=14
    ))
    WaitingForArrival: StageItem = field(default_factory=lambda: StageItem(
        DisplayName='Waiting for arrival',
        Documentation="""Ожидаем приезда""",
        IncludeStages=[
            '5. БРОНЬ В КЛИНИКУ',
        ],
        IncludeFields=[
            'Ожидаем приезда',
        ],
        Key='waiting_for_arrival',
        PurchaseRate=.85,
        Priority=15
    ))
    Treatment: StageItem = field(default_factory=lambda: StageItem(
        DisplayName='Treatment',
        Documentation="""Лечение""",
        IncludeStages=[
            '6. СЕЙЧАС В КЛИНИКЕ',
        ],
        IncludeFields=[
            'Сейчас В клинике',
        ],
        Key='treatment',
        PurchaseRate=1,
        Priority=16
    ))
    Audit: StageItem = field(default_factory=lambda: StageItem(
        DisplayName='Audit',
        Documentation="""Выписан из клиники (аудит)""",
        IncludeStages=[
            '7. ВЫПИСАН ИЗ КЛИНИКИ (АУДИТ)',
        ],
        IncludeFields=[
            'Аудит',
        ],
        Key='audit',
        PurchaseRate=1,
        AtWork=False,
        Priority=17
    ))
    Purchase: StageItem = field(default_factory=lambda: StageItem(
        DisplayName='Purchase',
        Documentation="""Покупка""",
        IncludeStages=[
            'УСПЕШНО РЕАЛИЗОВАНО',
        ],
        IncludeFields=[
            'Продажа',
        ],
        Key='purchase',
        PurchaseRate=1,
        AtWork=False,
        Priority=18
    ))

    def __post_init__(self):
        super().__init__()


class CloseReasonSm(Enum):
    """ Причины потери лида, позволяющие квалифицировать его как целевого """
    Lost = 'Пропал (перестал выходить на связь)/не беспокоить'
    ChangedTheMind = 'Заморожен/передумал'
    Expensive = 'Нет денег/Цена не устраивает'
    TooYoung = 'До 4 лет или до 18кг'
    # WeDoNotCure = 'Не лечим заболевания'
    DangerToTransport = 'Нетранспортабельный'
    Location = 'Пугает страна/путешествие'
    FriendsDoNotRecommend = r'Врач\ родственники\ друзья не рекомендуют'
    Death = 'Смерть пациента'
    NegativeReactionAfterTreatment = 'Негатив после лечения'
    Undefined = 'Отказ консилиума'
    CalledCompetitor = 'Выбрал конкурента'
    WantsGuarantee = 'Хочет гарантий'
    SeeNoTreatmentResults = 'Нет результатов от лечения'
    ExpectsBetterResult = 'Ожидают лучшего результата'
    SerbianPatient = 'Сербия'
    SerbianPatient2 = 'Пациента Ведет Сербия'
    SerbianPatient3 = 'Пациент из Сербии'
    SerbianPatient4 = 'Сделку ведет В.Н.'
    # FailedToGetInTouch = 'Не смогли выйти на контакт'


@dataclass()
class LeadSM(Lead):
    """ Данные лида """
    CloseReason = CloseReasonSm
    Stage = StageSM
    AutodocsSheet = 'SM'

    AddedToArrivalTimetable: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Added to arrival timetable',
        Documentation="""Внесен в Arrival Timetable - берем из доп. полей""",
        Key='added_to_arrival_timetable',
        CustomField='Внесен в Arrival Timetable'
    ))
    Agent: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Agent',
        Documentation="""...""",
        Key='agent',
        CustomField='Agent'
    ))
    OfferSendingSpeed: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Offer sent in (days)',
        Documentation="""Через сколько дней после получения опросника был отправлен оффер""",
        Key='offer_sent_in_days'
    ))
    ArrivalChance: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Arrival chance',
        Documentation="""Шанс приезда""",
        Key='arrival_chance',
        CustomField='(%) Arrival chance'
    ))
    Budget: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Budget',
        Documentation="""Бюджет""",
        Key='budget',
        CustomField='Бюджет'
    ))
    Clinic: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Clinic',
        Documentation="""Клиника""",
        Key='clinic',
        CustomField='Клиника'
    ))
    ConsultingDoctor: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Consulting doctor',
        Documentation="""Консультирующий врач""",
        Key='consulting_doctor',
        CustomField='Консультирующий доктор'
    ))
    CuringDoctor: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Curing doctor',
        Documentation="""Лечащий врач""",
        Key='curing_doctor',
        CustomField='Лечащий врач'
    ))
    DateOfAdmission: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Date of admission',
        Documentation="""Дата посещения (начала лечения)""",
        Key='date_of_admission',
        CustomField='Дата начала лечения',
        IsDate=True
    ))
    DateOfOffer: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Date of offer',
        Documentation="""Дата отправки оффера""",
        Key='date_of_offer',
        CustomField='Отправили OFFER Пациенту.',
        IsDate=True
    ))
    DateOfQuestionnaireRecieved: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Date of questionnaire recieved',
        Documentation="""Дата отправки опросника""",
        Key='date_of_questionnaire_recieved',
        CustomField='Recieved Questionnair',
        IsDate=True
    ))
    DateOfPriorConsent: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Date of prior consent',
        Documentation="""Дата предварительного согласия""",
        Key='date_of_prior_consent',
        CustomField='Дата предварительного согласия',
        IsDate=True
    ))
    DateOfTreatmentEnd: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Date of treatment end',
        Documentation="""Дата завершения лечения (начала лечения)""",
        Key='date_of_treatment_end',
        CustomField='Дата завершения лечения',
        IsDate=True
    ))
    DaysAtTheClinic: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Days at the clinic',
        Documentation="""Количество дней, проведенных в клинике""",
        Key='days_at_the_clinic',
        CustomField='Days in Clinic (Stay duration)'
    ))
    Discount: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Discount',
        Documentation="""Скидка""",
        Key='discount',
        CustomField='Размер скидки'
    ))
    Duration30Days: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Продолжительность сделки 30 дней',
        Documentation='...',
        Key='duration_30_days'
    ))
    EDSS: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='EDSS',
        Documentation="""Инвалидность""",
        Key='edss',
        CustomField='EDSS'
    ))
    HAIncluded: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='HA included',
        Documentation="""...""",
        Key='ha_included',
        CustomField='Включен HA'
    ))
    GoogleID: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Google ID',
        Documentation="""Идентификатор клиента в рекламной системе Google - берем из доп. полей""",
        Key='google_id',
        CustomField='Google Client ID'
    ))
    Language: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Language',
        Documentation="""Язык лида - берем из доп. полей""",
        Key='language',
        CustomField='Spoken language'
    ))

    # показатели для Италии
    QuestionnaireRecieved14Days: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Questionnaire recieved 14 days',
        Documentation="""Получен опросник 14 дней""",
        Key='7_days_questionnaire_recieved'
    ))
    OfferSent21Days: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Offer sent 21 days',
        Documentation="""Отправлен оффер 21 дней""",
        Key='21_days_offer_sent'
    ))
    PriorConsent35Days: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='35 days prior consent',
        Documentation="""
            1 - если пациент дал предварительное согласие на лечение в течение 35 дней с момента создания сделки
        """,
        Key='35_days_prior_consent'
    ))

    OfferSent14Days: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Offer sent 14 days',
        Documentation="""Отправлен оффер 14 дней""",
        Key='14_days_offer_sent'
    ))
    QuestionnaireRecieved7Days: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Questionnaire recieved 7 days',
        Documentation="""Получен опросник 7 дней""",
        Key='7_days_questionnaire_recieved'
    ))
    PriorConsent28Days: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='28 days prior consent',
        Documentation="""
            1 - если пациент дал предварительное согласие на лечение в течение 28 дней с момента создания сделки
        """,
        Key='28_days_prior_consent'
    ))
    PatientFolder: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Patient folder',
        Documentation="""Папка Пациента - берем из доп. полей""",
        Key='patient_folder',
        CustomField='Папка Пациента'
    ))
    PaymentMethod: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Payment method',
        Documentation="""Способ оплаты - берем из доп. полей""",
        Key='payment_method',
        CustomField='Способ оплаты'
    ))
    PrePay: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Prepay ammount',
        Documentation="""Сумма предоплаты - берем из доп. полей""",
        Key='pre_pay',
        CustomField='Сумма предоплаты, Евро'
    ))
    Treatment: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Treatment',
        Documentation="""Болезнь, диагноз, направление - берем из доп. полей""",
        Key='treatment',
        CustomField='Disease'
    ))
    TreatmentIfOther: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Treatment (Other)',
        Documentation="""Болезнь, диагноз, направление - берем из доп. полей""",
        Key='treatment_if_other',
        CustomField='Disease if other'
    ))

    def __post_init__(self):
        super().__init__()
