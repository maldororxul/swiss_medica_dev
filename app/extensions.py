""" Расширения Flask-приложения: работа с БД, сокеты """
__author__ = 'ke.mizonov'
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
socketio = SocketIO()
