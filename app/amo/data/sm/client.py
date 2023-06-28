""" Клиент SM для работы с данными из различных источников: AMO, телефония и проч. """
__author__ = 'ke.mizonov'
from app.amo.api.client import SwissmedicaAPIClient
from app.amo.data.base.client import Client


class SwissmedicaClient(Client):
    """ Клиент для работы с данными Swissmedica """
    api_client = SwissmedicaAPIClient
    time_shift: int = 3
