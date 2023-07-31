""" Глобальные настройки Flask-приложения """
__author__ = 'ke.mizonov'
import json
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """ Конфиг, к которому обращается приложение. Параметры """
    def __call__(self):
        self.SQLALCHEMY_DATABASE_URI = self.sqlalchemy_database_uri
        self.CONNECTIONS_LIMIT = self.connections_limit
        self.CHROMEDRIVER_PATH = self.chromedriver_path
        self.GOOGLE_CREDENTIALS = self.google_credentials
        self.HEROKU_URL = self.heroku_url
        self.SIPUNI = self.sipuni
        self.AUTOCALL_INTERVAL = self.autocall_interval
        self.NEW_LEAD_TELEGRAM = self.new_lead_telegram
        self.META_WHATSAPP_TOKEN = self.meta_whatsapp_token
        self.META_SYSTEM_USER_TOKEN = self.meta_system_user_token

    @property
    def sqlalchemy_database_uri(self):
        uri = os.environ.get('DATABASE_URL')
        if uri and uri.startswith("postgres://"):
            uri = uri.replace("postgres://", "postgresql://", 1)
        return uri

    @property
    def connections_limit(self):
        return int(os.environ.get('CONNECTIONS_LIMIT'))

    # @property
    # def SQLALCHEMY_TRACK_MODIFICATIONS(self):
    #     return os.environ.get('SQLALCHEMY_TRACK_MODIFICATIONS')

    @property
    def chromedriver_path(self):
        return os.environ.get('CHROMEDRIVER_PATH')

    @property
    def google_credentials(self):
        return json.loads(os.environ.get('GOOGLE_CREDENTIALS') or '')

    @property
    def heroku_url(self):
        return os.environ.get('HEROKU_URL')

    @property
    def sipuni(self):
        return json.loads(os.environ.get('SIPUNI') or '')

    @property
    def autocall_interval(self):
        return os.environ.get('AUTOCALL_INTERVAL')

    @property
    def new_lead_telegram(self):
        return json.loads(os.environ.get('NEW_LEAD_TELEGRAM') or '')

    @property
    def meta_whatsapp_token(self):
        return os.environ.get('META_WHATSAPP_TOKEN')

    @property
    def meta_system_user_token(self):
        return os.environ.get('META_SYSTEM_USER_TOKEN')
