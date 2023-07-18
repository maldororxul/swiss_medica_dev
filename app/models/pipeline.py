""" Воронка """
__author__ = 'ke.mizonov'
from sqlalchemy.dialects.postgresql import JSON
from app.extensions import db


class PipelineBase(db.Model):
    __abstract__ = True

    id = db.Column(db.Integer, primary_key=True)
    id_on_source = db.Column(db.Integer)
    name = db.Column(db.String(100), nullable=False)
    sort = db.Column(db.Integer, nullable=False)
    is_main = db.Column(db.Boolean, default=False)
    is_unsorted_on = db.Column(db.Boolean, default=False)
    is_archive = db.Column(db.Boolean, default=False)
    account_id = db.Column(db.Integer, nullable=False)
    _embedded = db.Column(JSON)

    def __repr__(self):
        return f'<Pipeline "{self.name}">'

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns if c.name != 'to_dict'}


class SMPipeline(PipelineBase):
    __tablename__ = 'Pipeline'
    __table_args__ = {"schema": "sm"}


class CDVPipeline(PipelineBase):
    __tablename__ = 'Pipeline'
    __table_args__ = {"schema": "cdv"}
