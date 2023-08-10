""" Задача """
__author__ = 'ke.mizonov'
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSON
from app.extensions import db


class TaskBase(db.Model):
    __abstract__ = True

    id = db.Column(db.Integer, primary_key=True)
    id_on_source = db.Column(db.Integer, unique=True, index=True)
    created_by = db.Column(db.Integer, nullable=False)
    updated_by = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.Integer, nullable=False, default=lambda: int(datetime.now().timestamp()))
    updated_at = db.Column(db.Integer, nullable=False, default=lambda: int(datetime.now().timestamp()))
    responsible_user_id = db.Column(db.Integer, nullable=False)
    group_id = db.Column(db.Integer, nullable=False)
    entity_id = db.Column(db.Integer, nullable=False)
    entity_type = db.Column(db.String, nullable=False)
    is_completed = db.Column(db.Boolean, default=False)
    task_type_id = db.Column(db.Integer, nullable=False)
    text = db.Column(db.String, nullable=True)
    duration = db.Column(db.Integer, nullable=False)
    complete_till = db.Column(db.Integer, nullable=False)
    result = db.Column(JSON, nullable=True)
    account_id = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f'<Task "{self.text}">'

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns if c.name != 'to_dict'}


class SMTask(TaskBase):
    __tablename__ = 'Task'
    __table_args__ = {"schema": "sm"}


class CDVTask(TaskBase):
    __tablename__ = 'Task'
    __table_args__ = {"schema": "cdv"}
