"""
Инициализация Flask Application

Подробнее о структуре приложения:
https://www.digitalocean.com/community/tutorials/how-to-structure-a-large-flask-application-with-flask-blueprints-and-flask-sqlalchemy
"""
__author__ = 'ke.mizonov'
import logging
from flask import Flask
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
from app.commands import create_tables
from config import Config
from app.extensions import db, socketio


def create_app() -> Flask:
    """ Инициализация приложения и всех его компонентов

    Returns:
        экземпляр приложения Flask
    """
    app = Flask(__name__)
    CORS(app)
    app.config.from_object(Config())
    # Logging
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
    # Initialize Flask extensions here
    db.init_app(app)
    socketio.init_app(app, async_mode='eventlet', cors_allowed_origins="*")
    app.scheduler = BackgroundScheduler()
    app.scheduler.start()
    # Register blueprints
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)
    # Register CLI commands
    app.cli.add_command(create_tables)
    return app
