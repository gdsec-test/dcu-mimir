from flask import Flask
from flask_restplus import Api
from .api import api as ns1


def create_app(config):
    app = Flask(__name__)
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
    return app
