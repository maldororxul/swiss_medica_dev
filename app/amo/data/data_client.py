""" Общие константы Amo, имеющие отношение к процессингу данных """
__author__ = 'ke.mizonov'
from typing import Callable
from app.amo.data.cdv.client import DrvorobjevClient
from app.amo.data.sm.client import SwissmedicaClient
from constants.constants import Branch

DATA_CLIENT = {
    Branch.CDV.value: DrvorobjevClient,
    Branch.SM.value: SwissmedicaClient
}


def data_client(branch: str) -> Callable:
    """ data-клиент """
    api_client = DATA_CLIENT.get(branch)
    if not api_client:
        raise Exception('Неизвестный data-клиент')
    return api_client
