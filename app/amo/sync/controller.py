""" Контроллеры синхронизации данных Amo """
__author__ = 'ke.mizonov'
from datetime import datetime
from typing import Dict, List, Callable, Optional
from sqlalchemy import Table, MetaData, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from app.amo.api.client import SwissmedicaAPIClient, DrvorobjevAPIClient, APIClient
from app.engine import get_engine
from app.logger import DBLogger
from app.models.log import SMLog


class SyncController:
    """ Контроллер синхронизации данных Amo """
    schema: str = NotImplemented
    api_client: Callable = NotImplemented

    def __init__(self, date_from: Optional[datetime] = None, date_to: Optional[datetime] = None):
        self.__date_from = date_from
        self.__date_to = date_to
        self.api_client: APIClient = self.api_client()

    def companies(self) -> bool:
        return self.__sync_data(
            collection=self.api_client.get_companies(date_from=self.__date_from, date_to=self.__date_to),
            table_name='Company',
        )

    def contacts(self) -> bool:
        return self.__sync_data(
            collection=self.api_client.get_contacts(date_from=self.__date_from, date_to=self.__date_to),
            table_name='Contact',
        )

    def update_data(
        self,
        collection: List[Dict],
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> bool:
        if date_from:
            self.__date_from = date_from
        if date_to:
            self.__date_to = date_to
        return self.__sync_data(collection=collection, table_name='Data')

    def events(self) -> bool:
        return self.__sync_data(
            collection=self.api_client.get_events(date_from=self.__date_from, date_to=self.__date_to),
            table_name='Event',
        )

    def leads(self) -> bool:
        return self.__sync_data(
            collection=self.api_client.get_leads(date_from=self.__date_from, date_to=self.__date_to),
            table_name='Lead',
        )

    def notes(self) -> bool:
        return self.__sync_data(
            collection=self.api_client.get_notes(date_from=self.__date_from, date_to=self.__date_to),
            table_name='Note',
        )

    def pipelines(self) -> bool:
        return self.__sync_data(
            collection=self.api_client.get_pipelines(),
            table_name='Pipeline',
        )

    def run(self) -> bool:
        """
        Returns:
            True - если на источнике была обнаружена хотя бы одна новая запись за период
        """
        return any([
            self.pipelines(),
            self.users(),
            self.companies(),
            self.contacts(),
            self.events(),
            self.leads(),
            self.notes(),
            self.tasks(),
        ])

    def tasks(self) -> bool:
        return self.__sync_data(
            collection=self.api_client.get_tasks(date_from=self.__date_from, date_to=self.__date_to),
            table_name='Task',
        )

    def users(self) -> bool:
        return self.__sync_data(
            collection=self.api_client.get_users(),
            table_name='User',
        )

    def __sync_data(self, collection: List[Dict], table_name: str) -> bool:
        engine = get_engine()
        target_table = Table(table_name, MetaData(), autoload_with=engine, schema=self.schema)
        has_new_records = False
        with engine.begin() as connection:
            for record in collection:
                try:
                    if record.get('_links'):
                        record.pop('_links')
                    is_new = self.__sync_record(target_table=target_table, record=record, connection=connection)
                    if is_new:
                        has_new_records = True
                except SQLAlchemyError as exc:
                    print(f"Error occurred during database operation: {exc}")
        return has_new_records

    def sync_record(self, record: Dict, table_name: str) -> bool:
        engine = get_engine()
        target_table = Table(table_name, MetaData(), autoload_with=engine, schema=self.schema)
        with engine.begin() as connection:
            return self.__sync_record(target_table=target_table, record=record, connection=connection)

    @staticmethod
    def __sync_record(target_table: Table, record: Dict, connection) -> bool:
        source_id = target_table.c.id_on_source
        stmt = select(target_table).where(source_id == record['id'])
        db_record = connection.execute(stmt).fetchone()
        # Prepare data for database (remove id from dict to prevent its overwriting)
        db_data = {key: value for key, value in record.items() if key != 'id'}
        if db_record and (not record.get('updated_at') or db_record.updated_at < record['updated_at']):
            # Update existing record
            update_stmt = (
                target_table.update().
                where(source_id == record['id']).
                values(**db_data)
            )
            connection.execute(update_stmt)
        elif not db_record:
            # Insert new record
            insert_stmt = insert(target_table).values(
                id_on_source=record['id'],
                **db_data
            )
            connection.execute(insert_stmt)
            return True
        return False


class SMSyncController(SyncController):
    """ Контроллер синхронизации данных Amo: SM """
    schema = 'sm'
    api_client: APIClient = SwissmedicaAPIClient

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.log = DBLogger(log_model=SMLog, branch='sm')


class CDVSyncController(SyncController):
    """ Контроллер синхронизации данных Amo: CDV """
    schema = 'cdv'
    api_client: APIClient = DrvorobjevAPIClient
