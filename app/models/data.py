""" Данные сводной таблицы """
__author__ = 'ke.mizonov'
from datetime import datetime
import json
import re
from sqlalchemy.dialects.postgresql import JSON
from app.extensions import db


def datetime_parser(dct):
    date_format = re.compile(r'\b\d{4}-\d{2}-\d{2}\b')
    for k, v in dct.items():
        if isinstance(v, str) and date_format.match(v):
            try:
                dct[k] = datetime.strptime(v, '%Y-%m-%d').date()
            except ValueError:
                pass
    return dct


class DataBase(db.Model):
    __abstract__ = True

    id = db.Column(db.Integer, primary_key=True)
    id_on_source = db.Column(db.Integer)
    created_at = db.Column(db.Integer, nullable=False)
    updated_at = db.Column(db.Integer, nullable=False)
    data = db.Column(JSON)

    def __repr__(self):
        return f'<Line "{self.id_on_source}">'

    def to_dict(self):
        line = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        # line['data'] = json.loads(line['data'], object_hook=datetime_parser)
        return line


class SMData(DataBase):
    __tablename__ = 'Data'
    __table_args__ = {"schema": "sm"}


class CDVData(DataBase):
    __tablename__ = 'Data'
    __table_args__ = {"schema": "cdv"}
