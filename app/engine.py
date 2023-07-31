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
            config.SQLALCHEMY_DATABASE_URI,
            pool_size=config.CONNECTIONS_LIMIT,
            max_overflow=config.CONNECTIONS_LIMIT,
            pool_pre_ping=True
        )
    return engine
