import os

from csetutils.flask import instrument
from flask import Flask
from flask_cors import CORS
from flask_restx import Api

from .api import api as ns1


def create_app(config):
    app = Flask(__name__)
    instrument(app, service_name='mimir', env=os.getenv('sysenv', 'dev'), sso=config.TOKEN_AUTHORITY, excluded_paths=[
        '/doc',
        '/swagger',
        '/v1/health'
    ])

    app.config.SWAGGER_UI_JSONEDITOR = True
    app.config.SWAGGER_UI_DOC_EXPANSION = 'list'
    authorizations = {
        'apikey': {
            'type': 'apiKey',
            'in': 'header',
            'name': 'Authorization'
        }
    }
    api = Api(
        app,
        version='1.0',
        title='DCU Repeat Infractions API',
        description='Provides insights about past infractions on domains, hosting, and shoppers.',
        validate=True,
        doc='/doc',
        authorizations=authorizations
    )
    app.config['token_authority'] = config.TOKEN_AUTHORITY
    app.config['cn_whitelist'] = config.CN_WHITELIST
    app.config['auth_groups'] = config.AUTH_GROUPS
    api.add_namespace(ns1)
    CORS(app, origins=['http://localhost:5000', 'http://127.0.0.1:5000', r'^https.*(-|\.)godaddy.com.*$'],
         supports_credentials=True)
    return app
