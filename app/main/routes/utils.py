from typing import Optional, Dict
from flask import request
from urllib.parse import urlparse, parse_qs

from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError


def add_if_not_exists(session: Session, model, filter_by: Dict):
    instance = session.query(model).filter_by(**filter_by).first()
    if instance:
        return instance, False
    else:
        instance = model(**filter_by)
        try:
            session.add(instance)
            session.commit()
            return instance, True
        except IntegrityError:
            session.rollback()
            instance = session.query(model).filter_by(**filter_by).first()
            return instance, False


def create_view_excluding_columns(session, model, excluded_columns):
    # Составляем список названий столбцов для включения в представление, исключая заданные
    included_columns = [column.name for column in model.__table__.columns if column.name not in excluded_columns]
    # Формируем строку с названиями столбцов для SQL запроса
    columns_str = ', '.join(included_columns)
    # Получаем имя схемы и таблицы из модели
    schema_name = model.__table_args__['schema']
    table_name = model.__tablename__
    # Формируем имя представления, используя имя схемы и таблицы
    view_name = f"{schema_name}_view_{table_name}"
    # SQL запрос для создания представления с использованием конструкции "CREATE OR REPLACE VIEW"
    sql = f"""
    CREATE OR REPLACE VIEW {schema_name}.{view_name} AS
    SELECT {columns_str}
    FROM {schema_name}.{table_name};
    """
    # Выполнение SQL запроса через сессию
    session.execute(text(sql))
    session.commit()


def get_data_from_post_request(_request) -> Optional[Dict]:
    if request.content_type == 'application/json':
        return _request.json
    elif request.content_type == 'application/x-www-form-urlencoded':
        return _request.form.to_dict()
    else:
        return None


def get_args_from_url(url: str) -> Dict:
    """ Получает словарь аргументов из URL, подходит для разбора utm

    Args:
        url: адрес

    Returns:
        {'utm_source': ..., 'utm_medium': ..., ...}
    """
    parse_result = urlparse(url)
    return {key: value[0] for key, value in parse_qs(parse_result.query).items()}
