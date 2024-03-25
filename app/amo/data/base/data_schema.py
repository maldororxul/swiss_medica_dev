""" Константы данных AMO """
__author__ = 'ke.mizonov'
from dataclasses import dataclass, field, fields
from typing import Optional, List, Tuple, Union

DEBUG = False

PRICE = 'price'
TO = ' -> '


def clear_spaces(text: str) -> str:
    """ Чистит двойные пробелы в строке """
    while '  ' in text:
        text = text.replace('  ', ' ')
    text_spl = text.split('\n')
    text = '\n'.join([x.strip() for x in text_spl])
    while '\n\n\n' in text:
        text = text.replace('\n\n\n', '\n\n')
    return text.strip()


@dataclass()
class LeadField:
    """ Поле лида """
    CustomField: Optional[str] = field(init=True, default=None)
    DisplayName: str = field(init=True, default=NotImplemented)
    Documentation: str = field(init=True, default='')
    IsDate: bool = field(init=True, default=False)
    IsRaw: bool = field(init=True, default=False)
    Key: str = field(init=True, default=NotImplemented)

    # def __post_init__(self):
    #     self.Documentation = clear_spaces(self.Documentation)


@dataclass()
class StageItem:
    """ Стадия воронки """
    DisplayName: str = field(init=True, default=NotImplemented)
    Documentation: str = field(init=True, default='')
    Key: str = field(init=True, default=NotImplemented)
    # потенциальная конверсия в покупку
    PurchaseRate: float = field(init=True, default=0)
    # список названий этапов воронки, на которых стадия считается пройденной
    IncludeStages: List[str] = field(init=True, default_factory=list)
    # список доп. полей, по которым определяется достижение этапа воронки
    IncludeFields: List[str] = field(init=True, default_factory=list)
    AtWork: bool = field(init=True, default=True)
    # целевой показатель (будет дописан в DisplayedName)
    # TargetValue: Optional[Union[str, int, float]] = field(init=True, default=None)
    # приоритет: 1 - самый высокий
    Priority: Optional[int] = field(init=True, default=None)
    # убирать нумерацию стадий
    WithoutNum: bool = field(init=True, default=False)

    def __post_init__(self, *args, **kwargs):
        # добавляем префикс
        prefix = kwargs.get('prefix')
        if prefix:
            self.Key = f'{prefix}_{self.Key}'
            self.DisplayName = f'{self.DisplayName} [{prefix}]'
        # if self.TargetValue:
        #     self.DisplayName = f'{self.DisplayName} [{self.TargetValue}]'
        # if self.prefix:
        #     self.Key = f'{self.prefix}_{self.Key}'
        #     self.DisplayName = f'{self.DisplayName} [{self.prefix}]'
        # добавляем stage_num к ключу, если определен приоритет стадии
        if self.Priority is not None and self.WithoutNum is False:
            num = self.Priority if self.Priority > 9 else f'0{self.Priority}'
            self.Key = f'stage_{num}_{self.Key}'
        self.Date = f'{self.Key}_date'
        # Key - это данные, которые попадут в пивот, определяются доп. полями;
        #   KeyByStage - данные, необходимые для сравнения результатов, определяются фактом прохождения воронки
        self.KeyByStage = f'{self.Key}_reached'
        self.Price = f'{self.Key}_price'
        self.Alive = f'{self.Key}_alive'
        # планируемый доход, исходя из конверсии с текущего этапа в продажи
        self.PlannedIncome = f'{self.Key}_planned_income_(rate {self.PurchaseRate})'
        self.PlannedIncomeFull = f'{self.Key}_planned_income_full_(rate {self.PurchaseRate})'
        # планируемое кол-во клиентов
        self.PlannedCustomers = f'{self.Key}_planned_customers_(rate {self.PurchaseRate})'
        self.__build_documentation()

    def is_reached(self, value: Optional[str]) -> bool:
        """ Определяет, достигнута ли текущая стадия """
        return str(value).lower() in map(lambda x: x.lower(), self.IncludeStages)

    def __build_documentation(self):
        """ Составление документации с учетом информации о доп. полях и стадиях """
        # terms_label = f'\nУсловия достижения:\n' if self.IncludeFields or self.IncludeStages else ''
        additional_fields, include_stages = '', ''
        if self.IncludeFields:
            additional_fields = '[Условие] Заполнено одно из доп. полей:\n* ' + '\n* '.join(self.IncludeFields)
        if self.IncludeStages:
            include_stages = '[Доп. условие] Достигнут один из этапов воронки:\n* ' + '\n* '.join(self.IncludeStages)
        extra_keys = f'Дополнительно создаются поля:' \
                     f'\n* {self.Key}_price - доход от сделок на данном этапе' \
                     f'\n* {self.Key}_alive - сделка находится на текущем этапе в данный момент (1)' \
                     f'\n* {self.Key}_planned_income_(rate XX) - планируемый доход от сделок, находящихся сейчас на данном этапе' \
                     f'\n* {self.Key}_planned_income_full_(rate XX) - планируемый доход от сделок, находящихся сейчас на данном этапе, а также прошедших данный этап' \
                     f'\n* {self.Key}_planned_customers_(rate XX) - планируемое количество успешных сделок из числа находящихся на данном этапе'
        self.Documentation = clear_spaces(
            f'{self.Documentation}\n\n{additional_fields}\n\n{include_stages}\n\n{extra_keys}'
        )


