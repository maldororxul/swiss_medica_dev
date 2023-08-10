""" Данные сводной таблицы """
__author__ = 'ke.mizonov'
from sqlalchemy.dialects.postgresql import JSON
from app.extensions import db
from app.main.utils import DateTimeEncoder


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
        line['data'] = DateTimeEncoder.decode(line['data'])
        return line


class SMData(DataBase):
    __tablename__ = 'Data'
    __table_args__ = {"schema": "sm"}


class CDVData(DataBase):
    __tablename__ = 'Data'
    __table_args__ = {"schema": "cdv"}
