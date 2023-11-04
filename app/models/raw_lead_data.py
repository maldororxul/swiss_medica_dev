""" Сырые данные сделки - любой входящий лид пишется сюда """
__author__ = 'ke.mizonov'
from datetime import datetime, date
from sqlalchemy.dialects.postgresql import JSON
from app.extensions import db


def decode(obj):
    for k, v in obj.items():
        if isinstance(v, str):
            try:
                obj[k] = datetime.fromisoformat(v)
            except ValueError:
                try:
                    obj[k] = date.fromisoformat(v)
                except ValueError:
                    pass
    return obj


class RawLeadDataBase(db.Model):
    __abstract__ = True

    id = db.Column(db.Integer, primary_key=True)
    id_on_source = db.Column(db.Integer, unique=True, index=True)
    created_at = db.Column(db.Integer, nullable=False)
    updated_at = db.Column(db.Integer, nullable=False)
    data = db.Column(JSON)

    def __repr__(self):
        return f'<Raw lead "{self.id_on_source}">'

    def to_dict(self):
        line = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        # line['data'] = decode(line['data'])
        return line


class SMRawLeadData(RawLeadDataBase):
    __tablename__ = 'RawLeadData'
    __table_args__ = {"schema": "sm"}


class CDVRawLeadData(RawLeadDataBase):
    __tablename__ = 'RawLeadData'
    __table_args__ = {"schema": "cdv"}
