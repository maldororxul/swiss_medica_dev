""" Кастомные команды для командной строки """
__author__ = 'ke.mizonov'
import click
from flask.cli import with_appcontext
from config import Config
from .extensions import db
from .models.amo_credentials import CDVAmoCredentials, SMAmoCredentials
from .models.amo_token import SMAmoToken, CDVAmoToken
from .models.contact import SMContact, CDVContact
from .models.event import SMEvent, CDVEvent
from .models.lead import CDVLead, SMLead
from .models.note import SMNote, CDVNote
from .models.pipeline import CDVPipeline, SMPipeline
from .models.user import SMUser, CDVUser
from .models.task import SMTask, CDVTask
from .models.company import SMCompany, CDVCompany
from .models.data import SMData, CDVData
from .models.log import SMLog, CDVLog
from .models.autocall import SMAutocallNumber, CDVAutocallNumber
from .models.chat import SMChat, CDVChat
from .models.raw_lead_data import SMRawLeadData, CDVRawLeadData


@click.command(name='create_tables')
@with_appcontext
def create_tables():
    """ Создание всех таблиц БД """
    db.create_all()
