import os

from flask_restplus import Namespace, Resource
from settings import config_by_name

settings = config_by_name[os.getenv('sysenv', 'dev')]()

api = Namespace('v1', title='DCU Repeat Infractions API', description='')


@api.route('/health', endpoint='health')
class Health(Resource):
    @api.response(200, 'OK')
    def get(self):
        """
        Health check endpoint
        """
        return 'OK', 200
