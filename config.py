""" Глобальные настройки Flask-приложения """
__author__ = 'ke.mizonov'
import json
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """ Конфиг, к которому обращается приложение. Параметры """
    @property
    def SQLALCHEMY_DATABASE_URI(self):
        uri = os.environ.get('DATABASE_URL')
        if uri and uri.startswith("postgres://"):
            uri = uri.replace("postgres://", "postgresql://", 1)
        return uri

    @property
    def CONNECTIONS_LIMIT(self):
        return int(os.environ.get('CONNECTIONS_LIMIT'))

    @property
    def SQLALCHEMY_TRACK_MODIFICATIONS(self):
        return os.environ.get('SQLALCHEMY_TRACK_MODIFICATIONS')

    @property
    def CHROMEDRIVER_PATH(self):
        return os.environ.get('CHROMEDRIVER_PATH')

    @property
    def GOOGLE_CREDENTIALS(self):
        return json.loads(os.environ.get('GOOGLE_CREDENTIALS') or '')

    @property
    def HEROKU_URL(self):
        return os.environ.get('HEROKU_URL')

    @property
    def SIPUNI(self):
        return json.loads(os.environ.get('SIPUNI') or '')

    @property
    def AUTOCALL_INTERVAL(self):
        return os.environ.get('AUTOCALL_INTERVAL')

    @property
    def NEW_LEAD_TELEGRAM(self):
        return json.loads(os.environ.get('NEW_LEAD_TELEGRAM') or '')

    @property
    def META_WHATSAPP_TOKEN(self):
        return os.environ.get('META_WHATSAPP_TOKEN')

    @property
    def META_SYSTEM_USER_TOKEN(self):
        return os.environ.get('META_SYSTEM_USER_TOKEN')
