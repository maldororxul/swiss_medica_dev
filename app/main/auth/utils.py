from functools import wraps
from flask_login import current_user
from flask import abort


def requires_roles(*roles):
    def wrapper(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role.name not in roles:
                abort(403)
            return f(*args, **kwargs)
        return wrapped
    return wrapper
