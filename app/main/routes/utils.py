from typing import Optional, Dict
from flask import request
from urllib.parse import urlparse, parse_qs
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
