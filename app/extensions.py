""" Расширения Flask-приложения: работа с БД, сокеты """
__author__ = 'ke.mizonov'
import json
from datetime import date, datetime
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
socketio = SocketIO()


class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime) or isinstance(obj, date):
            return obj.isoformat()  # Convert datetime to string in ISO format
        return super().default(obj)
