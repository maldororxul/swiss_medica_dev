""" Сделка """
__author__ = 'ke.mizonov'
from sqlalchemy.dialects.postgresql import JSON
from app.extensions import db


class LeadBase(db.Model):
    __abstract__ = True

    id = db.Column(db.Integer, primary_key=True)
    id_on_source = db.Column(db.Integer, unique=True, index=True)
    # source_id = db.Column(db.Integer)
    name = db.Column(db.String(255), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    responsible_user_id = db.Column(db.Integer, nullable=False)
    group_id = db.Column(db.Integer, nullable=False)
    status_id = db.Column(db.Integer, nullable=False)
    pipeline_id = db.Column(db.Integer, nullable=False)
    loss_reason_id = db.Column(db.Integer)
    created_by = db.Column(db.Integer, nullable=False)
    updated_by = db.Column(db.Integer, nullable=False)
    closed_at = db.Column(db.Integer)
    created_at = db.Column(db.Integer, nullable=False)
    updated_at = db.Column(db.Integer, nullable=False)
    closest_task_at = db.Column(db.Integer)
    is_deleted = db.Column(db.Boolean, default=False)
    custom_fields_values = db.Column(JSON)
    score = db.Column(db.Integer)
    account_id = db.Column(db.Integer, nullable=False)
    labor_cost = db.Column(db.Integer)
    is_price_modified_by_robot = db.Column(db.Boolean, default=False)
    _embedded = db.Column(JSON)

    def __repr__(self):
        return f'<Lead "{self.name}">'

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns if c.name != 'to_dict'}


class SMLead(LeadBase):
    __tablename__ = 'Lead'
    __table_args__ = {"schema": "sm"}


class CDVLead(LeadBase):
    __tablename__ = 'Lead'
    __table_args__ = {"schema": "cdv"}
