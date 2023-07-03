import os

from sqlalchemy import create_engine
from config import Config

CONNECTIONS_LIMIT = os.environ.get('CONNETIONS_LIMIT')

engine = None


def get_engine():
    global engine
    if engine is None:
        engine = create_engine(
            Config.SQLALCHEMY_DATABASE_URI,
            pool_size=CONNECTIONS_LIMIT,
            max_overflow=CONNECTIONS_LIMIT,
            pool_pre_ping=True
        )
    return engine
