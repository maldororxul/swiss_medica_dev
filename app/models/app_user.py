""" Пользователь приложения """
__author__ = 'ke.mizonov'
from sqlalchemy.orm import declared_attr
from app.extensions import db


class Role(db.Model):
    __tablename__ = 'role'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)


class AppUserBase(db.Model):
    __abstract__ = True

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    is_active = db.Column(db.Boolean, default=True)
    is_authenticated = db.Column(db.Boolean, default=True)

    @declared_attr
    def role_id(cls):
        return db.Column(db.Integer, db.ForeignKey('role.id'))

    @declared_attr
    def role(cls):
        return db.relationship('Role', backref='appusers')


class SMAppUser(AppUserBase):
    __tablename__ = 'app_user'
    __table_args__ = {"schema": "sm"}
    __mapper_args__ = {'polymorphic_identity': 'sm'}


class CDVAppUser(AppUserBase):
    __tablename__ = 'app_user'
    __table_args__ = {"schema": "cdv"}
    __mapper_args__ = {'polymorphic_identity': 'cdv'}
