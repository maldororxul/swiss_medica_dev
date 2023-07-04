import os
from dotenv import load_dotenv

load_dotenv()

uri = os.environ.get('DATABASE_URL')
if uri and uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)


class Config:
    # SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = uri
    CONNECTIONS_LIMIT = int(os.environ.get('CONNECTIONS_LIMIT'))
    SQLALCHEMY_TRACK_MODIFICATIONS = os.environ.get('SQLALCHEMY_TRACK_MODIFICATIONS')
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL')
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND')
    GOOGLE_CREDENTIALS = os.environ.get('GOOGLE_CREDENTIALS')
    SUPUNI_ID_CDV = os.environ.get('SUPUNI_ID_CDV')
    SIPUNI_KEY_CDV = os.environ.get('SIPUNI_KEY_CDV')
    SIPUNI_AUTOCALL_ID_CDV = os.environ.get('SIPUNI_AUTOCALL_ID_CDV')
