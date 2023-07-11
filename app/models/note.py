""" Примечание """
__author__ = 'ke.mizonov'
from sqlalchemy.dialects.postgresql import JSON
from app.extensions import db


class NoteBase(db.Model):
    __abstract__ = True

    id = db.Column(db.Integer, primary_key=True)
    id_on_source = db.Column(db.Integer)
    entity_id = db.Column(db.Integer, nullable=False)
    created_by = db.Column(db.Integer, nullable=False)
    updated_by = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.Integer, nullable=False)
    updated_at = db.Column(db.Integer, nullable=False)
    responsible_user_id = db.Column(db.Integer, nullable=False)
    group_id = db.Column(db.Integer, nullable=False)
    note_type = db.Column(db.String(100), nullable=False)
    params = db.Column(JSON)
    account_id = db.Column(db.Integer, nullable=False)
    _embedded = db.Column(JSON)

    def __repr__(self):
        return f'<Note "{self.id}">'

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class SMNote(NoteBase):
    __tablename__ = 'Note'
    __table_args__ = {"schema": "sm"}


class CDVNote(NoteBase):
    __tablename__ = 'Note'
    __table_args__ = {"schema": "cdv"}
