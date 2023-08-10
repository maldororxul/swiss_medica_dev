""" Компания """
__author__ = 'ke.mizonov'
from sqlalchemy.dialects.postgresql import JSON
from app.extensions import db


class CompanyBase(db.Model):
    __abstract__ = True

    id = db.Column(db.Integer, primary_key=True)
    id_on_source = db.Column(db.Integer, unique=True, index=True)
    name = db.Column(db.String(255), nullable=False)
    responsible_user_id = db.Column(db.Integer, nullable=False)
    group_id = db.Column(db.Integer, nullable=False)
    created_by = db.Column(db.Integer, nullable=False)
    updated_by = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.Integer, nullable=False)
    updated_at = db.Column(db.Integer, nullable=False)
    closest_task_at = db.Column(db.Integer)
    custom_fields_values = db.Column(JSON)
    is_deleted = db.Column(db.Boolean, default=False)
    account_id = db.Column(db.Integer, nullable=False)
    _embedded = db.Column(JSON)

    def __repr__(self):
        return f'<Company "{self.name}">'

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns if c.name != 'to_dict'}


class SMCompany(CompanyBase):
    __tablename__ = 'Company'
    __table_args__ = {"schema": "sm"}


class CDVCompany(CompanyBase):
    __tablename__ = 'Company'
    __table_args__ = {"schema": "cdv"}
