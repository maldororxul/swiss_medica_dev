""" Синглтон для соединения с БД """
__author__ = 'ke.mizonov'
from sqlalchemy import create_engine
from config import Config

engine = None


def get_engine():
    """ Синглтон для соединения с БД """
    global engine
    config = Config()
    if engine is None:
        engine = create_engine(
            config.sqlalchemy_database_uri,
            pool_size=config.connections_limit,
            max_overflow=config.connections_limit,
            pool_pre_ping=True
        )
    return engine
