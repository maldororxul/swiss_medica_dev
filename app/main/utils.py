""" Прочие полезные функции """
__author__ = 'ke.mizonov'
from typing import Dict, Callable, Tuple
from app.amo.api.client import SwissmedicaAPIClient, DrvorobjevAPIClient
from app.amo.processor.processor import SMDataProcessor, CDVDataProcessor

API_CLIENT = {
    'swissmedica': SwissmedicaAPIClient,
    'drvorobjev': DrvorobjevAPIClient,
}

DATA_PROCESSOR = {
    'drvorobjev': CDVDataProcessor,
    'swissmedica': SMDataProcessor,
}


def get_data_from_external_api(handler_func: Callable, request, **args):
    if request.content_type == 'application/json':
        data = request.json
    elif request.content_type == 'application/x-www-form-urlencoded':
        data = request.form.to_dict()
    else:
        return 'Unsupported Media Type', 415
    handler_func(data, **args)
    return 'success', 200


def handle_autocall_success(data: Dict) -> Tuple[str, str]:
    for k, v in data.items():
        print(f'{k} :: {v}')
    branch = data.get('account[subdomain]')
    processor = DATA_PROCESSOR.get(branch)()
    pipeline_id = data.get('leads[add][0][pipeline_id]')
    pipeline = processor.get_pipeline_and_status_by_id(
        pipeline_id=pipeline_id,
        status_id=data.get('leads[add][0][status_id]')
    )
    return (
        str(pipeline_id),
        f"{pipeline.get('pipeline') or ''}\n"
        f"URGENT! Lead answered (autocall): "
        f"https://swissmedica.amocrm.ru/leads/detail/{data.get('leads[add][0][id]')}".strip()
    )


def handle_new_lead(data: Dict) -> Tuple[str, str]:
    branch = data.get('account[subdomain]')
    processor = DATA_PROCESSOR.get(branch)()
    pipeline_id = data.get('leads[add][0][pipeline_id]')
    pipeline = processor.get_pipeline_and_status_by_id(
        pipeline_id=pipeline_id,
        status_id=data.get('leads[add][0][status_id]')
    )
    return (
        str(pipeline_id),
        f"{pipeline.get('pipeline') or ''}\n"
        f"New lead: https://swissmedica.amocrm.ru/leads/detail/{data.get('leads[add][0][id]')}".strip()
    )
