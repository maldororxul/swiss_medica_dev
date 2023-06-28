from dataclasses import dataclass
from enum import Enum
from app.amo.data.base.data_schema import Lead, LeadField, StageBase, StageItem


@dataclass()
class StageGrata(StageBase):
    """ Стадия воронки """
    RawLead: StageItem = StageItem(
        DisplayName='Сырой лид',
        Documentation="""Сырой лид, потенциальный клиент - этап сделки, через который проходят все заявки.""",
        IncludeStages=[],
        IncludeFields=[],
        Key='raw_lead',
        Priority=0
    )
    Lead: StageItem = StageItem(
        DisplayName='Лид',
        Documentation="""
            Лид, потенциальный клиент

            Исключения:
            - имеющие причину закрытия 'Duplicate Lead' (дубликаты) и 'SPAM'
            - удаленные (в том числе в результате объединения)

            Удаленные сделки выявляются по событиям в Amo.
        """,
        IncludeStages=[
            'первичный контакт'
        ],
        IncludeFields=[],
        Key='lead',
        Priority=1
    )
    FirstContact: StageItem = StageItem(
        DisplayName='Первичный контакт',
        Documentation="""...""",
        IncludeStages=[
            'первичный контакт'
        ],
        IncludeFields=[],
        Key='first_contact',
        Priority=2
    )
    Call: StageItem = StageItem(
        DisplayName='Звонок',
        Documentation="""...""",
        IncludeStages=[
            'звонок'
        ],
        IncludeFields=[],
        Key='call',
        Priority=3
    )
    Decision: StageItem = StageItem(
        DisplayName='Принимает решение',
        Documentation="""...""",
        IncludeStages=[
            'принимает решение'
        ],
        IncludeFields=[],
        Key='decision',
        Priority=4
    )
    Meeting: StageItem = StageItem(
        DisplayName='Встреча',
        Documentation="""...""",
        IncludeStages=[
            'Встреча'
        ],
        IncludeFields=[],
        Key='meeting',
        Priority=5
    )
    Agreement: StageItem = StageItem(
        DisplayName='Договор',
        Documentation="""...""",
        IncludeStages=[
            'Смета/договор'
        ],
        IncludeFields=[],
        Key='agreement',
        Priority=6
    )
    Success: StageItem = StageItem(
        DisplayName='Успешно реализовано',
        Documentation="""...""",
        IncludeStages=[
            'Успешно реализовано'
        ],
        IncludeFields=[],
        Key='success',
        Priority=7
    )
    Failed: StageItem = StageItem(
        DisplayName='Закрыто и не реализовано',
        Documentation="""...""",
        IncludeStages=[
            'Закрыто и не реализовано'
        ],
        IncludeFields=[],
        Key='failed',
        Priority=8
    )


class CloseReasonGrata(Enum):
    """ Причины потери лида """
    BuiltHouse = 'Готовый дом'
    ChangedTheMind = 'Передумал'
    Competitors = 'Конкуренты'
    Expensive = 'Дорого'
    FutureInterest = 'Отложенный интерес'
    Realtor = 'Риэлтор'
    # WrongTheme = 'Не то направление'


