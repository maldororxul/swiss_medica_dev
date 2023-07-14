""" Глобальные настройки Flask-приложения """
__author__ = 'ke.mizonov'
import json
import os
from dotenv import load_dotenv

load_dotenv()

uri = os.environ.get('DATABASE_URL')
if uri and uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)


class Config:
    SQLALCHEMY_DATABASE_URI = uri
    CONNECTIONS_LIMIT = int(os.environ.get('CONNECTIONS_LIMIT'))
    SQLALCHEMY_TRACK_MODIFICATIONS = os.environ.get('SQLALCHEMY_TRACK_MODIFICATIONS')
    CHROMEDRIVER_PATH = os.environ.get("CHROMEDRIVER_PATH")
    GOOGLE_CREDENTIALS = json.loads(os.environ.get('GOOGLE_CREDENTIALS') or '')
    HEROKU_URL = os.environ.get("HEROKU_URL")
    SIPUNI = json.loads(os.environ.get("SIPUNI"))
    AUTOCALL_INTERVAL = os.environ.get("AUTOCALL_INTERVAL")
    NEW_LEAD_TELEGRAM = json.loads(os.environ.get("NEW_LEAD_TELEGRAM") or '')
