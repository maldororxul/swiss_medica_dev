from flask import Flask
from flask_socketio import SocketIO, emit


def create_app():
    app = Flask(__name__)
    socketio = SocketIO(app, async_mode='eventlet')

    @app.route('/')
    def index():
        return "Connected"

    @socketio.on('connect')
    def handle_connect():
        print('Client connected')
        emit('response', {'message': 'Connected'})

    @socketio.on('disconnect')
    def handle_disconnect():
        print('Client disconnected')

    return app
