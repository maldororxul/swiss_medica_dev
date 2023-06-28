""" Клиент CDV для работы с данными из различных источников: AMO, телефония и проч. """
__author__ = 'ke.mizonov'
from app.amo.api.client import DrvorobjevAPIClient
from app.amo.data.base.client import Client


class DrvorobjevClient(Client):
    """ Клиент для работы с данными Drvorobjev """
    api_client = DrvorobjevAPIClient
    time_shift: int = 2
