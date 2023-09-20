""" Логика работы с таблицей Arrival """
__author__ = 'ke.mizonov'
from datetime import datetime
from flask import request, Response, Flask
from app.amo.api.client import SwissmedicaAPIClient, DrvorobjevAPIClient
from app.amo.processor.processor import GoogleSheets
from app.google_api.client import GoogleAPIClient
from app.main.processors import DATA_PROCESSOR
from app.main.routes.telegram import get_data_from_post_request
from config import Config


API_CLIENT = {
    'SM': SwissmedicaAPIClient,
    'CDV': DrvorobjevAPIClient,
    'sm': SwissmedicaAPIClient,
    'cdv': DrvorobjevAPIClient,
    'swissmedica': SwissmedicaAPIClient,
    'drvorobjev': DrvorobjevAPIClient,
}


def waiting_for_arrival(branch: str):
    collection = []
    # инифиализация клиентов для работы с Amo API и с данными
    amo_client = API_CLIENT.get(branch)()
    processor = DATA_PROCESSOR.get(branch)()
    # получаем из конфига все воронки и статусы, в которых следует искать лиды
    pipelines = (Config().arrival.get(branch) or {}).get('pipelines') or []
    for pipeline_config in pipelines:
        pipeline_id, status_id = pipeline_config['pipeline_id'], pipeline_config['status_id']
        pipeline = processor.get_pipeline_and_status_by_id(
            pipeline_id=int(pipeline_id) if str(pipeline_id).isnumeric() else None,
            status_id=int(status_id) if str(status_id).isnumeric() else None
        ) or {}
        # получаем лиды из Amo
        leads = amo_client.get_leads_by_pipeline_and_status(pipeline_id=pipeline_id, status_id=status_id)
        for lead in leads:
            _embedded = lead.get('_embedded') or {}
            # получаем контакт из Amo
            contacts = _embedded.get('contacts')
            contact = amo_client.get_contact_by_id(contact_id=contacts[0]['id']) if contacts else {}
            email_and_phone = '; '.join([
                cf['values'][0]['value']
                for cf in contact.get('custom_fields_values') or []
                if cf.get('field_code') in ('PHONE', 'EMAIL')
            ])
            # получаем пользователя, ответственного за лид
            user = processor.get_user_by_id(user_id=lead.get('responsible_user_id')) or (None, None, '')
            link_to_amo = (((lead.get('_links') or {}).get('self') or {}).get('href') or '').split('?')[0]
            cf_dict = processor.get_cf_dict(lead=lead)
            arrival_dt = datetime.fromtimestamp(cf_dict.get('Дата начала лечения')).date()
            departure_dt = datetime.fromtimestamp(cf_dict.get('Дата завершения лечения')).date()
            disease = cf_dict.get('Disease')
            if disease == 'Other':
                disease = cf_dict.get('Disease if other')
            collection.append({
                # "created_at": ...,
                # "updated_at": ...,
                # разделил имя пациента и ссылку, а также заболевание и ссылку
                "Client's Name": contact.get('name'),
                'Disease': disease,
                "Clinic": cf_dict.get('Клиника'),
                'Amo Link': link_to_amo,
                'Amo Stage': pipeline.get('status'),
                'Google Drive Link': cf_dict.get('Папка Пациента'),
                # "Client's Name + Link to amoCRM": ...,
                # "Disease + Link to Client Google Drive Folder": ...,
                "Arrival Date": str(arrival_dt),
                "Departure Date": str(departure_dt),
                "Duration": cf_dict.get('Days in Clinic (Stay duration)'),
                "Spoken Language": cf_dict.get('Spoken language'),
                "Gender": cf_dict.get('Gender') or '',
                "Manager": user[2],

                "Country": cf_dict.get('Country_from_Jivo') or '',

                "New or Repeated": 'Repeated' if pipeline.get('pipeline') in ('Re-sales to Client SM', '') else 'New',
                "Consulting Doctor": cf_dict.get('Консультирующий доктор') or '',
                "Arrival flight details": cf_dict.get('Arrival flight details') or '',
                "Departure flight details": cf_dict.get('Departure flight details') or '',
                "Problem patient or companion": cf_dict.get('Problem patient or companion') or '',
                "Wheelchair": cf_dict.get('Wheelchair') or '',
                "Number of Companions": cf_dict.get('Number of Companions') or '',
                "Food Intolerance": cf_dict.get('Food Intolerance') or '',
                "Contacts: Email, Phone number": email_and_phone,
                "Comments (Manager)": cf_dict.get('Comments') or '',
            })
    if collection:
        GoogleAPIClient(
            book_id=GoogleSheets.ArrivalSM.value,
            sheet_title='Arrival'
        ).update_collection(collection=collection, unique_key='Amo Link', archive_sheet='Archive', has_dates=True)
    return Response(status=204)
