from flask import Blueprint

bp = Blueprint('main', __name__)

# from .tasks import add_random_lead
from app.main import routes
