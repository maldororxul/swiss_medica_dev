""" Контроллеры синхронизации данных Amo """
__author__ = 'ke.mizonov'
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from sqlalchemy import Table, MetaData, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.dialects.postgresql import insert as pg_insert
from app.engine import get_engine
from app.logger import DBLogger
from app.models.log import SMLog, CDVLog


class SyncController:
    """ Контроллер синхронизации данных Amo """
    schema: str = NotImplemented

    def __init__(self, date_from: Optional[datetime] = None, date_to: Optional[datetime] = None):
        self.__date_from = date_from
        self.__date_to = date_to

    # def companies(self) -> bool:
    #     return self.__sync_data(
    #         collection=self.api_client.get_companies(date_from=self.__date_from, date_to=self.__date_to),
    #         table_name='Company',
    #     )

    def chat(self, lead_id: int, data: Dict) -> bool:
        phone = data.get('phone')
        """
        'type': 'visitor',
        'visitor': visitor,
        'message': message,
        'utm': utmParams,
        'referer': referer,
        'create_lead': create_lead,
        'chat_name': CHANNEL_NAME
        """
        message = {
            'date': datetime.now(),
            'type': data.get('type'),
            'text': data.get('message'),
        }
        if data.get('create_lead'):
            message['text'] = 'Init Tawk chat'
        engine = get_engine()
        target_table = Table('Chat', MetaData(), autoload_with=engine, schema=self.schema)
        messages = []
        with engine.begin() as connection:
            phone_field = target_table.c.phone
            stmt = select(target_table).where(phone_field == phone)
            db_record = connection.execute(stmt).fetchone()
            if db_record:
                # Update existing record
                messages = db_record.messages
                messages.append(message)
                update_stmt = (
                    target_table.update().
                    where(phone_field == phone).
                    values(messages=messages)
                )
                connection.execute(update_stmt)
            elif not db_record and lead_id:
                messages = [message]
                # Insert new record
                try:
                    insert_stmt = insert(target_table).values(
                        phone=phone,
                        messages=messages,
                        lead_id=lead_id,
                        name=data['visitor']['name'],
                        referer=data['referer'],
                        utm=data['utm']
                    )
                    connection.execute(insert_stmt)
                except Exception as exc:
                    print(f'insert {target_table.name} error {exc}')
        return messages

    def sync_records(self, records: List[Dict], table_name: str, connection, engine) -> bool:
        target_table = Table(table_name, MetaData(), autoload_with=engine, schema=self.schema)
        exclude_fields = ('_links', 'email', 'roles')
        from sqlalchemy import select

        # Подготовка данных для вставки
        insert_records = [{
            key: value for key, value in record.items() if key not in exclude_fields
        } for record in records]
        for record in insert_records:
            record['id_on_source'] = record.pop('id')
        if not insert_records:
            return False
        # Предварительная проверка существующих данных
        existing_records_query = select(target_table).where(
            target_table.c.id_on_source.in_([record['id_on_source'] for record in insert_records])
        )
        existing_records = connection.execute(existing_records_query).fetchall()
        # Преобразование результатов запроса в словарь, используя _mapping для доступа к данным как к словарю
        existing_records_dict = {
            record._mapping['id_on_source']: dict(record._mapping)
            for record in existing_records
        }
        need_update = False
        for record in insert_records:
            if record['id_on_source'] not in existing_records_dict:
                need_update = True
                break
            existing_record = existing_records_dict[record['id_on_source']]
            if any(record[key] != existing_record.get(key) for key in record.keys() if key not in exclude_fields):
                need_update = True
                break
        if not need_update:
            return False
        try:
            stmt = pg_insert(target_table).values(insert_records)
            on_conflict_stmt = stmt.on_conflict_do_update(
                index_elements=['id_on_source'],  # Уникальный идентификатор для обновления
                set_={name: stmt.excluded[name] for name in insert_records[0].keys() if name not in exclude_fields}
            )
            result = connection.execute(on_conflict_stmt)
            return result.rowcount > 0
        except Exception as exc:
            print(f'Error during UPSERT operation: {exc}')
            return False


class SMSyncController(SyncController):
    """ Контроллер синхронизации данных Amo: SM """
    schema = 'sm'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.log = DBLogger(log_model=SMLog, branch='sm')


class CDVSyncController(SyncController):
    """ Контроллер синхронизации данных Amo: CDV """
    schema = 'cdv'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.log = DBLogger(log_model=CDVLog, branch='cdv')