@dataclass()
class LeadGrata(Lead):
    """ Данные лида """
    CloseReason = CloseReasonGrata
    Stage = StageGrata

    Meeting28Days: LeadField = LeadField(
        DisplayName='Встреча в течение 28 дней',
        Documentation='...',
        Key='meeting_28_days'
    )
    Duration30Days: LeadField = LeadField(
        DisplayName='Продолжительность сделки 30 дней',
        Documentation='...',
        Key='duration_30_days'
    )
    FailedAndFutureInterest: LeadField = LeadField(
        DisplayName='Неуспешно закрыта + Отложенный интерес',
        Documentation='...',
        Key='failed_and_future_interest'
    )
    FailedAndBuiltHouse: LeadField = LeadField(
        DisplayName='Неуспешно закрыта + Готовый дом',
        Documentation='...',
        Key='failed_and_built_house'
    )

    CFLand: LeadField = LeadField(
        DisplayName='Земельный участок',
        Documentation='...',
        Key='Земельный участок',
        CustomField='Земельный участок'
    )
    CFFormOfPayment: LeadField = LeadField(
        DisplayName='Форма оплаты',
        Documentation='...',
        Key='Форма оплаты',
        CustomField='Форма оплаты'
    )
    CFApartmentInSale: LeadField = LeadField(
        DisplayName='квартира в продаже',
        Documentation='...',
        Key='квартира в продаже',
        CustomField='квартира в продаже'
    )
    CFFirstDeposit: LeadField = LeadField(
        DisplayName='Первоначальный взнос',
        Documentation='...',
        Key='Первоначальный взнос',
        CustomField='Первоначальный взнос'
    )
    CFHouseProject: LeadField = LeadField(
        DisplayName='Проект дома',
        Documentation='...',
        Key='Проект дома',
        CustomField='Проект дома'
    )
    CFClientClassification: LeadField = LeadField(
        DisplayName='Квалификация клиента',
        Documentation='...',
        Key='Квалификация клиента',
        CustomField='Квалификация клиента'
    )
    CFDeadline: LeadField = LeadField(
        DisplayName='Сроки строительства',
        Documentation='...',
        Key='Сроки строительства',
        CustomField='Сроки строительства'
    )
    CFBudget: LeadField = LeadField(
        DisplayName='Бюджет клиента',
        Documentation='...',
        Key='Бюджет клиента',
        CustomField='Бюджет клиента'
    )
    CFTRANID: LeadField = LeadField(
        DisplayName='TRANID',
        Documentation='...',
        Key='TRANID',
        CustomField='TRANID'
    )
    CFFORMNAME: LeadField = LeadField(
        DisplayName='FORMNAME',
        Documentation='...',
        Key='FORMNAME',
        CustomField='FORMNAME'
    )
    CFFORMID: LeadField = LeadField(
        DisplayName='FORMID',
        Documentation='...',
        Key='FORMID',
        CustomField='FORMID'
    )
    CFREFERER: LeadField = LeadField(
        DisplayName='REFERER',
        Documentation='...',
        Key='REFERER',
        CustomField='REFERER'
    )
    CFCHECKBOX: LeadField = LeadField(
        DisplayName='CHECKBOX',
        Documentation='...',
        Key='CHECKBOX',
        CustomField='CHECKBOX'
    )
    CFQUESTION1: LeadField = LeadField(
        DisplayName='QUESTION1',
        Documentation='...',
        Key='QUESTION1',
        CustomField='QUESTION1'
    )
    CFQUESTION2: LeadField = LeadField(
        DisplayName='QUESTION2',
        Documentation='...',
        Key='QUESTION2',
        CustomField='QUESTION2'
    )
    CFQUESTION3: LeadField = LeadField(
        DisplayName='QUESTION3',
        Documentation='...',
        Key='QUESTION3',
        CustomField='QUESTION3'
    )
    CFQUESTION4: LeadField = LeadField(
        DisplayName='QUESTION4-ALTERNATIVE',
        Documentation='...',
        Key='QUESTION4-ALTERNATIVE',
        CustomField='QUESTION4-ALTERNATIVE'
    )
    CFQUESTION5: LeadField = LeadField(
        DisplayName='QUESTION5',
        Documentation='...',
        Key='QUESTION5',
        CustomField='QUESTION5'
    )
    CFQUESTION6: LeadField = LeadField(
        DisplayName='QUESTION6',
        Documentation='...',
        Key='QUESTION6',
        CustomField='QUESTION6'
    )
    CFAge: LeadField = LeadField(
        DisplayName='Возраст',
        Documentation='...',
        Key='Возраст',
        CustomField='Возраст'
    )
    CFPlanningDeadline: LeadField = LeadField(
        DisplayName='Планируемый срок',
        Documentation='...',
        Key='Планируемый срок',
        CustomField='Планируемый срок'
    )
    CF_ym_uid: LeadField = LeadField(
        DisplayName='_ym_uid',
        Documentation='...',
        Key='_ym_uid',
        CustomField='_ym_uid'
    )
    CFyclid: LeadField = LeadField(
        DisplayName='yclid',
        Documentation='...',
        Key='yclid',
        CustomField='yclid'
    )
    CFWaysOfContact: LeadField = LeadField(
        DisplayName='КАК_С_ВАМИ_СВЯЗАТЬСЯ',
        Documentation='...',
        Key='КАК_С_ВАМИ_СВЯЗАТЬСЯ',
        CustomField='КАК_С_ВАМИ_СВЯЗАТЬСЯ'
    )
    CFName: LeadField = LeadField(
        DisplayName='NAME',
        Documentation='...',
        Key='NAME',
        CustomField='NAME'
    )
    CFAdvertisement: LeadField = LeadField(
        DisplayName='Объявление',
        Documentation='...',
        Key='Объявление',
        CustomField='Объявление'
    )
    CFAdvertisementURL: LeadField = LeadField(
        DisplayName='URL объявления',
        Documentation='...',
        Key='URL объявления',
        CustomField='URL объявления'
    )
    CFAgreement: LeadField = LeadField(
        DisplayName='Смета',
        Documentation='...',
        Key='Смета',
        CustomField='Смета'
    )
    CFMangoOfficeLine: LeadField = LeadField(
        DisplayName='Номер линии MANGO OFFICE',
        Documentation='...',
        Key='Номер линии MANGO OFFICE',
        CustomField='Номер линии MANGO OFFICE'
    )
