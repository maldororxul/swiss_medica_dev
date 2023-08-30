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
from apscheduler.events import (
    EVENT_SCHEDULER_STARTED,
    EVENT_SCHEDULER_SHUTDOWN,
    EVENT_SCHEDULER_PAUSED,
    EVENT_SCHEDULER_RESUMED,
    EVENT_JOB_EXECUTED,
    EVENT_JOB_ERROR,
    EVENT_JOB_MISSED
)
from app.commands import create_tables
from app.event_listener import scheduler_listener
from app.main.routes.autocall import start_autocalls
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
    app.scheduler.add_listener(
        scheduler_listener,
        EVENT_SCHEDULER_STARTED | EVENT_SCHEDULER_SHUTDOWN | EVENT_SCHEDULER_PAUSED | EVENT_SCHEDULER_RESUMED |
        EVENT_JOB_MISSED | EVENT_JOB_EXECUTED | EVENT_JOB_ERROR
    )
    # запускаем фоновые задачи
    start_autocalls()
    # app.scheduler.start()
    # Register blueprints
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)
    # Register CLI commands
    app.cli.add_command(create_tables)
    return app
