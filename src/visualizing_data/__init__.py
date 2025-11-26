from flask import Blueprint

bp = Blueprint('visualizing_data', __name__, url_prefix='/data')

from . import routes
