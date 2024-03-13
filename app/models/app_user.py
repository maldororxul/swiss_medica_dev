""" Пользователь приложения """
__author__ = 'ke.mizonov'
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


class SMAppUser(AppUserBase):
    __tablename__ = 'app_user_sm'
    __table_args__ = {"schema": "sm"}
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'))
    role = db.relationship('Role', backref=db.backref('sm_users', lazy=True))


class CDVAppUser(AppUserBase):
    __tablename__ = 'app_user_cdv'
    __table_args__ = {"schema": "cdv"}
    __mapper_args__ = {'polymorphic_identity': 'cdv'}
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'))
    role = db.relationship('Role', backref=db.backref('cdv_users', lazy=True))
