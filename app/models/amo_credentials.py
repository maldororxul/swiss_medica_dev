""" Данные для подключения к Amo """
__author__ = 'ke.mizonov'
from app.extensions import db


class AmoCredentialsBase(db.Model):
    __abstract__ = True

    id = db.Column(db.Integer, primary_key=True)
    auth_code = db.Column(db.String(1000), nullable=False)
    client_id = db.Column(db.String(40), nullable=False)
    client_secret = db.Column(db.String(64), nullable=False)
    redirect_url = db.Column(db.String(1000), nullable=False)

    def __repr__(self):
        return f'<AmoCredentials "{self.name}">'


class SMAmoCredentials(AmoCredentialsBase):
    __tablename__ = 'AmoCredentials'
    __table_args__ = {"schema": "sm"}


class CDVAmoCredentials(AmoCredentialsBase):
    __tablename__ = 'AmoCredentials'
    __table_args__ = {"schema": "cdv"}
