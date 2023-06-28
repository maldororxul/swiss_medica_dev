""" Константы Amo, имеющие отношение к API """
__author__ = 'ke.mizonov'
from enum import Enum


class AmoEvent(Enum):
    """ Типы событий Amo """
    Added = 'lead_added'
    # CustomFieldValueChanged = 'custom_field_value_changed'
    Deleted = 'lead_deleted'
    IncomeCall = 'incoming_call'
    IncomeChat = 'incoming_chat_message'
    Merged = 'entity_merged'
    OutcomeCall = 'outgoing_call'
    OutcomeChat = 'outgoing_chat_message'
    ResponsibleChanged = 'entity_responsible_changed'
    # SaleFieldChanged = 'sale_field_changed'
    StageChanged = 'lead_status_changed'


class AmoNote(Enum):
    """ Типы примечаний Amo """
    Email = 'amomail_message'
    OutcomeCall = 'call_out'
    IncomeCall = 'call_in'
    Common = 'common'
