""" Чат Tawk """
__author__ = 'ke.mizonov'
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSON
from app.extensions import db


class ChatBase(db.Model):
    __abstract__ = True

    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, nullable=False)
    date = db.Column(db.DateTime, default=datetime.now())
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False, unique=True)
    referer = db.Column(db.String)
    utm = db.Column(JSON)
    messages = db.Column(JSON)

    def __repr__(self):
        return f'<Chat with "{self.name}, {self.phone}">'

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns if c.name != 'to_dict'}


class SMChat(ChatBase):
    __tablename__ = 'Chat'
    __table_args__ = {"schema": "sm"}


class CDVChat(ChatBase):
    __tablename__ = 'Chat'
    __table_args__ = {"schema": "cdv"}
