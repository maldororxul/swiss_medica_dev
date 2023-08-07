""" Прочие полезные функции """
__author__ = 'ke.mizonov'

import time
from typing import Dict, Callable, Tuple, Optional
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
    """
    leads[status][0][id] :: 23802129
    leads[status][0][status_id] :: 58841526
    leads[status][0][pipeline_id] :: 3508507
    leads[status][0][old_status_id] :: 58840350
    leads[status][0][old_pipeline_id] :: 7010970
    """
    branch = data.get('account[subdomain]')
    processor = DATA_PROCESSOR.get(branch)()
    pipeline_id = data.get('leads[status][0][pipeline_id]')
    pipeline = processor.get_pipeline_and_status_by_id(
        pipeline_id=pipeline_id,
        status_id=data.get('leads[status][0][status_id]')
    )
    return (
        str(pipeline_id),
        f"{pipeline.get('pipeline') or ''}\n"
        f"URGENT! Answered autocall: "
        f"https://{branch}.amocrm.ru/leads/detail/{data.get('leads[status][0][id]')}".strip()
    )


def handle_new_lead(data: Dict) -> Tuple[Optional[str], Optional[str]]:
    lead_id = data.get('leads[add][0][id]')
    event = 'New lead'
    key = 'add'
    if not lead_id:
        event = 'Lead moved'
        key = 'status'
        lead_id = data.get(f'leads[{key}][0][id]')
    if not lead_id:
        return None, None
    branch = data.get('account[subdomain]')
    processor = DATA_PROCESSOR.get(branch)()
    pipeline_id = data.get(f'leads[{key}][0][pipeline_id]')
    pipeline = processor.get_pipeline_and_status_by_id(
        pipeline_id=pipeline_id,
        status_id=data.get(f'leads[{key}][0][status_id]')
    )
    # проверка на дубли (находит первый дубль из возможных)
    amo_client = API_CLIENT.get(branch)()
    lead = amo_client.get_lead_by_id(lead_id=lead_id)
    contacts = []
    for contact in (lead.get('_embedded') or {}).get('contacts') or []:
        contacts.append(amo_client.get_contact_by_id(contact_id=contact['id']))
        time.sleep(0.25)
    lead['contacts'] = contacts
    duplicated = None
    for field_code in ('PHONE', 'EMAIL'):
        for contact in processor.get_lead_contacts(lead=lead, field_code=field_code):
            if len(contact) < 6:
                continue
            if field_code == 'EMAIL' and '@' not in contact:
                continue
            # processor.log.add(text=f"{field_code} :: {contact}")
            if not contact:
                continue
            for existing_lead in amo_client.find_leads(query=contact, limit=2) or []:
                if str(existing_lead['id']) != str(lead_id):
                    duplicated = existing_lead
                    break
            time.sleep(0.25)
            if duplicated:
                break
        if duplicated:
            break
    duplicate = f"Duplicate: https://{branch}.amocrm.ru/leads/detail/{duplicated['id']}" if duplicated else ''
    # прописываем тег "duplicated_lead"
    dup_tag = 'duplicated_lead'
    if duplicate:
        # обновляем теги текущего лида
        existing_tags = [
            {'name': tag['name']}
            for tag in (lead.get('_embedded') or {}).get('tags') or []
            if tag['name'] != dup_tag
        ]
        existing_tags.append({'name': dup_tag})
        amo_client.update_lead(lead_id=lead_id, data={'_embedded': {'tags': existing_tags}})
        # обновляем теги лида-дубля
        existing_tags = [
            {'name': tag['name']}
            for tag in (duplicated.get('_embedded') or {}).get('tags') or []
            if tag['name'] != dup_tag
        ]
        existing_tags.append({'name': dup_tag})
        amo_client.update_lead(lead_id=duplicated['id'], data={'_embedded': {'tags': existing_tags}})
    return (
        str(pipeline_id),
        f"{pipeline.get('pipeline') or ''}\n"
        f"{event}: https://{branch}.amocrm.ru/leads/detail/{lead_id}\n"
        f"{duplicate}".strip()
    )


def handle_get_in_touch(data: Dict) -> Tuple[Optional[str], Optional[str]]:
    """
    leads[status][0][id] :: 23802129
    leads[status][0][status_id] :: 58841526
    leads[status][0][pipeline_id] :: 3508507
    leads[status][0][old_status_id] :: 58840350
    leads[status][0][old_pipeline_id] :: 7010970
    """
    lead_id = data.get('leads[status][0][id]')
    if not lead_id:
        return None, None
    branch = data.get('account[subdomain]')
    processor = DATA_PROCESSOR.get(branch)()
    pipeline_id = data.get('leads[status][0][pipeline_id]')
    pipeline = processor.get_pipeline_and_status_by_id(
        pipeline_id=pipeline_id,
        status_id=data.get('leads[status][0][status_id]')
    )
    # получаем лид из Amo
    amo_client = API_CLIENT.get(branch)()
    lead = amo_client.get_lead_by_id(lead_id=lead_id)
    # получаем пользователя, ответственного за лид
    user = processor.get_user_by_id(user_id=lead.get('responsible_user_id'))
    created_at, updated_at = lead.get('created_at'), lead.get('updated_at')
    reaction_time = updated_at - created_at if created_at and updated_at else None
    if reaction_time:
        if reaction_time < 3600 * 12:
            reaction_time = time.strftime('%H:%M:%S', time.gmtime(reaction_time))
        else:
            reaction_time = 'over 12 hours'
    return (
        str(pipeline_id),
        f"{pipeline.get('pipeline') or ''}\n"
        f"Lead: https://{branch}.amocrm.ru/leads/detail/{lead_id} "
        f"Responsible: {user.name if user else ''}\n"
        f"Reaction time: {reaction_time or ''}".strip()
    )
