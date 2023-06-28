""" Общие константы Amo, имеющие отношение к процессингу данных """
__author__ = 'ke.mizonov'
from typing import Callable
from app.amo.data.cdv.processor import DrvorobjevAmoProcessor
from app.amo.data.kazan.processor import KazanAmoProcessor
from app.amo.data.sm.processor import SwissmedicaAmoProcessor
from constants.constants import Branch

DATA_PROCESSOR = {
    Branch.CDV.value: DrvorobjevAmoProcessor,
    Branch.SM.value: SwissmedicaAmoProcessor,
    Branch.Kazan.value: KazanAmoProcessor,
}


def data_processor(branch: str) -> Callable:
    """ data-процессор """
    processor = DATA_PROCESSOR.get(branch)
    if not processor:
        raise Exception('Неизвестный data-процессор')
    return processor