# @dataclass()
# class StageItemExtended(StageItem):
#     def __post_init__(self):
#         # добавляем префикс
#         if self.prefix:
#             self.Key = f'{self.prefix}_{self.Key}'
#             self.DisplayName = f'{self.DisplayName} [{self.prefix}]'
#         super().__post_init__()


@dataclass()
class StageBase:
    """ Базовый класс, описывающий стадии воронки """
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
        IncludeStages=[],
        IncludeFields=[],
        Key='lead',
        Priority=1
    ))

    @classmethod
    def get_by_key(cls, value: Optional[str]) -> Optional[StageItem]:
        """ Получает StageItem по ключу """
        if not value:
            return None
        for key, stage_item in cls.__dict__.items():
            if key[:1] == '_' or isinstance(stage_item, classmethod):
                continue
            if stage_item.Key == value:
                return stage_item
        return None

    @classmethod
    def get_reached_stages(cls, values: Optional[List[Tuple[str, int]]]) -> List[Tuple[StageItem, int]]:
        """ По переданным названиям этапов воронки определяет,
                какие стадии и когда были достигнуты для данного лида """
        stages = []
        if DEBUG:
            print('reached:')
        for stage_name, time_value in values or []:
            if DEBUG:
                print('*', stage_name)
            for key, stage_item in cls.__dict__.items():
                if key[:1] == '_' or isinstance(stage_item, classmethod):
                    continue
                if not stage_item.is_reached(value=stage_name):
                    continue
                if DEBUG:
                    print('** reached', stage_name, key, stage_item)
                stages.append((stage_item, time_value))
        cls.__check_stages_priority(stages=stages)
        return stages

    @staticmethod
    def __check_stages_priority(stages: List[Tuple[StageItem, Union[int, str]]]):
        """ Проверяет последовательность этапов сделки:
                если заполнен следующий этап, то должен быть заполнен предыдущий
        """
        stages_names = [x[0] for x in stages]
        stages_priority = Lead.get_stages_priority()
        for i in range(len(stages_priority) - 1, -1, -1):
            stage = stages_priority[i]
            if stage in stages_names:
                for j in range(i - 1, -1, -1):
                    past_stage: StageItem = stages_priority[j]
                    if past_stage in stages_names:
                        continue
                    stages_names.append(past_stage)
                    stages.append((past_stage, ''))


