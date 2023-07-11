""" Синглтон для соединения с БД """
__author__ = 'ke.mizonov'
from sqlalchemy import create_engine
from config import Config

engine = None


def get_engine():
    """ Синглтон для соединения с БД """
    global engine
    if engine is None:
        engine = create_engine(
            Config.SQLALCHEMY_DATABASE_URI,
            pool_size=Config.CONNECTIONS_LIMIT,
            max_overflow=Config.CONNECTIONS_LIMIT,
            pool_pre_ping=True
        )
    return engine
