import click
from flask.cli import with_appcontext

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


@click.command(name='create_tables')
@with_appcontext
def create_tables():
    db.create_all()
