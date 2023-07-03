import logging
import os
from datetime import datetime, timedelta
from apscheduler.jobstores.base import JobLookupError
from flask import render_template, jsonify, current_app, redirect, url_for, request, stream_with_context, Response, \
    send_file
from app import db, socketio
from app.amo.api.client import SwissmedicaAPIClient, DrvorobjevAPIClient
from app.logger import DBLogger
from app.main import bp
from app.main.processors import DATA_PROCESSOR
from app.main.tasks import get_data_from_amo, update_pivot_data
from app.models.data import SMData
from app.models.event import SMEvent
from app.models.lead import SMLead
from app.models.log import SMLog
from app.utils.excel import ExcelClient


API_CLIENT = {
    'SM': SwissmedicaAPIClient,
    'CDV': DrvorobjevAPIClient,
}


@bp.route('/')
def index():
    processor = DATA_PROCESSOR.get('sm')()
    # processor.add_log(branch='sm', text='test', log_type=1)
    # # тащим лог
    # for log in processor.get_logs(branch='sm') or []:
    #     dt = datetime.fromtimestamp(log.created_at).strftime("%Y-%m-%d %H:%M:%S")
    #     socketio.emit('new_event', {'msg': f'{dt} :: {log.text}'})
    # границы данных
    df, dt = processor.get_data_borders()
    date_from = datetime.fromtimestamp(df) if df else None
    date_to = datetime.fromtimestamp(dt) if dt else None
    date_curr = date_from + timedelta(minutes=60) if date_from else datetime.now()

    # app = current_app._get_current_object()
    # app.scheduler.add_job(
    #     id='get_logs',
    #     func=socketio.start_background_task,
    #     args=[get_logs, app, 'sm'],
    #     trigger='interval',
    #     seconds=5,
    #     max_instances=1
    # )
    # if not app.scheduler.running:
    #     app.scheduler.start()

    return render_template(
        'index.html',
        sm_df=date_from,
        sm_dt=date_to,
        sm_curr=date_curr.strftime("%Y-%m-%dT%H:%M")
    )


@bp.route('/get_token', methods=['GET'])
def get_token():
    return render_template('get_token.html')


@bp.route('/get_token', methods=['POST'])
def send_auth_code():
    auth_code = request.form.get('auth_code')
    client_id = request.form.get('client_id')
    client_secret = request.form.get('client_secret')
    redirect_url = request.form.get('redirect_url')
    branch = request.form.get('branch')
    # записываем креды в БД
    with current_app.app_context():
        api_client = API_CLIENT.get(branch)()
        api_client.get_token(
            auth_code=auth_code,
            client_id=client_id,
            client_secret=client_secret,
            redirect_url=redirect_url,
        )
    return redirect(url_for('main.get_token'))


@bp.route('/leads')
def get_leads():
    leads = SMLead.query.all()
    return jsonify([{"id": lead.id, "name": lead.name} for lead in leads])


@bp.route('/events')
def get_events():
    # fixme tmp
    collection = SMEvent.query.all()
    return jsonify([x.to_dict() for x in collection])


@bp.route('/sm_data')
def get_data():
    collection = SMData.query.all()
    return jsonify([x.to_dict() for x in collection])


@bp.route('/sm_data_excel')
def data_to_excel():
    collection = SMData.query.all()
    data = [(x.to_dict() or {}).get('data') for x in collection]
    # print(type(data[0]['created_at']))
    ExcelClient(file_path=os.path.join('app', 'data'), file_name='sm_data').write(data=[
        ExcelClient.Data(data=data)
    ])
    return send_file(os.path.join('data', 'sm_data.xlsx'), as_attachment=True)


@bp.route('/sm_data_csv')
def data_to_csv():
    # conn = psycopg2.connect(database="your_database", user="your_username", password="your_password", host="127.0.0.1", port="5432")
    # cursor = conn.cursor()
    #
    # query = "SELECT * FROM your_table"
    # cursor.execute(query)

    def generate():
        # data = ['data']
        # print(data)
        # yield f'data\n'
        collection = SMData.query.all()
        for row in collection[:-1]:
            yield f"{row.data};"
        yield collection[-1].data

    # string = ''.join(generate())
    # result = ''
    # for num, c in enumerate(string, 1):
    #     if num > 13000 and num < 14200:
    #         result += c
    # print(result)

    return Response(stream_with_context(generate()), mimetype='text/csv')


