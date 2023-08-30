from app.amo.api.client import SwissmedicaAPIClient, DrvorobjevAPIClient
from app.amo.processor.processor import SMDataProcessor, CDVDataProcessor
from app.models.autocall import SMAutocallNumber, CDVAutocallNumber

API_CLIENT = {
    'swissmedica': SwissmedicaAPIClient,
    'drvorobjev': DrvorobjevAPIClient,
}

DATA_PROCESSOR = {
    'swissmedica': SMDataProcessor,
    'drvorobjev': CDVDataProcessor,
}

AUTOCALL_NUMBER = {
    'swissmedica': SMAutocallNumber,
    'drvorobjev': CDVAutocallNumber,
}
