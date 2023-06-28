""" Клиент SM для работы с данными из различных источников: AMO, телефония и проч. """
__author__ = 'ke.mizonov'
from app.amo.api.client import KazanAPIClient
from app.amo.data.base.client import Client


class KazanClient(Client):
    """ Клиент для работы с данными Swissmedica """
    api_client = KazanAPIClient
    time_shift: int = 3
