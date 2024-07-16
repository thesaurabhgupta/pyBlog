# c3papplication/__init__.py
import os
from flask import Flask
from c3papplication.oauth.models import db
from c3papplication.oauth.oauth2 import config_oauth
import logging, logging.config

log_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'conf/logging.conf')
logging.config.fileConfig(log_file_path, disable_existing_loggers=False)
logger = logging.getLogger(__name__)


def create_c3p_app():
    app = Flask(__name__)

    setup_app(app)

    with app.app_context():
        from .api import c3p_api_blueprint
        app.register_blueprint(c3p_api_blueprint)
        return app


def setup_app(app):
    # Set the environment variables
    OAUTH2_TOKEN_EXPIRES_IN = {
        'authorization_code': 3600,
        'implicit': 3600,
        'password': 864000,
        'client_credentials': 864000
    }

    config = {
        'SECRET_KEY': 'secret',
        'OAUTH2_REFRESH_TOKEN_GENERATOR': True,
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'OAUTH2_TOKEN_EXPIRES_IN': OAUTH2_TOKEN_EXPIRES_IN,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///db.sqlite',
    }
    app.config.update(config)

    # Create tables if they do not exist already
    @app.before_first_request
    def create_tables():
        db.create_all()

    db.init_app(app)
    config_oauth(app)
    # app.register_blueprint(bp, url_prefix='')
