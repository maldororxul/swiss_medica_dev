""" Данные для подключения к Amo """
__author__ = 'ke.mizonov'
from app.extensions import db


class AmoTokenBase(db.Model):
    __abstract__ = True

    id = db.Column(db.Integer, primary_key=True)
    token_type = db.Column(db.String(10), nullable=False)
    expires_in = db.Column(db.String(6), nullable=False)
    access_token = db.Column(db.String(1000), nullable=False)
    refresh_token = db.Column(db.String(1000), nullable=False)

    def __repr__(self):
        return f'<AmoCredentials "{self.access_token}">'


class SMAmoToken(AmoTokenBase):
    __tablename__ = 'AmoToken'
    __table_args__ = {"schema": "sm"}


class CDVAmoToken(AmoTokenBase):
    __tablename__ = 'AmoToken'
    __table_args__ = {"schema": "cdv"}
