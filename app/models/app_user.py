""" Пользователь приложения """
__author__ = 'ke.mizonov'
from app.extensions import db


class RoleBase(db.Model):
    __abstract__ = True
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)


class SMRole(RoleBase):
    __tablename__ = 'role'
    __table_args__ = {"schema": "sm"}


class CDVRole(RoleBase):
    __tablename__ = 'role'
    __table_args__ = {"schema": "cdv"}


class AppUserBase(db.Model):
    __abstract__ = True

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    is_active = db.Column(db.Boolean, default=True)
    is_authenticated = db.Column(db.Boolean, default=True)

    def get_id(self):
        return self.id


class SMAppUser(AppUserBase):
    __tablename__ = 'app_user'
    __table_args__ = {"schema": "sm"}
    role_id = db.Column(db.Integer, db.ForeignKey('sm.role.id'))
    role = db.relationship('SMRole', backref=db.backref('app_users', lazy=True))


class CDVAppUser(AppUserBase):
    __tablename__ = 'app_user'
    __table_args__ = {"schema": "cdv"}
    role_id = db.Column(db.Integer, db.ForeignKey('cdv.role.id'))
    role = db.relationship('CDVRole', backref=db.backref('app_users', lazy=True))
