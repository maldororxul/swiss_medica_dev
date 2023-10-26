""" Глобальные настройки Flask-приложения """
__author__ = 'ke.mizonov'
import json
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """ Конфиг, к которому обращается приложение. Параметры """
    def __init__(self):
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
        self.WHATSAPP = self.whatsapp
        self.TAWK = self.tawk
        self.TAWK_REST_KEY = self.tawk_rest_key
        self.MANAGERS = self.managers
        self.SIPUNI_COOKIES = self.sipuni_cookies

    @property
    def sqlalchemy_database_uri(self):
        uri = os.environ.get('DATABASE_URL')
        if uri and uri.startswith("postgres://"):
            uri = uri.replace("postgres://", "postgresql://", 1)
        return uri

    @property
    def continue_to_work(self):
        return json.loads(os.environ.get('CONTINUE_TO_WORK') or '')

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
    def chromedriver_binary_location(self):
        return os.environ.get('GOOGLE_CHROME_SHIM')

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
    def arrival(self):
        return json.loads(os.environ.get('ARRIVAL'))

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

    @property
    def whatsapp(self):
        return json.loads(os.environ.get('WHATSAPP') or '')

    @property
    def tawk(self):
        """
        Returns:
            {
                "cdv_main": {
                    "branch": "CDV",
                    "pipeline_id": "5389528",
                    "status_id": "47873530",
                    "phone_field_id": "8671",
                    "email_field_id": "8673"
                }
            }
        """
        return json.loads(os.environ.get('TAWK') or '')

    @property
    def tawk_rest_key(self):
        return os.environ.get('TAWK_REST_KEY')

    @property
    def managers(self):
        return json.loads(os.environ.get('MANAGERS') or '')

    @property
    def sipuni_cookies(self):
        return json.loads(os.environ.get('SIPUNI_COOKIES') or '')
