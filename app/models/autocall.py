""" Список автообзвона """
from app.extensions import db


class AutocallNumberBase(db.Model):
    __abstract__ = True

    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, nullable=False)
    number = db.Column(db.String(20), nullable=False)

    def __repr__(self):
        return f'<Autocall Number "{self.number}">'

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class SMAutocallNumber(AutocallNumberBase):
    __tablename__ = 'AutocallNumber'
    __table_args__ = {"schema": "sm"}


class CDVAutocallNumber(AutocallNumberBase):
    __tablename__ = 'AutocallNumber'
    __table_args__ = {"schema": "cdv"}
