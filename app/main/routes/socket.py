""" Маршруты для работы веб-сокетов """
__author__ = 'ke.mizonov'
from datetime import datetime
from app import socketio
from app.main.processors import DATA_PROCESSOR


@socketio.on('connect')
def pre_load_from_socket():
    """ Предзагрузка данных через сокет в момент установки соединения """
    # вытаскиваем логи
    logs = []
    for processor_entity in DATA_PROCESSOR.values():
        processor = processor_entity()
        logs.extend(processor.log.get() or [])
    logs = sorted([log for log in logs], key=lambda x: x.created_at)
    for log in logs:
        dt = datetime.fromtimestamp(log.created_at).strftime("%Y-%m-%d %H:%M:%S")
        socketio.emit('new_event', {'msg': f"{dt} :: {log.text[:1000]}"})
