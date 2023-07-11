""" Маршруты для работы с Автообзвоном """
__author__ = 'ke.mizonov'
from flask import redirect, url_for, request
from app.main import bp
from app.main.autocall.handler import Autocall
from app.main.utils import get_data_from_external_api


@bp.route('/autocall_handler', methods=['POST'])
def autocall_handler():
    """
    Call data:
        {
            'number': '995591058618',
            'dateTime': '2023-07-04 14:44:17',
            'status': 'Исходящие, отвеченные',
            'operator': '',
            'record': 'https://sipuni.com/api/callback/record/05578a253f510b1840c67016426218c1',
            'callId': '1688471056.154959'
        }
    """
    return get_data_from_external_api(
        request=request,
        handler_func=Autocall().handle_autocall_result,
    )


@bp.route('/autocall', methods=['POST'])
def init_autocall():
    return get_data_from_external_api(
        request=request,
        handler_func=Autocall().handle_lead_status_changed
    )
