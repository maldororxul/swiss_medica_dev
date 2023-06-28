"""
https://www.digitalocean.com/community/tutorials/how-to-structure-a-large-flask-application-with-flask-blueprints-and-flask-sqlalchemy
"""
import logging
# from celery import Celery
from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler

from app.commands import create_tables
from config import Config
from app.extensions import db, socketio

# Get the logger for 'apscheduler' and set its level to ERROR
logging.getLogger('apscheduler').setLevel(logging.ERROR)


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize Flask extensions here
    db.init_app(app)
    socketio.init_app(app)

    app.scheduler = BackgroundScheduler()
    app.scheduler.start()

    # Register blueprints here
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    app.cli.add_command(create_tables)

    return app


app = create_app()

if __name__ == '__main__':
    socketio.run(app)