@dataclass()
class Lead:
    """ Данные лида """
    Pipelines = []
    CloseReason = []
    Stage = StageBase
    AutodocsSheet: Optional[str] = None

    Id: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Id',
        Documentation='Идентификатор сделки из Amo',
        IsRaw=True,
        Key='id'
    ))
    CreatedAt: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Created at',
        Documentation='Дата создания сделки из Amo',
        IsRaw=True,
        Key='created_at',
        IsDate=True
    ))
    CreatedAtHour: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Created at (hour)',
        Documentation='Час создания сделки из Amo',
        Key='created_at_hour'
    ))
    UpdatedAt: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Updated at',
        Documentation='Дата последнего обновления сделки из Amo',
        IsRaw=True,
        Key='updated_at',
        IsDate=True
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
    ClosedAt: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Closed at',
        Documentation='Дата закрытия сделки из Amo',
        IsRaw=True,
        Key='closed_at',
        IsDate=True
    ))
    Name: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Name',
        Documentation='Название сделки из Amo',
        IsRaw=True,
        Key='name'
    ))
    Price: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Price',
        Documentation='Cтоимость сделки из Amo',
        IsRaw=True,
        Key='price'
    ))
    OnDuty: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Duty time',
        Documentation='1 - сделка создана в рабочее время',
        Key='duty_time'
    ))
    ReactionType: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Reaction type',
        Documentation="""
            Способ реакции на новый лид: звонок, email, заметка, перенос на стадию "пытаюсь связаться", закрытие сделки
        """,
        Key='reaction_type'
    ))
    CreationSource: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Creation source',
        Documentation="""
            Источник создания лида, определяемый по событиям (логика определена в классе CommunicationBase)
        """,
        Key='creation_source'
    ))
    FirstSuccessfulIncomingCall: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='First successful incoming call',
        Documentation="""
            Входящий звонок от клиента с ненулевой длительностью состоялся раньше любого ответного действия менеджера
        """,
        Key='first_successful_incoming_call'
    ))

    IncomingCallAttempt: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Incoming call attempt',
        Documentation='Количество попыток дозвониться (входящие)',
        Key='incoming_call_attempt'
    ))
    IncomingCallDuration: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Incoming call duration',
        Documentation='Суммарная длительность входящих звонков (2 - 150 мин)',
        Key='incoming_call_duration'
    ))
    OutgoingCallAttempt: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Outgoing call attempt',
        Documentation='Количество попыток дозвониться (исходящие)',
        Key='outgoing_call_attempt'
    ))
    OutgoingCallQuantity: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Outgoing call quantity',
        Documentation='Количество исходящих звонков (2 - 150 мин)',
        Key='outgoing_call_quantity'
    ))
    OutgoingCallDuration: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Outgoing call duration',
        Documentation='Суммарная длительность исходящих звонков (2 - 150 мин)',
        Key='outgoing_call_duration'
    ))
    IncomingChatQuantity: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Incoming chat quantity',
        Documentation='Количество входящих сообщений в чатах',
        Key='incoming_chat_quantity'
    ))
    OutgoingChatQuantity: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Outgoing chat quantity',
        Documentation='Количество исходящих сообщений в чатах',
        Key='outgoing_chat_quantity'
    ))
    IncomingEmailQuantity: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Incoming email quantity',
        Documentation='Количество входящих писем',
        Key='incoming_email_quantity'
    ))
    OutgoingEmailQuantity: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Outgoing email quantity',
        Documentation='Количество исходящих писем',
        Key='outgoing_email_quantity'
    ))

    ReactionTimeLess300: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Reaction time (<5 min)',
        Documentation='1 - если время первой реакции на новый лид в пределах 5 минут',
        Key='reaction_time_less_300'
    ))
    ReactionTimeGreater300: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Reaction time (>5 min)',
        Documentation='1 - если время первой реакции на новый лид больше 5 минут',
        Key='reaction_time_greater_300'
    ))
    ReactionTimeMissed: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='No reaction',
        Documentation='1 - если не обнаружена реакция на сделку',
        Key='no_reaction'
    ))

    CallbackTimeLess300: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Callback time (<5 min)',
        Documentation='1 - если время первого звонка в пределах 5 минут',
        Key='callback_time_less_300'
    ))
    CallbackTimeGreater300: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Callback time (>5 min)',
        Documentation='1 - если время первого звонка больше 5 минут',
        Key='callback_time_greater_300'
    ))
    CallbackTimeMissed: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='No callback',
        Documentation='1 - если не обнаружен звонок',
        Key='no_callback'
    ))

    ReactionTimeOnDuty: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Reaction time on duty, sec.',
        Documentation='Время первой реакции на новый лид, созданный в рабочее время (секунды)',
        Key='reaction_time_on_duty_sec'
    ))
    ReactionTimeOffDuty: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Reaction time off duty, sec.',
        Documentation='Время первой реакции на новый лид, созданный в нерабочее время (секунды)',
        Key='reaction_time_off_duty_sec'
    ))
    ReactionTimeOnDutyLess300: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Reaction time on duty (<5 min)',
        Documentation='1 - если время первой реакции на новый лид в пределах 5 минут в рабочее время',
        Key='reaction_time_on_duty_less_300'
    ))
    ReactionTimeOffDutyLess300: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Reaction time off duty (<5 min)',
        Documentation='1 - если время первой реакции на новый лид в пределах 5 минут в нерабочее время',
        Key='reaction_time_on_duty_less_300'
    ))
    ReactionTimeOnDutyGreater300: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Reaction time on duty (>5 min)',
        Documentation='1 - если время первой реакции на новый лид больше 5 минут в рабочее время',
        Key='reaction_time_on_duty_greater_300'
    ))
    ReactionTimeOffDutyGreater300: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Reaction time off duty (>5 min)',
        Documentation='1 - если время первой реакции на новый лид больше 5 минут в нерабочее время',
        Key='reaction_time_on_duty_greater_300'
    ))
    ReactionTimeOnDutyMissed: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='No reaction on duty',
        Documentation='1 - если не обнаружена реакция на сделку в рабочее время',
        Key='no_reaction_on_duty'
    ))
    ReactionTimeOffDutyMissed: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='No reaction off duty',
        Documentation='1 - если не обнаружена реакция на сделку в нерабочее время',
        Key='no_reaction_off_duty'
    ))
    
    CallbackTimeOnDutyLess300: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Callback time on duty (<5 min)',
        Documentation='1 - если время первой реакции (исходящего звонка) в пределах 5 минут в рабочее время',
        Key='callback_time_on_duty_less_300'
    ))
    CallbackTimeOffDutyLess300: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Callback time off duty (<5 min)',
        Documentation='1 - если время первой реакции (исходящего звонка) в пределах 5 минут в нерабочее время',
        Key='callback_time_on_duty_less_300'
    ))
    CallbackTimeOnDutyGreater300: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Callback time on duty (>5 min)',
        Documentation='1 - если время первой реакции (исходящего звонка) больше 5 минут в рабочее время',
        Key='callback_time_on_duty_greater_300'
    ))
    CallbackTimeOffDutyGreater300: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Callback time off duty (>5 min)',
        Documentation='1 - если время первой реакции (исходящего звонка) больше 5 минут в нерабочее время',
        Key='callback_time_on_duty_greater_300'
    ))
    CallbackTimeOnDutyMissed: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='No callback on duty',
        Documentation='1 - если не обнаружена реакция на сделку в рабочее время',
        Key='no_callback_on_duty'
    ))
    CallbackTimeOffDutyMissed: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='No callback off duty',
        Documentation='1 - если не обнаружена реакция на сделку в нерабочее время',
        Key='no_callback_off_duty'
    ))

    LongestCallDuration: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Longest call duration',
        Documentation="""
            Длительность самого долгого звонка из состоявшихся (сек)

            Информация о звонках берется из примечаний к лидам
        """,
        Key='longest_call_duration'
    ))
    LongestCallLink: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Longest call link',
        Documentation="""
            Ссылка на скачивание самого долгого звонка из состоявшихся (сек)

            Информация о звонках берется из примечаний к лидам
        """,
        Key='longest_call_link'
    ))
    PurchaseExtended: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Purchase extended',
        Documentation="""Продажа, включая в клинике и выписан из клиники""",
        Key='purchase_extended'
    ))
    PurchaseExtendedPrice: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Purchase extended price',
        Documentation="""Выручка от продажи, включая в клинике и выписан из клиники""",
        Key='purchase_extended_price'
    ))
    AllAlive: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='All alive',
        Documentation="""Все активные на данный момент лиды""",
        Key='all_alive'
    ))
    AtWork: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='At work',
        Documentation="""Сумма активных лидов в работе""",
        Key='at_work'
    ))
    AtWorkAnyPipeline: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='At work any pipeline',
        Documentation="""Сумма активных лидов в работе (в любой воронке)""",
        Key='at_work_any_pipeline'
    ))
    Phone: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Phone',
        Documentation='Список телефонов',
        Key='phone'
    ))

    # NoInteraction: LeadField = LeadField(
    #     DisplayName='No interaction',
    #     Documentation='Лид, у которого нет события с входящими или исходящими чатами или звонками',
    #     Key='no_interaction'
    # )
    # Outgoing: LeadField = LeadField(
    #     DisplayName='Outgoing',
    #     Documentation='Лид с первым исходящим звонком или сообщением',
    #     Key='outgoing'
    # )
    # OutgoingProblem: LeadField = LeadField(
    #     DisplayName='Outgoing (problem)',
    #     Documentation='Лид с первым исходящим звонком или сообщением (возникла проблема)',
    #     Key='outgoing_problem'
    # )
    # OutgoingProblemVOIP: LeadField = LeadField(
    #     DisplayName='Outgoing (problem, voip)',
    #     Documentation='Лид с первым исходящим звонком или сообщением (возникла проблема)',
    #     Key='outgoing_problem_voip'
    # )
    # Incoming: LeadField = LeadField(
    #     DisplayName='Incoming',
    #     Documentation='Лид с первым входящим звонком или сообщением',
    #     Key='incoming'
    # )
    # IncomingOnDuty: LeadField = LeadField(
    #     DisplayName='Incoming (duty time)',
    #     Documentation='Лид с входящим звонком или сообщением (в рабочее время)',
    #     Key='incoming_duty_time'
    # )
    # SlowReaction: LeadField = LeadField(
    #     DisplayName='Reaction time (>5 min)',
    #     Documentation='Время реакции на новый лид (более 5 минут)',
    #     Key='reaction_time_slow'
    # )
    # SlowReactionOnDuty: LeadField = LeadField(
    #     DisplayName='Reaction time (>5 min, duty time)',
    #     Documentation='Время реакции на новый лид (более 5 минут, в рабочее время)',
    #     Key='reaction_time_slow_duty_time'
    # )
    # FastReaction: LeadField = LeadField(
    #     DisplayName='Reaction time (<5 min).',
    #     Documentation='Время реакции на новый лид (менее 5 минут)',
    #     Key='reaction_time_5_min'
    # )
    # FastOutgoingReaction: LeadField = LeadField(
    #     DisplayName='Outgoing reaction (<60 min).',
    #     Documentation='Время реакции на новый лид (менее 60 минут)',
    #     Key='outgoing_reaction_60_min'
    # )
    # FastOutgoingReactionVOIP2: LeadField = LeadField(
    #     DisplayName='Outgoing reaction (<2 min, voip)',
    #     Documentation='Время реакции на новый лид по данным телефонии (менее 2 минут)',
    #     Key='outgoing_reaction_fast_voip_2_min'
    # )
    # FastOutgoingReactionVOIP5: LeadField = LeadField(
    #     DisplayName='Outgoing reaction (<5 min, voip)',
    #     Documentation='Время реакции на новый лид по данным телефонии (менее 5 минут)',
    #     Key='outgoing_reaction_fast_voip_5_min'
    # )
    # FastOutgoingReactionVOIP60: LeadField = LeadField(
    #     DisplayName='Outgoing reaction (<60 min, voip)',
    #     Documentation='Время реакции на новый лид по данным телефонии (менее 60 минут)',
    #     Key='outgoing_reaction_fast_voip_60_min'
    # )
    # SlowOutgoingReaction: LeadField = LeadField(
    #     DisplayName='Outgoing reaction (>60 min)',
    #     Documentation='Время реакции на новый лид (более 60 минут)',
    #     Key='outgoing_reaction_slow'
    # )
    # SlowOutgoingReactionVOIP2: LeadField = LeadField(
    #     DisplayName='Outgoing reaction (>2 min, voip)',
    #     Documentation='Время реакции на новый лид по данным телефонии (более 2 минут)',
    #     Key='outgoing_reaction_slow_voip_2_min'
    # )
    # SlowOutgoingReactionVOIP5: LeadField = LeadField(
    #     DisplayName='Outgoing reaction (>5 min, voip)',
    #     Documentation='Время реакции на новый лид по данным телефонии (более 5 минут)',
    #     Key='outgoing_reaction_slow_voip_5_min'
    # )
    # SlowOutgoingReactionVOIP60: LeadField = LeadField(
    #     DisplayName='Outgoing reaction (>60 min, voip)',
    #     Documentation='Время реакции на новый лид по данным телефонии (более 60 минут)',
    #     Key='outgoing_reaction_slow_voip_60_min'
    # )
    # FastReactionOnDuty: LeadField = LeadField(
    #     DisplayName='Reaction time (<5 min, duty time)',
    #     Documentation='Время реакции на новый лид (менее 5 минут, в рабочее время)',
    #     Key='reaction_time_5_min_duty_time'
    # )
    # NoReaction: LeadField = LeadField(
    #     DisplayName='No reaction',
    #     Documentation='Есть входящий звонок или чат, но в истории лида нет исходящего ответа',
    #     Key='no_reaction'
    # )
    # NoReactionOnDuty: LeadField = LeadField(
    #     DisplayName='No reaction (duty time)',
    #     Documentation='Есть входящий звонок или чат, но в истории лида нет исходящего ответа (в рабочее время)',
    #     Key='no_reaction_duty_time'
    # )
    # ImmidiateReaction: LeadField = LeadField(
    #     DisplayName='Incoming call/chat or Lead was merged',
    #     Documentation="""
    #         Мгновенная реакция на новый лид, либо лид не нуждается в реакции
    #
    #         Это может быть объединенный лид, либо лид, созданный по входящему звонку или чату
    #     """,
    #     Key='reaction_time_0_min'
    # )
    Responsible: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Responsible',
        Documentation="""
            Имя ответственного пользователя (менеджера)

            Заполняется из справочника пользователей на основе идентификатора пользователя, известного из сделки
        """,
        Key='responsible_user_name'
    ))
    ResponsibleGroup: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Responsible Group',
        Documentation="""
            Группа ответственного пользователя (менеджера)

            Заполняется из справочника пользователей на основе идентификатора пользователя, известного из сделки
        """,
        Key='responsible_group'
    ))
    Deleted: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Deleted leads',
        Documentation="""
            Лид был удален
            
            Сверка происходит по событиям
        """,
        Key='deleted_leads'
    ))
    ClosedIn: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Closed in',
        Documentation="""
            Время в днях, прошедшее с момента создания лида до его закрытия
        """,
        Key='closed_in'
    ))
    DeletedBy: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Deleted by',
        Documentation="""
            Ответственный за удаление лида
    
            Сверка происходит по событиям и справочнику пользователей
        """,
        Key='deleted_by'
    ))
    InputField: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Input',
        Documentation="""
            Доп. поле INPUT

            Харнит данные форм захвата
        """,
        Key='input_field'
    ))
    LossReason: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Loss reason',
        Documentation="""
            Причина закрытия
            
            Получается из справочника причин закрытия Amo на основе идентификатора причины закрытия
        """,
        Key='loss_reason'
    ))
    PipelineName: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Pipeline name',
        Documentation="""
            Название воронки

            Получаем из справочника воронок Amo по известному идентификатору воронки, в которой находится данная сделка
        """,
        Key='pipeline_name'
    ))
    StatusName: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Status name',
        Documentation="""
            Название этапа воронки

            Получаем из справочника воронок Amo по известному идентификатору статуса, в котором находится данная сделка
        """,
        Key='status_name'
    ))
    Link: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Link',
        Documentation="""Ссылка на сделку - строится, исходя из известного поддомена и идентификатора""",
        Key='link_to_amo'
    ))
    Tags: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Tags',
        Documentation="""Тэги - те самые, что отображаются в Amo""",
        Key='tags'
    ))
    Jivo: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Jivo',
        Documentation="""1 - если в тегах встречается jivo""",
        Key='jivo'
    ))
    DateUnrealized: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Date unrealized',
        Documentation="""Дата неуспешного закрытия сделки""",
        Key='date_unrealized',
        IsDate=True
    ))
    DateReanimated: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Date reanimated',
        Documentation="""Дата реанимации лида""",
        Key='date_reanimated',
        IsDate=True
    ))
    DateRealizedAfterReanimation: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='Date realized after reanimation',
        Documentation="""Дата успешного закрытия сделки после реанимации""",
        Key='date_realized_after_reanimation',
        IsDate=True
    ))
    FirstOutgoingCallDateTime: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='First outgoing call date time',
        Documentation="""
            Дата / время первого исходящего звонка

            Сверка по отчетам телефонии, номер телефона берется из контактов
        """,
        Key='first_outgoing_call_datetime'
    ))
    FirstOutgoingCallReactionTime: LeadField = field(default_factory=lambda: LeadField(
        DisplayName='First outgoing call reaction time',
        Documentation="""
            Дата / время первого исходящего звонка - дата / время создания лида

            Сверка по отчетам телефонии, номер телефона берется из контактов
        """,
        Key='first_outgoing_call_reaction_time'
    ))

    @classmethod
    def get_loss_reasons(cls) -> Tuple:
        """ Причина закрытия / потери лида """
        return tuple([reason.value for reason in cls.CloseReason])

    @dataclass(frozen=True)
    class Utm:
        """ Utm-метки """
        Creative: LeadField = field(default_factory=lambda: LeadField(
            DisplayName='utm_creative',
            Documentation="""""",
            Key='utm_creative'
        ))
        Device: LeadField = field(default_factory=lambda: LeadField(
            DisplayName='utm_device',
            Documentation="""""",
            Key='utm_device'
        ))
        Match: LeadField = field(default_factory=lambda: LeadField(
            DisplayName='utm_match',
            Documentation="""""",
            Key='utm_match'
        ))
        Source: LeadField = field(default_factory=lambda: LeadField(
            DisplayName='utm_source',
            Documentation="""""",
            Key='utm_source'
        ))
        Medium: LeadField = field(default_factory=lambda: LeadField(
            DisplayName='utm_medium',
            Documentation="""""",
            Key='utm_medium'
        ))
        Term: LeadField = field(default_factory=lambda: LeadField(
            DisplayName='utm_term',
            Documentation="""""",
            Key='utm_term'
        ))
        Campaign: LeadField = field(default_factory=lambda: LeadField(
            DisplayName='utm_campaign',
            Documentation="""""",
            Key='utm_campaign'
        ))
        Placement: LeadField = field(default_factory=lambda: LeadField(
            DisplayName='utm_placement',
            Documentation="""""",
            Key='utm_placement'
        ))
        Referer: LeadField = field(default_factory=lambda: LeadField(
            DisplayName='utm_referer',
            Documentation="""""",
            Key='utm_referer'
        ))
        Network: LeadField = field(default_factory=lambda: LeadField(
            DisplayName='utm_network',
            Documentation="""""",
            Key='utm_network'
        ))
        Target: LeadField = field(default_factory=lambda: LeadField(
            DisplayName='utm_target',
            Documentation="""""",
            Key='utm_target'
        ))
        Position: LeadField = field(default_factory=lambda: LeadField(
            DisplayName='utm_position',
            Documentation="""""",
            Key='utm_position'
        ))
        Content: LeadField = field(default_factory=lambda: LeadField(
            DisplayName='utm_content',
            Documentation="""""",
            Key='utm_content'
        ))
        YM_CID: LeadField = field(default_factory=lambda: LeadField(
            DisplayName='ym_cid',
            Documentation="""""",
            Key='ym_cid'
        ))

        @classmethod
        def get_keys(cls):
            keys = []
            for field_name, field_definition in cls.__dataclass_fields__.items():
                default_factory = field_definition.default_factory
                if callable(default_factory):
                    field_instance = default_factory()
                    if isinstance(field_instance, LeadField):
                        keys.append(field_instance.Key)
            return keys

    # @dataclass()
    # class Stage(StageBase):
    #     """ Стадия воронки """

    # @classmethod
    # def get_by_status(cls, value: str) -> Optional[StageItem]:
    #     """ Получает StageItem по имени стадии в Amo """
    #     print('value', value)
    #     priorities = cls.__get_stages_priority()
    #     print('priorities', priorities)
    #     for stage in priorities:
    #         stage_item: StageItem = stage['stage']
    #         print(stage_item.IncludeStages)
    #         if value in stage_item.IncludeStages:
    #             return stage_item
    #     return None

    @classmethod
    def get_date_fields(cls):
        """ Генератор полей лида, содержащих даты """
        instance = cls()
        for _field in fields(cls):
            value = getattr(instance, _field.name)
            if isinstance(value, LeadField) and value.IsDate:
                yield value

    @classmethod
    def get_fields(cls):
        """ Генератор всех полей лида """
        instance = cls()
        for _field in fields(cls):
            value = getattr(instance, _field.name)
            if isinstance(value, LeadField):
                yield value

    @classmethod
    def get_custom_fields(cls):
        """ Генератор дополнительных полей лида """
        instance = cls()
        for _field in fields(cls):
            value = getattr(instance, _field.name)
            if isinstance(value, LeadField) and value.CustomField:
                yield value

    @classmethod
    def get_raw_fields(cls):
        """ Генератор "сырых" полей лида - то есть тех, которые берутся непосредственно из сделки Amo """
        instance = cls()
        for _field in fields(cls):
            value = getattr(instance, _field.name)
            if isinstance(value, LeadField) and value.IsRaw:
                yield value

    @classmethod
    def get_stages_priority(cls) -> Tuple:
        """ Возвращает кортеж стадий воронки лида, отсортированных по порядку прохождения """
        priorities = cls.__get_stages_priority()
        return tuple(x['field'] for x in priorities)

    @classmethod
    def get_documentation(cls):
        result = {x.Key: x.Documentation for x in cls.get_raw_fields()}
        result.update({x.Key: x.Documentation for x in cls.get_fields()})
        result.update({x.Key: x.Documentation for x in cls.get_stages_priority()})
        result.update({x['field'].Key: x['field'].Documentation for x in cls.__get_utms()})
        return result

    @classmethod
    def __get_stages_priority(cls) -> List:
        """ Возвращает список стадий воронки лида, отсортированных по порядку прохождения """
        priorities = []
        instance = cls.Stage()
        for _field in fields(cls.Stage):
            value = getattr(instance, _field.name)
            if isinstance(value, StageItem) and value.Priority is not None:
                priorities.append({'priority': value.Priority, 'field': value})
        # for val in cls.Stage.__dict__.get('__dataclass_fields__').values():
        #     if isinstance(val.default_factory, StageItem) and val.default_factory.Priority is not None:
        #         priorities.append({'priority': val.default_factory.Priority, 'field': val.default_factory})
        priorities = [val for val in sorted(priorities, key=lambda x: x['priority'])]
        # print('---', priorities)
        return priorities

    @classmethod
    def __get_utms(cls) -> List:
        """ Возвращает список меток """
        utm = []
        instance = cls.Utm()
        for _field in fields(cls.Utm):
            value = getattr(instance, _field.name)
            if isinstance(value, LeadField):
                utm.append({'field': value})
        # for val in cls.Utm.__dict__.get('__dataclass_fields__').values():
        #     if isinstance(val.default, LeadField):
        #         utm.append({'field': val.default})
        return utm


# fixme предметы кластеризации
CLUSTER_SUBJECT = (
    None,
    # Lead.Responsible,
    # # Lead.Treatment,
    # # Lead.Country,
    # Lead.Tags,
    # Lead.Utm.Medium,
    # Lead.Utm.Target,
    # Lead.Utm.Term,
    # Lead.Utm.Match,
    # Lead.Utm.Source,
    # Lead.Utm.Campaign,
    # Lead.Utm.Content,
    # Lead.Utm.Creative,
    # Lead.Utm.Device,
    # Lead.Utm.Network,
    # Lead.Utm.Placement,
    # Lead.Utm.Position,
    # Lead.Utm.Referer,
)
