import os
import logging

from flask import current_app, request
from flask_restplus import Namespace, Resource, abort, reqparse
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
        @api.doc(security='apikey')
        @token_required
        def get(self, infractionId):
            """
            Returns information associated with a specific infractionId or a 404 if the id is not found
            """
            try:
                query = query_helper.get_infraction_from_id(infractionId)
            except (KeyError, TypeError, ValueError) as e:
                abort(422, e)
            except Exception as e:
                self._logger.warning('Error fetching {}: {}'.format(infractionId, e))
                abort(422, 'Error submitting request')

            if not query:
                abort(404, 'Infraction ID: {} not found'.format(infractionId))

            return query, 200

    @api.route('/infractions', endpoint='get_infractions')
    class GetInfractions(Resource):
        _logger = logging.getLogger(__name__)
        parser = reqparse.RequestParser()
        parser.add_argument('sourceDomainOrIp', type=str, location='args', required=False,
                            help='Domain or IP address')
        parser.add_argument('hostingGuid', type=str, location='args', required=False,
                            help='Hosting account GUID')
        parser.add_argument('shopperId', type=str, location='args', required=False,
                            help='Shopper account number')
        parser.add_argument('infractionType', type=str, location='args', required=False,
                            help='One of three infraction Types: INTENTIONALLY_MALICIOUS, SUSPENDED, or CUSTOMER_WARNING')
        parser.add_argument('startDate', type=str, location='args', required=False,
                            help='Date from which infractions are retrieved. Default 6 months prior to current date. Format: YYYY-MM-DD')
        parser.add_argument('endDate', type=str, location='args', required=False,
                            help='Date up to which infractions are retrieved. Default to current date. Format: YYYY-MM-DD')

        @api.expect(parser)
        @api.response(200, 'OK')
        @api.response(401, 'Unauthorized')
        @api.response(403, 'Forbidden')
        @api.response(404, 'Resource Not Found')
        @api.response(422, 'Validation Error')
        @api.doc(security='apikey')
        @token_required
        def get(self):
            """
            Returns a list infractions associated with the supplied infraction data.
            """
            tmp_args = self.parser.parse_args()

            # Check the parsed args from tmp_args create a new dict that only includes the k:v pairs where value is NOT None
            args = {k: v for k, v in tmp_args.items() if v}

            try:
                query = query_helper.get_infractions(args)
            except (KeyError, TypeError, ValueError) as e:
                abort(422, e)
            except Exception as e:
                self._logger.warning('Error fetching {}: {}'.format(args, e))
                abort(422, 'Error submitting request')

            if not query:
                abort(404, 'Unable to find matching events for {}'.format(args))

            return query
