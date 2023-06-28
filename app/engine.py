from sqlalchemy import create_engine
from config import Config


def get_engine():
    return create_engine(
        Config.SQLALCHEMY_DATABASE_URI,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True
    )
