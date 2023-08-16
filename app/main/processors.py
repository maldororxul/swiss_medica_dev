""" Пост-процессоры для работы с данными Amo """
__author__ = 'ke.mizonov'
from app.amo.processor.processor import SMDataProcessor, CDVDataProcessor

DATA_PROCESSOR = {
    'sm': SMDataProcessor,
    'cdv': CDVDataProcessor,
    'swissmedica': SMDataProcessor,
    'drvorobjev': CDVDataProcessor,
}
