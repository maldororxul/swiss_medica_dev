import click
from flask.cli import with_appcontext
from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.sql.ddl import CreateSchema

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


@click.command(name='create_tables')
@with_appcontext
def create_tables():
    with db.engine.connect() as connection:
        connection.execute(text("CREATE SCHEMA IF NOT EXISTS sm"))
        connection.execute(text("CREATE SCHEMA IF NOT EXISTS cdv"))

    # engine = create_engine(
    #     Config.SQLALCHEMY_DATABASE_URI,
    #     pool_size=20,
    #     max_overflow=100,
    #     pool_pre_ping=True
    # )
    # for schema_name in ('sm', 'cdv'):
    #     if not engine.dialect.has_schema(engine, schema_name):
    #         engine.execute(CreateSchema(schema_name))
    db.create_all()
