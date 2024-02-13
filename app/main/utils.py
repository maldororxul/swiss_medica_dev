""" Прочие полезные функции """
__author__ = 'ke.mizonov'
import time
from datetime import date, datetime
from typing import Dict, Callable, Tuple, Optional
from app.amo.api.client import SwissmedicaAPIClient, DrvorobjevAPIClient
from app.amo.processor.processor import SMDataProcessor, CDVDataProcessor
from app.google_api.client import GoogleAPIClient
from config import Config
from modules.constants.constants.constants import GoogleSheets

DUP_TAG = 'duplicated_lead'

API_CLIENT = {
    'SM': SwissmedicaAPIClient,
    'CDV': DrvorobjevAPIClient,
    'sm': SwissmedicaAPIClient,
    'cdv': DrvorobjevAPIClient,
    'swissmedica': SwissmedicaAPIClient,
    'drvorobjev': DrvorobjevAPIClient,
}

DATA_PROCESSOR = {
    'drvorobjev': CDVDataProcessor,
    'swissmedica': SMDataProcessor,
}


class DateTimeEncoder:
    @staticmethod
    def encode(obj):
        for k, v in obj.items():
            if isinstance(v, (date, datetime)):
                obj[k] = v.isoformat()
        return obj

    @staticmethod
    def decode(obj):
        for k, v in obj.items():
            if isinstance(v, str):
                try:
                    obj[k] = datetime.fromisoformat(v)
                except ValueError:
                    try:
                        obj[k] = date.fromisoformat(v)
                    except ValueError:
                        pass
        return obj


def get_data_from_external_api(handler_func: Callable, request, **args):
    if request.content_type == 'application/json':
        data = request.json
    elif request.content_type == 'application/x-www-form-urlencoded':
        data = request.form.to_dict()
    else:
        return 'Unsupported Media Type', 415
    handler_func(data, **args)
    return 'success', 200


def handle_autocall_success(data: Dict) -> Tuple[str, str, str]:
    """
    leads[status][0][id] :: 23802129
    leads[status][0][status_id] :: 58841526
    leads[status][0][pipeline_id] :: 3508507
    leads[status][0][old_status_id] :: 58840350
    leads[status][0][old_pipeline_id] :: 7010970
    """
    lead_id = data.get('account[status]')
    branch = data.get('account[subdomain]')
    processor = DATA_PROCESSOR.get(branch)()
    pipeline_id = data.get('leads[status][0][pipeline_id]')
    pipeline = processor.get_pipeline_and_status_by_id(
        pipeline_id=pipeline_id,
        status_id=data.get('leads[status][0][status_id]')
    )
    # проверка на дубли (находит первый дубль из возможных)
    amo_client = API_CLIENT.get(branch)()
    lead = amo_client.get_lead_by_id(lead_id=lead_id)
    existing_tags = [
        {'name': tag['name']}
        for tag in (lead.get('_embedded') or {}).get('tags') or []
        if tag['name'] != DUP_TAG
    ]
    duplicate = check_for_duplicated_leads(
        processor=processor,
        lead=lead,
        amo_client=amo_client,
        branch=branch,
        existing_tags=existing_tags
    )
    # получаем пользователя, ответственного за лид
    user = processor.get_user_by_id(user_id=lead.get('responsible_user_id'))
    tags_str = ', '.join([tag['name'] for tag in existing_tags])
    if tags_str:
        tags_str = f'{tags_str}'
    return (
        'NEW_LEAD',
        str(pipeline_id),
        f"{pipeline.get('pipeline') or ''} :: {pipeline.get('status') or ''}\n"
        f"URGENT! Answered autocall: "
        f"https://{branch}.amocrm.ru/leads/detail/{data.get('leads[status][0][id]')}\n"
        f"Tags: {tags_str}\n"
        f"Responsible: {user.name if user else ''}\n"
        f"{duplicate}".strip()
    )


