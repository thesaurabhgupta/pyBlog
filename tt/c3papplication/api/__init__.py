# c3papplication/api/__init__.py
from flask import Blueprint
from flask_cors import CORS

c3p_api_blueprint = Blueprint('api', __name__)
CORS(c3p_api_blueprint)
CORS(c3p_api_blueprint, resources={r"/*": {"origins": "*"}}) # enable CORS on the c3p_apis blue print
from . import routes,routes2
