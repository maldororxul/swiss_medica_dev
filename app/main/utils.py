"""
Формат данных при смене статуса лида:
{
    'leads[status][0][id]': '23802129',
    'leads[status][0][status_id]': '47873533',
    'leads[status][0][pipeline_id]': '5389528',
    'leads[status][0][old_status_id]': '47888833',
    'leads[status][0][old_pipeline_id]': '5389528',
    'account[id]': '29013640',
    'account[subdomain]': 'drvorobjev'
}

"""
from typing import Dict
from app.amo.api.client import SwissmedicaAPIClient, DrvorobjevAPIClient
from app.amo.processor.processor import SMDataProcessor, CDVDataProcessor

API_CLIENT = {
    'swissmedica': SwissmedicaAPIClient,
    'drvorobjev': DrvorobjevAPIClient,
}

DATA_PROCESSOR = {
    'swissmedica': SMDataProcessor,
    'drvorobjev': CDVDataProcessor,
}


def parse_webhook_data(data: Dict):
    branch = data.get('account[subdomain]')
    processor = DATA_PROCESSOR.get(branch)()
    # реагируем только на изменение статусов
    if 'leads[status][0][old_status_id]' not in data and 'leads[status][0][status_id]' not in data:
        processor.log.add(text=f'Wrong event')
        return
    client = API_CLIENT.get(branch)()
    try:
        lead_data = client.get_lead_by_id(lead_id=data.get('leads[status][0][id]'))
        processor.log.add(text=f'Lead data: {type(lead_data)} {lead_data}'[:999])
        phones = processor.get_lead_phones(lead=lead_data, forced_contacts_update=True)
        processor.log.add(text=f'Phones: {phones}'[:999])
    except Exception as exc:
        processor.log.add(text=f'Error 2: {exc}'[:999])