def handle_new_lead_slow_reaction(data: Dict) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    lead_id = data.get('leads[add][0][id]')
    event = 'Need to insure'
    key = 'add'
    if not lead_id:
        key = 'status'
        lead_id = data.get(f'leads[{key}][0][id]')
    if not lead_id:
        return None, None, None
    branch = data.get('account[subdomain]')
    processor = DATA_PROCESSOR.get(branch)()
    pipeline_id = data.get(f'leads[{key}][0][pipeline_id]')
    pipeline = processor.get_pipeline_and_status_by_id(
        pipeline_id=pipeline_id,
        status_id=data.get(f'leads[{key}][0][status_id]')
    )
    # return (
    #     'NEED_TO_INSURE',
    #     str(pipeline_id),
    #     f"{pipeline.get('pipeline') or ''}\n"
    #     f"{event}: https://{branch}.amocrm.ru/leads/detail/{lead_id}\n"
    # )
    # проверка на дубли (находит первый дубль из возможных)
    amo_client = API_CLIENT.get(branch)()
    lead = amo_client.get_lead_by_id(lead_id=lead_id)
    existing_tags = [
        {'name': tag['name']}
        for tag in (lead.get('_embedded') or {}).get('tags') or []
        if tag['name'] != DUP_TAG
    ]
    # получаем пользователя, ответственного за лид
    user = processor.get_user_by_id(user_id=lead.get('responsible_user_id'))
    tags_str = ', '.join([tag['name'] for tag in existing_tags])
    if tags_str:
        tags_str = f'{tags_str}'
    duplicate = check_for_duplicated_leads(
        processor=processor,
        lead=lead,
        amo_client=amo_client,
        branch=branch,
        existing_tags=existing_tags
    )
    return (
        'NEED_TO_INSURE',
        str(pipeline_id),
        f"{pipeline.get('pipeline') or ''} :: {pipeline.get('status') or ''}\n"
        f"{event}: https://{branch}.amocrm.ru/leads/detail/{lead_id}\n"
        f"Tags: {tags_str}\n"
        f"Responsible: {user.name if user else ''}\n"
        f"{duplicate}".strip()
    )


def check_for_duplicated_leads(processor, lead, amo_client, branch, existing_tags) -> str:
    contacts = []
    for contact in (lead.get('_embedded') or {}).get('contacts') or []:
        contacts.append(amo_client.get_contact_by_id(contact_id=contact['id']))
        time.sleep(0.25)
    lead['contacts'] = contacts
    duplicated = None
    for field_code in ('PHONE', 'EMAIL'):
        for contact in processor.get_lead_contacts(lead=lead, field_code=field_code):
            if not contact or len(contact) < 6:
                continue
            if field_code == 'EMAIL' and '@' not in contact:
                continue
            # processor.log.add(text=f"{field_code} :: {contact}")
            if not contact:
                continue
            for existing_lead in amo_client.find_leads(query=contact, limit=2) or []:
                if str(existing_lead['id']) != str(lead['id']):
                    duplicated = existing_lead
                    break
            time.sleep(0.25)
            if duplicated:
                break
        if duplicated:
            break
    duplicate = ''
    if duplicated:
        _embedded = duplicated.get('_embedded') or {}
        loss_reason = _embedded.get('loss_reason')
        is_spam = loss_reason[0]['name'] in ('SPAM', 'СПАМ') if loss_reason else False
        # получаем пользователя, ответственного за лид
        duplicated_user = amo_client.get_user(_id=duplicated.get('responsible_user_id'))
        duplicate = f"*Duplicate*: https://{branch}.amocrm.ru/leads/detail/{duplicated['id']}\n" \
                    f"*Responsible for duplicate*: {duplicated_user.get('name') if duplicated_user else '???'}"
        if is_spam:
            duplicate = f'{duplicate}\nPROBABLY SPAM!'
        else:
            # перемещаем лид
            try:
                if duplicated.get('loss_reason_id') and duplicated.get('closed_at'):
                    move_lead_to_continue_to_work(lead=duplicated, branch=branch, amo_client=amo_client)
            except Exception as exc:
                print('failed to move lead', exc)
        # обновляем теги текущего лида, прописываем тег "duplicated_lead"
        pass
        # existing_tags.append({'name': DUP_TAG})
        # amo_client.update_lead(lead_id=lead_id, data={'_embedded': {'tags': existing_tags}})
        # обновляем теги лида-дубля
        # existing_tags = [
        #     {'name': tag['name']}
        #     for tag in (duplicated.get('_embedded') or {}).get('tags') or []
        #     if tag['name'] != DUP_TAG
        # ]
        # existing_tags.append({'name': DUP_TAG})
        # lead.get('responsible_user_id')
        # """
        # {
        #     "id": 54884,
        #     "price": 50000,
        #     "pipeline_id": 47521,
        #     "status_id": 525743,
        #     "_embedded": {
        #         "tags": null
        #     }
        # }
        # """
        # amo_client.update_lead(lead_id=duplicated['id'], data={'_embedded': {'tags': existing_tags}})
    return duplicate


