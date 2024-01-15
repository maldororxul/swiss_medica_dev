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
        self.AMO_CHAT = self.amo_chat

    @property
    def sqlalchemy_database_uri(self):
        uri = os.environ.get('DATABASE_URL')
        if uri and uri.startswith("postgres://"):
            uri = uri.replace("postgres://", "postgresql://", 1)
        return uri

    @property
    def amo_chat(self):
        return json.loads(os.environ.get('AMO_CHAT') or '')

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
        return {
            "drvorobjev": {
                "id": "030238",
                "key": "0.pxdvia21d9e",
                "login": "Kirill.Mizonov@swissmedica21.com",
                "password": "0c8PEs9YpiJ7afeKf73C",
                "autocall": {
                    "21774": {
                        "name": "New Auto Reach :: Serbia - Serbian",
                        "success_name": "New_patients_general_SE :: 04. Responded for Auto Reach",
                        "pipeline_id": "7010970",
                        "status_id": "58840350",
                        "success_pipeline_id": "3508507",
                        "success_status_id": "58841526",
                        "schedule": {
                            "Monday": ["07:00 - 14:00"],
                            "Tuesday": ["07:00 - 14:00"],
                            "Wednesday": ["07:00 - 14:00"],
                            "Thursday": ["07:00 - 14:00"],
                            "Friday": ["07:00 - 14:00"],
                            "Saturday": ["10:00 - 14:00"],
                            "Sunday": ["10:00 - 14:00"]
                        },
                        "calls_limit": "5"
                    },
                    "07": {
                        "name": "New Auto Reach :: France - French",
                        "success_name": "New_patients_general_SE :: 04. Responded for Auto Reach",
                        "pipeline_id": "7010970",
                        "status_id": "58840354",
                        "success_pipeline_id": "3508507",
                        "success_status_id": "58841526"
                    },
                    "08": {
                        "name": "New Auto Reach :: Germany - German",
                        "success_name": "New_patients_general_SE :: 04. Responded for Auto Reach",
                        "pipeline_id": "7010970",
                        "status_id": "58840358",
                        "success_pipeline_id": "3508507",
                        "success_status_id": "58841526"
                    },
                    "09": {
                        "name": "New Auto Reach :: Austria - Austrian",
                        "success_name": "New_patients_general_SE :: 04. Responded for Auto Reach",
                        "pipeline_id": "7010970",
                        "status_id": "58840470",
                        "success_pipeline_id": "3508507",
                        "success_status_id": "58841526"
                    },
                    "010": {
                        "name": "New Auto Reach :: Italy - Italian",
                        "success_name": "New_patients_general_SE :: 04. Responded for Auto Reach",
                        "pipeline_id": "7010970",
                        "status_id": "58840474",
                        "success_pipeline_id": "3508507",
                        "success_status_id": "58841526"
                    },
                    "011": {
                        "name": "New Auto Reach :: Romania - Romanian",
                        "success_name": "New_patients_general_SE :: 04. Responded for Auto Reach",
                        "pipeline_id": "7010970",
                        "status_id": "58840478",
                        "success_pipeline_id": "3508507",
                        "success_status_id": "58841526"
                    },
                    "0": {
                        "name": "New Auto Reach :: Bulgaria - Bulgarian",
                        "success_name": "New_patients_general_SE :: 04. Responded for Auto Reach",
                        "pipeline_id": "7010970",
                        "status_id": "58840482",
                        "success_pipeline_id": "3508507",
                        "success_status_id": "58841526"
                    },
                    "23868": {
                        "name": "New Auto Reach :: Other Europe - English",
                        "success_name": "New_patients_general_SE :: 04. Responded for Auto Reach",
                        "pipeline_id": "7010970",
                        "status_id": "58840486",
                        "success_pipeline_id": "3508507",
                        "success_status_id": "58841526",
                        "schedule": {
                            "Monday": ["07:00 - 14:00"],
                            "Tuesday": ["07:00 - 14:00"],
                            "Wednesday": ["07:00 - 14:00"],
                            "Thursday": ["07:00 - 14:00"],
                            "Friday": ["07:00 - 14:00"],
                            "Saturday": ["10:00 - 14:00"],
                            "Sunday": ["10:00 - 14:00"]
                        },
                        "calls_limit": "5"
                    },
                    "000": {
                        "name": "New Auto Reach :: America - English",
                        "success_name": "New_patients_general_SE :: 04. Responded for Auto Reach",
                        "pipeline_id": "7010970",
                        "status_id": "58840490",
                        "success_pipeline_id": "3508507",
                        "success_status_id": "58841526"
                    },
                    "00": {
                        "name": "New Auto Reach :: Pacific - English",
                        "success_name": "New_patients_general_SE :: 04. Responded for Auto Reach",
                        "pipeline_id": "7010970",
                        "status_id": "58840494",
                        "success_pipeline_id": "3508507",
                        "success_status_id": "58841526"
                    },
                    "23889": {
                        "name": "Disappear Auto Reach :: Serbia - Serbian",
                        "success_name": "New_patients_general_SE :: 04. Responded for Auto Reach",
                        "pipeline_id": "7010974",
                        "status_id": "58840366",
                        "success_pipeline_id": "3508507",
                        "success_status_id": "58841526",
                        "schedule": {
                            "Monday": ["07:00 - 14:00"],
                            "Tuesday": ["07:00 - 14:00"],
                            "Wednesday": ["07:00 - 14:00"],
                            "Thursday": ["07:00 - 14:00"],
                            "Friday": ["07:00 - 14:00"],
                            "Saturday": ["10:00 - 14:00"],
                            "Sunday": ["10:00 - 14:00"]
                        },
                        "calls_limit": "5"
                    },
                    "0000": {
                        "name": "Disappear Auto Reach :: France - French",
                        "success_name": "New_patients_general_SE :: 04. Responded for Auto Reach",
                        "pipeline_id": "7010974",
                        "status_id": "58840370",
                        "success_pipeline_id": "3508507",
                        "success_status_id": "58841526"
                    },
                    "00000": {
                        "name": "Disappear Auto Reach :: Germany - German",
                        "success_name": "New_patients_general_SE :: 04. Responded for Auto Reach",
                        "pipeline_id": "7010974",
                        "status_id": "58840374",
                        "success_pipeline_id": "3508507",
                        "success_status_id": "58841526"
                    },
                    "000000": {
                        "name": "Disappear Auto Reach :: Austria - Austrian",
                        "success_name": "New_patients_general_SE :: 04. Responded for Auto Reach",
                        "pipeline_id": "7010974",
                        "status_id": "58840542",
                        "success_pipeline_id": "3508507",
                        "success_status_id": "58841526"
                    },
                    "0000000": {
                        "name": "Disappear Auto Reach :: Italy - Italian",
                        "success_name": "New_patients_general_SE :: 04. Responded for Auto Reach",
                        "pipeline_id": "7010974",
                        "status_id": "58840546",
                        "success_pipeline_id": "3508507",
                        "success_status_id": "58841526"
                    },
                    "01": {
                        "name": "Disappear Auto Reach :: Romania - Romanian",
                        "success_name": "New_patients_general_SE :: 04. Responded for Auto Reach",
                        "pipeline_id": "7010974",
                        "status_id": "58840550",
                        "success_pipeline_id": "3508507",
                        "success_status_id": "58841526"
                    },
                    "02": {
                        "name": "Disappear Auto Reach :: Bulgaria - Bulgarian",
                        "success_name": "New_patients_general_SE :: 04. Responded for Auto Reach",
                        "pipeline_id": "7010974",
                        "status_id": "58840554",
                        "success_pipeline_id": "3508507",
                        "success_status_id": "58841526"
                    },
                    "23892": {
                        "name": "Disappear Auto Reach :: Other Europe - English",
                        "success_name": "New_patients_general_SE :: 04. Responded for Auto Reach",
                        "pipeline_id": "7010974",
                        "status_id": "58840558",
                        "success_pipeline_id": "3508507",
                        "success_status_id": "58841526",
                        "schedule": {
                            "Monday": ["07:00 - 14:00"],
                            "Tuesday": ["07:00 - 14:00"],
                            "Wednesday": ["07:00 - 14:00"],
                            "Thursday": ["07:00 - 14:00"],
                            "Friday": ["07:00 - 14:00"],
                            "Saturday": ["10:00 - 14:00"],
                            "Sunday": ["10:00 - 14:00"]
                        },
                        "calls_limit": "5"
                    },
                    "03": {
                        "name": "Disappear Auto Reach :: America - English",
                        "success_name": "New_patients_general_SE :: 04. Responded for Auto Reach",
                        "pipeline_id": "7010974",
                        "status_id": "58840562",
                        "success_pipeline_id": "3508507",
                        "success_status_id": "58841526"
                    },
                    "04": {
                        "name": "Disappear Auto Reach :: Pacific - English",
                        "success_name": "New_patients_general_SE :: 04. Responded for Auto Reach",
                        "pipeline_id": "7010974",
                        "status_id": "58840566",
                        "success_pipeline_id": "3508507",
                        "success_status_id": "58841526"
                    }
                }
            },
            "swissmedica": {
                "id": "082853",
                "key": "0.z4sn343lpw",
                "login": "uladzimir.zenkovich@swissmedica21.com",
                "password": "QTagn2",
                "autocall": {
                    "22788": {
                        "name": "New Auto Reach :: English - Europe",
                        "success_name": "НОВЫЕ КЛИЕНТЫ :: Ответил на автообзвон",
                        "pipeline_id": "7080722",
                        "status_id": "59313242",
                        "success_pipeline_id": "772717",
                        "success_status_id": "59313086",
                        "schedule": {
                            "Monday": ["09:00 - 14:00"],
                            "Tuesday": ["09:00 - 14:00"],
                            "Wednesday": ["09:00 - 14:00"],
                            "Thursday": ["09:00 - 14:00"],
                            "Friday": ["09:00 - 14:00"],
                            "Saturday": ["12:00 - 14:00"],
                            "Sunday": ["12:00 - 14:00"]
                        },
                        "calls_limit": "5"
                    },
                    "25963": {
                        "name": "New Auto Reach :: English - USA",
                        "success_name": "НОВЫЕ КЛИЕНТЫ :: Ответил на автообзвон",
                        "pipeline_id": "7080722",
                        "status_id": "61456502",
                        "success_pipeline_id": "772717",
                        "success_status_id": "59313086",
                        "schedule": {
                            "Monday": ["15:00 - 18:00"],
                            "Tuesday": ["15:00 - 18:00"],
                            "Wednesday": ["15:00 - 18:00"],
                            "Thursday": ["15:00 - 18:00"],
                            "Friday": ["15:00 - 18:00"],
                            "Saturday": ["15:00 - 18:00"],
                            "Sunday": ["15:00 - 18:00"]
                        },
                        "calls_limit": "5"
                    },
                    "24564": {
                        "name": "New Auto Reach :: Italian - Europe",
                        "success_name": "ITALY :: Ответил на автообзвон",
                        "pipeline_id": "7080722",
                        "status_id": "59590130",
                        "success_pipeline_id": "5707270",
                        "success_status_id": "60882906",
                        "schedule": {
                            "Monday": ["09:00 - 14:00"],
                            "Tuesday": ["09:00 - 14:00"],
                            "Wednesday": ["09:00 - 14:00"],
                            "Thursday": ["09:00 - 14:00"],
                            "Friday": ["09:00 - 14:00"],
                            "Saturday": ["12:00 - 14:00"],
                            "Sunday": ["12:00 - 14:00"]
                        },
                        "calls_limit": "5"
                    },
                    "24978": {
                        "name": "New Auto Reach :: German - Europe",
                        "success_name": "GERMAN :: Ответил на автообзвон",
                        "pipeline_id": "7080722",
                        "status_id": "60802086",
                        "success_pipeline_id": "2048428",
                        "success_status_id": "60882910",
                        "schedule": {
                            "Monday": ["09:00 - 14:00"],
                            "Tuesday": ["09:00 - 14:00"],
                            "Wednesday": ["09:00 - 14:00"],
                            "Thursday": ["09:00 - 14:00"],
                            "Friday": ["09:00 - 14:00"],
                            "Saturday": ["12:00 - 14:00"],
                            "Sunday": ["12:00 - 14:00"]
                        },
                        "calls_limit": "5"
                    },
                    "24981": {
                        "name": "Disappeared Auto Reach :: English - Europe",
                        "success_name": "НОВЫЕ КЛИЕНТЫ :: Ответил на автообзвон",
                        "pipeline_id": "7299106",
                        "status_id": "60802710",
                        "success_pipeline_id": "772717",
                        "success_status_id": "59313086",
                        "schedule": {
                            "Monday": ["09:00 - 14:00"],
                            "Tuesday": ["09:00 - 14:00"],
                            "Wednesday": ["09:00 - 14:00"],
                            "Thursday": ["09:00 - 14:00"],
                            "Friday": ["09:00 - 14:00"],
                            "Saturday": ["12:00 - 14:00"],
                            "Sunday": ["12:00 - 14:00"]
                        },
                        "calls_limit": "5"
                    },
                    "25960": {
                        "name": "Disappeared Auto Reach :: English - USA",
                        "success_name": "НОВЫЕ КЛИЕНТЫ :: Ответил на автообзвон",
                        "pipeline_id": "7299106",
                        "status_id": "61456618",
                        "success_pipeline_id": "772717",
                        "success_status_id": "59313086",
                        "schedule": {
                            "Monday": ["15:00 - 18:00"],
                            "Tuesday": ["15:00 - 18:00"],
                            "Wednesday": ["15:00 - 18:00"],
                            "Thursday": ["15:00 - 18:00"],
                            "Friday": ["15:00 - 18:00"],
                            "Saturday": ["15:00 - 18:00"],
                            "Sunday": ["15:00 - 18:00"]
                        },
                        "calls_limit": "5"
                    },
                    "24984": {
                        "name": "Disappeared Auto Reach :: Italian - Europe",
                        "success_name": "ITALY :: Ответил на автообзвон",
                        "pipeline_id": "7299106",
                        "status_id": "60802714",
                        "success_pipeline_id": "5707270",
                        "success_status_id": "60882906",
                        "schedule": {
                            "Monday": ["09:00 - 14:00"],
                            "Tuesday": ["09:00 - 14:00"],
                            "Wednesday": ["09:00 - 14:00"],
                            "Thursday": ["09:00 - 14:00"],
                            "Friday": ["09:00 - 14:00"],
                            "Saturday": ["12:00 - 14:00"],
                            "Sunday": ["12:00 - 14:00"]
                        },
                        "calls_limit": "5"
                    },
                    "24987": {
                        "name": "Disappeared Auto Reach :: German - Europe",
                        "success_name": "GERMAN :: Ответил на автообзвон",
                        "pipeline_id": "7299106",
                        "status_id": "60802718",
                        "success_pipeline_id": "2048428",
                        "success_status_id": "60882910",
                        "schedule": {
                            "Monday": ["09:00 - 14:00"],
                            "Tuesday": ["09:00 - 14:00"],
                            "Wednesday": ["09:00 - 14:00"],
                            "Thursday": ["09:00 - 14:00"],
                            "Friday": ["09:00 - 14:00"],
                            "Saturday": ["12:00 - 14:00"],
                            "Sunday": ["12:00 - 14:00"]
                        },
                        "calls_limit": "5"
                    }
                }
            }
        }
        # return json.loads(os.environ.get('SIPUNI') or '')

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
                    "sites": ["https://swiss-medica-2e0e7bc937df.herokuapp.com"],
                    "branch": "CDV",
                    "pipeline_id": "5389528",
                    "status_id": "47873530",
                    "phone_field_id": "8671",
                    "email_field_id": "8673"
                },
                "sm_main": {
                    "sites": ["https://swiss-medica-2e0e7bc937df.herokuapp.com"],
                    "branch": "SM",
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
        return json.loads(os.environ.get('TAWK_REST_KEY') or '')

    @property
    def managers(self):
        return json.loads(os.environ.get('MANAGERS') or '')

    @property
    def sipuni_cookies(self):
        return json.loads(os.environ.get('SIPUNI_COOKIES') or '')

    @property
    def startstemcells_forms(self):
        return {
            '1878': {"n": "Subscription form - footer: IT", "r": "IT", "l": 0},
            '1880': {"n": "Subscription form - footer: DE", "r": "DE", "l": 0},
            '1879': {"n": "Subscription form - footer: FR", "r": "FR", "l": 0},
            '318': {"n": "Subscription form - footer", "r": "EN", "l": 0},
            '3420': {"n": "Subscription form - footer: CZ", "r": "CZ", "l": 0},
            '317': {"n": "Subscription form - modal", "r": "EN", "l": 0},
            '43': {"n": "Get consultation", "r": "EN", "l": 1},
            '60': {"n": "Gutenberg - Send request", "r": "EN", "l": 1},
            '44': {"n": "Call Me Back - modal", "r": "EN", "l": 1},
            '247': {"n": "Contact form", "r": "EN", "l": 1},
            '59': {"n": "Gutenberg - Get consultation", "r": "EN", "l": 1},
            '3418': {"n": "Gutenberg - Get consultation CZ", "r": "CZ", "l": 1},
            '3419': {"n": "Gutenberg - Send request CZ", "r": "CZ", "l": 1},
            '3415': {"n": "Get consultation CZ", "r": "CZ", "l": 1},
            '3416': {"n": "Call Me Back - modal - CZ", "r": "CZ", "l": 1},
            '3417': {"n": "Contact form - CZ", "r": "CZ", "l": 1},
            '1877': {"n": "Gutenberg - Send request DE", "r": "DE", "l": 1},
            '1874': {"n": "Gutenberg - Get consultation DE", "r": "DE", "l": 1},
            '1856': {"n": "Get consultation DE", "r": "DE", "l": 1},
            '1851': {"n": "Call Me Back - modal - DE", "r": "DE", "l": 1},
            '1848': {"n": "Contact form - DE", "r": "DE", "l": 1},
            '1872': {"n": "Gutenberg - Get consultation IT", "r": "IT", "l": 1},
            '1844': {"n": "Contact form - IT", "r": "IT", "l": 1},
            '1875': {"n": "Gutenberg - Send request IT", "r": "IT", "l": 1},
            '1849': {"n": "Call Me Back - modal - IT", "r": "IT", "l": 1},
            '1854': {"n": "Get consultation IT", "r": "IT", "l": 1},
            '1850': {"n": "Call Me Back - modal - FR", "r": "FR", "l": 1},
            '1855': {"n": "Get consultation FR", "r": "FR", "l": 1},
            '1876': {"n": "Gutenberg - Send request FR", "r": "FR", "l": 1},
            '1873': {"n": "Gutenberg - Get consultation FR", "r": "FR", "l": 1},
            '1847': {"n": "Contact form - FR", "r": "FR", "l": 1}
        }
        # return json.loads(os.environ.get('STARTSTEMCELLS_FORMS') or '')
