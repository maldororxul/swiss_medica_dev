""" Контроллеры синхронизации данных с Amo """
__author__ = 'ke.mizonov'

from app.amo.api.sync_client import SwissmedicaAPIClient, DrvorobjevAPIClient

SYNC_CONTROLLER = {
    'sm': SwissmedicaAPIClient,
    'cdv': DrvorobjevAPIClient,
    'SM': SwissmedicaAPIClient,
    'CDV': DrvorobjevAPIClient,
    'swissmedica': SwissmedicaAPIClient,
    'drvorobjev': DrvorobjevAPIClient
}
