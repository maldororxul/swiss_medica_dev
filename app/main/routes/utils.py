from typing import Optional, Dict
from flask import request


def get_data_from_post_request(_request) -> Optional[Dict]:
    if request.content_type == 'application/json':
        return _request.json
    elif request.content_type == 'application/x-www-form-urlencoded':
        return _request.form.to_dict()
    else:
        return None
