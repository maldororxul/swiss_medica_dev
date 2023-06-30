from sqlalchemy import create_engine
from config import Config


def get_engine():
    return create_engine(
        Config.SQLALCHEMY_DATABASE_URI,
        pool_size=3,
        max_overflow=6,
        pool_pre_ping=True
    )
