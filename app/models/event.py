""" Событие """
__author__ = 'ke.mizonov'
from sqlalchemy.dialects.postgresql import JSON
from app.extensions import db


class EventBase(db.Model):
    __abstract__ = True

    id = db.Column(db.Integer, primary_key=True)
    id_on_source = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(100), nullable=False)
    entity_id = db.Column(db.Integer, nullable=False)
    entity_type = db.Column(db.String(100), nullable=False)
    created_by = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.Integer, nullable=False)
    value_after = db.Column(JSON)
    value_before = db.Column(JSON)
    account_id = db.Column(db.Integer, nullable=False)
    _embedded = db.Column(JSON)

    def __repr__(self):
        return f'<Event "{self.id}">'

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class SMEvent(EventBase):
    __tablename__ = 'Event'
    __table_args__ = {"schema": "sm"}


class CDVEvent(EventBase):
    __tablename__ = 'Event'
    __table_args__ = {"schema": "cdv"}
