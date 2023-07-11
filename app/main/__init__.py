from flask import Blueprint

bp = Blueprint('main', __name__)

# маршрутизаторы
from app.main.routes import autocall
from app.main.routes import main
from app.main.routes import socket
from app.main.routes import telegram
