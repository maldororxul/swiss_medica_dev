""" Лог """
import time
from datetime import datetime
from typing import Optional

from app.extensions import db

LIMIT = 300_000


class LogBase(db.Model):
    __abstract__ = True

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.Integer, nullable=False)
    type = db.Column(db.Integer, nullable=False)        # 1 - сообщение на главном экране
    branch = db.Column(db.String(50))       # sm, cdv
    text = db.Column(db.String(1000))

    def __repr__(self):
        return f'<Log {datetime.fromtimestamp(self.created_at)} :: {self.type} :: "{self.text}">'

    @classmethod
    def add(cls, branch: str, text: str, log_type: int, created_at: Optional[int] = None):
        if not created_at:
            created_at = int(time.time())
        record = cls(branch=branch, text=text, type=log_type, created_at=created_at)
        db.session.add(record)
        # commit the new record first
        db.session.commit()
        # check if there are more than LIMIT records
        if cls.query.count() > LIMIT:
            oldest_record = cls.query.order_by(cls.id).first()
            db.session.delete(oldest_record)
            db.session.commit()

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class SMLog(LogBase):
    __tablename__ = 'Log'
    __table_args__ = {"schema": "sm"}


class CDVLog(LogBase):
    __tablename__ = 'Log'
    __table_args__ = {"schema": "cdv"}
