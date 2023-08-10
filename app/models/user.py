""" Пользователь """
__author__ = 'ke.mizonov'
from sqlalchemy.dialects.postgresql import JSON
from app.extensions import db


class UserBase(db.Model):
    __abstract__ = True

    id = db.Column(db.Integer, primary_key=True)
    id_on_source = db.Column(db.Integer, unique=True, index=True)
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True)
    lang = db.Column(db.String(2))
    rights = db.Column(JSON)
    _embedded = db.Column(JSON)

    def __repr__(self):
        return f'<User "{self.name}">'

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns if c.name != 'to_dict'}


class SMUser(UserBase):
    __tablename__ = 'User'
    __table_args__ = {"schema": "sm"}


class CDVUser(UserBase):
    __tablename__ = 'User'
    __table_args__ = {"schema": "cdv"}
