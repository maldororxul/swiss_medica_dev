""" Межмодульные константы """
__author__ = 'ke.mizonov'
from enum import Enum


class Branch(Enum):
    CDV = 'Dr Vorobjev'
    SM = 'Swiss Medica'
    CDVPsy = 'CDV Psychologists'
    Kazan = 'Kazan'


class GoogleSheets(Enum):
    Autodocs = '1FtUmL_q40vNr7-x43tuQ18slr6B8AIuLASdS_pPg-R0'
    MissedCalls = '1XBxLusLu9vlN2C4SfE1pG7PwBhEnlKvgDtKCVyXpWuo'
    MissedChatsKDV = '1XBxLusLu9vlN2C4SfE1pG7PwBhEnlKvgDtKCVyXpWuo'
    MissedChatsSM = '1GR1gXQPs8W8SeWX4frjFdagVluYjDx55AenJpHxjDI4'
    KmSettings = '10aAoXEOFXTFFdrOO-bYvQvh9pD4Vt1VYrtMhYHsYbzc'
    SeoDataCDV = '1IQoHDRkJpHPlFQSUYAXHF_xdmcE8A9VWI1CfJ8ouF-k'
    SeoDataSM = '1JufkKLDBlZMnMgP-pQKBS-tOp3AYIrL9OVf8eFrlmYo'
    UtmRulesCDV = '1blEKCs2rkNVlo7E61xvAwgrGeW3H_du-3nblbJCn6rs'
    UtmRulesSM = '11IDgZXK8LBA9UGIira8QWOlqjnPOKMV5F6y6ZEZujCE'
    ScheduleSM = '1ZnQwx14FMhzFogbvsc86AWAqY9XhRsMo7Y8kGbrrIEE'
    Managers = '1BZB73bLbFG-zm2aRPzmzJIrN0OlktOeOEx0fEl2fplA'


MISSED_CHATS_SHEET_ID = {
    Branch.CDV.value: GoogleSheets.MissedChatsKDV,
    Branch.SM.value: GoogleSheets.MissedChatsSM
}

CLOSE_REASON_FAILED = (
    '9. Закрыто и не реализовано',
    'ЗАКРЫТО И НЕ РЕАЛИЗОВАНО',
    'Closed and unrealized',
    'Закрыто и не реализовано',
    'Closed - lost'
)

CLOSE_REASON_SUCCESS = (
    'Successfully realized',
    'Успешно реализовано'
)
