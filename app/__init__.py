"""
Инициализация Flask Application

Подробнее о структуре приложения:
https://www.digitalocean.com/community/tutorials/how-to-structure-a-large-flask-application-with-flask-blueprints-and-flask-sqlalchemy
"""
__author__ = 'ke.mizonov'
import logging
from datetime import timedelta
from flask import Flask
from flask_login import LoginManager
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
from app.commands import create_tables
from app.models.app_user import SMAppUser
from config import Config
from app.extensions import db, socketio

login_manager = LoginManager()


@login_manager.user_loader
def load_user(user_id: int):
    return SMAppUser.query.get(int(user_id))


def create_app() -> Flask:
    """ Инициализация приложения и всех его компонентов

    Returns:
        экземпляр приложения Flask
    """
    app = Flask(__name__)
    CORS(app)
    app.config.from_object(Config())
    app.config['SESSION_COOKIE_SECURE'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
    # Logging
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
    # Initialize Flask extensions here
    db.init_app(app)
    login_manager.init_app(app)
    socketio.init_app(app, async_mode='eventlet', cors_allowed_origins="*")
    app.scheduler = BackgroundScheduler()
    # Register blueprints
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)
    # Login endpoint
    login_manager.login_view = 'main.login'
    # Register CLI commands
    app.cli.add_command(create_tables)
    # запускаем фоновые задачи
    from app.main.sync.run import run as run_amo_data_sync
    # загрузка данных из Amo
    for branch in ('sm', ):
        app.scheduler.add_job(
            id=f'amo_data_sync_{branch}',
            func=socketio.start_background_task,
            args=[run_amo_data_sync, app, branch],
            trigger='interval',
            seconds=60,
            max_instances=1
        )
    app.scheduler.start()
    return app