def move_lead_to_continue_to_work(lead, branch, amo_client):
    """ Перемещает лид на этап "Продолжить работу" в соответствующей воронке
    {
        "swissmedica": {
            "pipeline_id": "continue_to_work_status_id",
            "772717": "21521746",
            "5707270": "50171239",
            "2047060": "29830045",
            "2048428": "29839171"
        }
    }
    """
    config = (Config().continue_to_work or {}).get(branch) or {}
    if config:
        pipeline_id = lead.get('pipeline_id')
        status_id = config.get(str(pipeline_id))
        if status_id:
            amo_client.update_lead(
                lead_id=lead.get('id'),
                data={
                    'pipeline_id': int(pipeline_id),
                    'status_id': int(status_id)
                }
            )


def handle_new_interaction(data: Dict) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """

    {'leads[mail_in][0][id]': '34388191', 'leads[mail_in][0][status_id]': '61769054', 'leads[mail_in][0][pipeline_id]': '7438250', 'account[id]': '9884604', 'account[subdomain]': 'swissmedica'}
    {'leads[call_in][0][id]': '34404851', 'leads[call_in][0][status_id]': '61769054', 'leads[call_in][0][pipeline_id]': '7438250', 'account[id]': '9884604', 'account[subdomain]': 'swissmedica'}
    Args:
        data:

    Returns:

    """
    key = 'call_in'
    event = 'Incoming call'
    lead_id = data.get(f'leads[{key}][0][id]')
    if not lead_id:
        key = 'mail_in'
        event = 'Incoming email'
        lead_id = data.get(f'leads[{key}][0][id]')
    if not lead_id:
        return None, None, None
    branch = data.get('account[subdomain]')
    processor = DATA_PROCESSOR.get(branch)()
    pipeline_id = data.get(f'leads[{key}][0][pipeline_id]')
    # pipeline = processor.get_pipeline_and_status_by_id(
    #     pipeline_id=pipeline_id,
    #     status_id=data.get(f'leads[{key}][0][status_id]')
    # )
    # получаем лид и пользователя, ответственного за лид
    amo_client = API_CLIENT.get(branch)()
    lead = amo_client.get_lead_by_id(lead_id=lead_id)
    user = processor.get_user_by_id(user_id=lead.get('responsible_user_id'))
    user = user.name if user else ''
    # тегаем пользователя через @
    telegram_name = None
    managers = GoogleAPIClient(book_id=GoogleSheets.Managers.value, sheet_title='managers').get_sheet()
    for manager in managers:
        if manager.get('manager') == user:
            telegram_name = manager.get('telegram')
            break
    telegram_name = f"@{telegram_name}" if telegram_name else ''
    return (
        'NEW_INCOMING',
        str(pipeline_id),
        f"{event}: https://{branch}.amocrm.ru/leads/detail/{lead_id}\n"
        f"Responsible: {telegram_name if telegram_name else user}".strip()
    )


def handle_new_lead(data: Dict) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    lead_id = data.get('leads[add][0][id]')
    event = 'New lead'
    key = 'add'
    if not lead_id:
        event = 'Lead moved'
        key = 'status'
        lead_id = data.get(f'leads[{key}][0][id]')
    if not lead_id:
        return None, None, None
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
    existing_tags = [
        {'name': tag['name']}
        for tag in (lead.get('_embedded') or {}).get('tags') or []
        if tag['name'] != DUP_TAG
    ]
    # получаем пользователя, ответственного за лид
    user = processor.get_user_by_id(user_id=lead.get('responsible_user_id'))
    tags_str = ', '.join([tag['name'] for tag in existing_tags])
    if tags_str:
        tags_str = f'{tags_str}'
    duplicate = check_for_duplicated_leads(
        processor=processor,
        lead=lead,
        amo_client=amo_client,
        branch=branch,
        existing_tags=existing_tags
    )
    return (
        'NEW_LEAD',
        str(pipeline_id),
        f"{pipeline.get('pipeline') or ''} :: {pipeline.get('status') or ''}\n"
        f"{event}: https://{branch}.amocrm.ru/leads/detail/{lead_id}\n"
        f"Tags: {tags_str}\n"
        f"Responsible: {user.name if user else ''}\n"
        f"{duplicate}".strip()
    )


def handle_get_in_touch(data: Dict) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    leads[status][0][id] :: 23802129
    leads[status][0][status_id] :: 58841526
    leads[status][0][pipeline_id] :: 3508507
    leads[status][0][old_status_id] :: 58840350
    leads[status][0][old_pipeline_id] :: 7010970
    """
    lead_id = data.get('leads[status][0][id]')
    if not lead_id:
        return None, None, None
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
        'GET_IN_TOUCH',
        str(pipeline_id),
        f"{pipeline.get('pipeline') or ''}\n"
        f"Lead: https://{branch}.amocrm.ru/leads/detail/{lead_id} "
        f"Responsible: {user.name if user else ''}\n"
        f"Reaction time: {reaction_time or ''}".strip()
    )
