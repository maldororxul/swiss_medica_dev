""" Прочие полезные функции """
__author__ = 'ke.mizonov'
from typing import Dict, Callable


def get_data_from_external_api(handler_func: Callable, request, **args):
    if request.content_type == 'application/json':
        data = request.json
    elif request.content_type == 'application/x-www-form-urlencoded':
        data = request.form.to_dict()
    else:
        return 'Unsupported Media Type', 415
    handler_func(data, **args)
    return 'success', 200


def handle_new_lead(data: Dict) -> str:
    return '\n'.join([f'{key} :: {value}' for key, value in data.items()])
