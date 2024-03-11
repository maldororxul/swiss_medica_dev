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
    # api_client: Callable = NotImplemented

    def __init__(self, date_from: Optional[datetime] = None, date_to: Optional[datetime] = None):
        self.__date_from = date_from
        self.__date_to = date_to
        # self.api_client: APIClient = self.api_client()

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

    # def update_data(
    #     self,
    #     collection: List[Dict],
    #     date_from: Optional[datetime] = None,
    #     date_to: Optional[datetime] = None
    # ) -> bool:
    #     if date_from:
    #         self.__date_from = date_from
    #     if date_to:
    #         self.__date_to = date_to
    #     return self.__sync_data(collection=collection, table_name='Data')
    #
    # def pipelines(self) -> bool:
    #     return self.__sync_data(
    #         collection=self.api_client.get_pipelines(),
    #         table_name='Pipeline',
    #     )

    # def run(self, date_from: Optional[datetime] = None, date_to: Optional[datetime] = None) -> bool:
    #     """
    #     Returns:
    #         True - если на источнике была обнаружена хотя бы одна новая запись за период
    #     """
    #     if date_from:
    #         self.__date_from = date_from
    #     if date_to:
    #         self.__date_to = date_to
    #     return any([
    #         self.pipelines(),
    #         self.users(),
    #         # self.companies(),
    #         self.contacts(),
    #         self.events(),
    #         self.leads(),
    #         self.notes(),
    #         self.tasks(),
    #     ])

    # def users(self) -> bool:
    #     return self.__sync_data(
    #         collection=self.api_client.get_users(),
    #         table_name='User',
    #     )

    # def sync_data(self, collection: List[Dict], table_name: str) -> bool:
    #     return self.__sync_data(collection=collection, table_name=table_name)
    #
    # def __sync_data(self, collection: List[Dict], table_name: str) -> bool:
    #     # print(f'__sync_data {table_name}')
    #     engine = get_engine()
    #     target_table = Table(table_name, MetaData(), autoload_with=engine, schema=self.schema)
    #     has_new_records = False
    #     with engine.begin() as connection:
    #         for record in collection:
    #             if not record:
    #                 continue
    #             try:
    #                 if record.get('_links'):
    #                     record.pop('_links')
    #                 is_new = self.__sync_record(target_table=target_table, record=record, connection=connection)
    #                 if is_new:
    #                     has_new_records = True
    #             except SQLAlchemyError as exc:
    #                 print(f"Error occurred during database operation: {exc}")
    #     return has_new_records

    # def sync_record(self, record: Dict, table_name: str) -> bool:
    #     engine = get_engine()
    #     target_table = Table(table_name, MetaData(), autoload_with=engine, schema=self.schema)
    #     with engine.begin() as connection:
    #         return self.__sync_record(target_table=target_table, record=record, connection=connection)

    def sync_records(self, records: List[Dict], table_name: str, connection, engine) -> bool:
        target_table = Table(table_name, MetaData(), autoload_with=engine, schema=self.schema)
        exclude_fileds = ('_links', 'email')
        # Подготовка данных для вставки
        insert_records = [{
            key: value for key, value in record.items() if key not in exclude_fileds
        } for record in records]
        for record in insert_records:
            record['id_on_source'] = record.pop('id')  # Предполагаемое изменение, если 'id' используется для других целей
        if insert_records:
            try:
                stmt = pg_insert(target_table).values(insert_records)
                on_conflict_stmt = stmt.on_conflict_do_update(
                    index_elements=['id_on_source'],  # Уникальный идентификатор для обновления
                    set_={name: stmt.excluded[name] for name in insert_records[0].keys() if name not in exclude_fileds}
                )
                result = connection.execute(on_conflict_stmt)
                # Проверяем, были ли затронуты строки
                return result.rowcount > 0
            except Exception as exc:
                print(f'Error during UPSERT operation: {exc}')
                return False
        return False

    # @staticmethod
    # def __sync_record(target_table: Table, record: Dict, connection) -> bool:
    #     source_id = target_table.c.id_on_source
    #     stmt = select(target_table).where(source_id == record['id'])
    #     db_record = connection.execute(stmt).fetchone()
    #     # Prepare data for database (remove id from dict to prevent its overwriting)
    #     db_data = {key: value for key, value in record.items() if key != 'id'}
    #     if db_record and (not record.get('updated_at') or db_record.updated_at < record['updated_at']):
    #         # Update existing record
    #         update_stmt = (
    #             target_table.update().
    #             where(source_id == record['id']).
    #             values(**db_data)
    #         )
    #         connection.execute(update_stmt)
    #         return True
    #     elif not db_record:
    #         # Insert new record
    #         try:
    #             insert_stmt = insert(target_table).values(
    #                 id_on_source=record['id'],
    #                 **db_data
    #             )
    #             connection.execute(insert_stmt)
    #         except Exception as exc:
    #             print(f'insert {target_table.name} error {exc}')
    #         return True
    #     return False


class SMSyncController(SyncController):
    """ Контроллер синхронизации данных Amo: SM """
    schema = 'sm'
    # api_client: APIClient = SwissmedicaAPIClient

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.log = DBLogger(log_model=SMLog, branch='sm')


class CDVSyncController(SyncController):
    """ Контроллер синхронизации данных Amo: CDV """
    schema = 'cdv'
    # api_client: APIClient = DrvorobjevAPIClient

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.log = DBLogger(log_model=CDVLog, branch='cdv')
