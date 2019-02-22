import os
import logging

from flask import current_app, request
from flask_restplus import Namespace, Resource, abort
from functools import wraps
from gd_auth.token import AuthToken
from settings import config_by_name
from service.utils.query_helper import QueryHelper

env = os.getenv('sysenv', 'dev')
settings = config_by_name[env]()

query_helper = QueryHelper(settings)

api = Namespace('v1', title='DCU Repeat Infractions API', description='')


def token_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        cn_whitelist = current_app.config.get('cn_whitelist')
        token_authority = current_app.config.get('token_authority')

        if not token_authority:  # bypass if no token authority is set
            return f(*args, **kwargs)

        token = request.headers.get('Authorization', '').strip()
        if not token:
            return {'message': 'Authorization header not provided'}, 401

        if token.startswith('sso-jwt'):
            token = token[8:].strip()

        try:
            token = token.encode() if isinstance(token, str) else token
            auth_token = AuthToken.parse(token, token_authority, 'cert')
            jwt_common_name = auth_token.subject.get('cn')
            if jwt_common_name not in cn_whitelist:
                return {'message': 'Authenticated user is not allowed access'}, 403
        except Exception:
            return {'message': 'Authentication not sent or invalid'}, 401

        return f(*args, **kwargs)

    return wrapped


@api.route('/health', endpoint='health')
class Health(Resource):
    @api.response(200, 'OK')
    def get(self):
        """
        Health check endpoint
        """
        return 'OK', 200

    @api.route('/infractions/<string:infractionId>', endpoint='get_infraction_id')
    class GetInfractionId(Resource):
        _logger = logging.getLogger(__name__)

        @api.doc(params={'infractionId': 'the unique request id to retrieve information for a specific infraction'})
        @api.response(200, 'OK')
        @api.response(401, 'Unauthorized')
        @api.response(403, 'Forbidden')
        @api.response(404, 'Resource Not Found')
        @api.response(422, 'Validation Error')
        def get(self, infractionId):
            """
            Returns information associated with a specific infractionId or a 404 if the id is not found
            """
            try:
                query = query_helper.get_infraction_from_id(infractionId)
            except (KeyError, TypeError, ValueError) as e:
                abort(422, str(e))
            except Exception as e:
                self._logger.warning('Error fetching {}: {}'.format(infractionId, str(e)))
                abort(422, 'Error submitting request')

            if not query:
                abort(404, 'Infraction ID: {} not found'.format(infractionId))

            return query, 200
