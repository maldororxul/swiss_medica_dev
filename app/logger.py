from typing import Optional, List
from sqlalchemy import Table, MetaData, select
from app import db
from app.engine import get_engine


class DBLogger:
    """ Класс, отвечающий за запись логов в БД """
    def __init__(self, log_model: db.Model, branch: str):
        self.log = log_model
        self.branch = branch
        self.engine = get_engine()

    def add(self, text: str, log_type: int = 1, created_at: Optional[int] = None):
        self.log.add(branch=self.branch, text=text, log_type=log_type, created_at=created_at)

    def get(self, log_type: int = 1, limit: int = 100) -> List[db.Model]:
        table = Table('Log', MetaData(), autoload_with=self.engine, schema=self.branch)
        with self.engine.begin() as connection:
            stmt = select(table)\
                .where(table.c['type'] == log_type, table.c['branch'] == self.branch)\
                .order_by(table.c.id.desc())\
                .limit(limit=limit)
            return connection.execute(stmt).fetchall()