# @bp.route('/build')
# def build():
#     date_from = datetime(2023, 6, 20, 0, 0, 0)
#     date_to = datetime(2023, 6, 20, 23, 59, 59)
#     with current_app.app_context():
#         collection = []
#         for line in SMDataProcessor(date_from=date_from, date_to=date_to).update() or []:
#             item = {key.split('_(')[0]: value for key, value in line.items()}
#             collection.append({
#                 'id': line['id'],
#                 'updated_at': line['updated_at_ts'],
#                 'data': json.dumps(item, cls=DateTimeEncoder)
#             })
#         SMSyncController(date_from=date_from, date_to=date_to).update_data(collection=collection)
#     return ''


# @socketio.on('connect')
# def test_connect():
#     print('Client connected')
#
#
# @socketio.on('disconnect')
# def test_disconnect():
#     print('Client disconnected')


@bp.route('/webhook', methods=['POST'])
def handle_webhook():
    data = request.get_json()
    db_logger = DBLogger(branch='sm', log_model=SMLog)
    db_logger.add(text='test 666 webhook', log_type=1)
    socketio.emit('new_event', {'msg': f'test 666 webhook {data}'})
    current_app.logger.setLevel(logging.INFO)
    current_app.logger.info('test 666 webhook')  # or do something else with the data
    return jsonify({'status': 'ok'}), 200


@socketio.on('connect')
def pre_load_from_socket():
    """ Предзагрузка данных через сокет в момент установки соединения """
    processor = DATA_PROCESSOR.get('sm')()
    logs = processor.log.get(branch='sm') or []
    logs.reverse()
    for log in logs:
        dt = datetime.fromtimestamp(log.created_at).strftime("%Y-%m-%d %H:%M:%S")
        socketio.emit('new_event', {'msg': f'{dt} :: {log.text}'})


@bp.route('/button1')
def start_sm():
    lowest_dt = datetime.strptime(request.args.get('time', default=None, type=str), "%Y-%m-%dT%H:%M")
    # current_app - это проксированный экземпляр приложения,
    # _get_current_object - доступ к объекту приложения напрямую
    # с проксированным объектом получается некорректный контекст => костыляем
    app = current_app._get_current_object()
    # загрузка данных из Amo SM
    try:
        app.scheduler.remove_job('get_data_from_amo_sm')
    except JobLookupError:
        pass
    app.scheduler.add_job(
        id='get_data_from_amo_sm',
        func=socketio.start_background_task,
        args=[get_data_from_amo, app, 'sm', lowest_dt],
        trigger='interval',
        seconds=5,
        max_instances=1
    )
    if not app.scheduler.running:
        app.scheduler.start()
    # загрузка данных из Amo CDV
    # app.scheduler.add_job(
    #     id='get_data_from_amo_cdv',
    #     func=get_data_from_amo,
    #     args=[app, 'cdv'],
    #     trigger='interval',
    #     seconds=5,
    #     max_instances=1
    # )
    return render_template('index.html')
    # return 'started scheduler "get data from amo"'


@bp.route('/start_update_pivot_data')
def start_update_pivot_data():
    app = current_app._get_current_object()
    # обновление данных для сводной таблицы SM
    app.scheduler.add_job(
        id='update_pivot_data_sm',
        func=update_pivot_data,
        args=[app, 'sm'],
        trigger='interval',
        seconds=5,
        max_instances=1
    )
    return 'started scheduler "update pivot data"'


@bp.route('/create_all')
def create_all():
    # ипорты нужны для создания структуры БД!
    from app.models.amo_credentials import CDVAmoCredentials, SMAmoCredentials
    from app.models.amo_token import SMAmoToken, CDVAmoToken
    from app.models.contact import SMContact, CDVContact
    from app.models.event import SMEvent, CDVEvent
    from app.models.lead import CDVLead, SMLead
    from app.models.note import SMNote, CDVNote
    from app.models.pipeline import CDVPipeline, SMPipeline
    from app.models.user import SMUser, CDVUser
    from app.models.task import SMTask, CDVTask
    from app.models.company import SMCompany, CDVCompany
    from app.models.data import SMData, CDVData
    from app.models.log import SMLog, CDVLog
    with current_app.app_context():
        db.create_all()
    return 'tables created'


@bp.route('/drop_all')
def drop_all():
    with current_app.app_context():
        db.drop_all()
    return 'tables dropped'
