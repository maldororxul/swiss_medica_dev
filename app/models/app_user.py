""" Пользователь приложения """
__author__ = 'ke.mizonov'
from app.extensions import db


class Role(db.Model):
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
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), nullable=False)
    role = db.relationship('Role', backref=db.backref('users', lazy=True))

    def __repr__(self):
        return f'<Application user "{self.username}">'

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns if c.name != 'to_dict'}

    def get_id(self):
        return self.id


class SMAppUser(AppUserBase):
    __tablename__ = 'app_user'
    __table_args__ = {"schema": "sm"}


class CDVAppUser(AppUserBase):
    __tablename__ = 'app_user'
    __table_args__ = {"schema": "cdv"}
