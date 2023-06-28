""" Контакт """
from sqlalchemy.dialects.postgresql import JSON
from app.extensions import db


class ContactBase(db.Model):
    __abstract__ = True

    id = db.Column(db.Integer, primary_key=True)
    id_on_source = db.Column(db.Integer)
    name = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    responsible_user_id = db.Column(db.Integer, nullable=False)
    group_id = db.Column(db.Integer, nullable=False)
    created_by = db.Column(db.Integer, nullable=False)
    updated_by = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.Integer, nullable=False)
    updated_at = db.Column(db.Integer, nullable=False)
    is_deleted = db.Column(db.Boolean, default=False)
    is_unsorted = db.Column(db.Boolean, default=False)
    closest_task_at = db.Column(db.Integer)
    custom_fields_values = db.Column(JSON)
    account_id = db.Column(db.Integer, nullable=False)
    _embedded = db.Column(JSON)

    def __repr__(self):
        return f'<Contact "{self.name}">'

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class SMContact(ContactBase):
    __tablename__ = 'Contact'
    __table_args__ = {"schema": "sm"}


class CDVContact(ContactBase):
    __tablename__ = 'Contact'
    __table_args__ = {"schema": "cdv"}
