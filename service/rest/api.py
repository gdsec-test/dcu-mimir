import copy
import logging
import os
from functools import wraps
from urllib.parse import urlencode, urlparse, urlunparse

from flask import current_app, request
from flask_restplus import Namespace, Resource, abort, fields, reqparse
from gd_auth.token import AuthToken
from redlock import RedLockError

from service.utils.query_helper import QueryHelper
from settings import config_by_name

env = os.getenv('sysenv', 'dev')
settings = config_by_name[env]()

query_helper = QueryHelper(settings)

api = Namespace('v1', title='DCU Repeat Infractions API', description='')

infraction_types = ['INTENTIONALLY_MALICIOUS',
                    'SUSPENDED',
                    'CUSTOMER_WARNING',
                    'REPEAT_OFFENDER',
                    'EXTENSIVE_COMPROMISE',
                    'CONTENT_REMOVED',
                    'SHOPPER_COMPROMISE',
                    'MALWARE_SCANNER_NOTICE']

infraction_event = api.model(
    'InfractionEvent', {
        'infractionType': fields.String(required=True, description='the infraction type', enum=infraction_types),
        'ticketId': fields.String(require=True, description='ticket or incident associated with the infraction'),
        'sourceDomainOrIp': fields.String(required=True, description='domain associated with the infraction',
                                          example='godaddy.com'),
        'hostingGuid': fields.String(required=True, description='hosting guid associated with the infraction',
                                     example='testguid-test-guid-test-guidtest1234'),
        'shopperId': fields.String(required=True, description='shopper account associated with the infraction',
                                   example='abc123'),
    })

infraction_result = api.model(
    'InfractionCreationResponse', {
        'infractionId': fields.String(required=True, description='monotonically increasing request id',
                                      example='f9c8e07373d4471cac5c4027ac6db034')
    }
)

infraction_id_result = api.inherit(
    'InfractionIdResult', infraction_event, {
        'infractionId': fields.String(required=True, description='monotonically increasing request id',
                                      example='f9c8e07373d4471cac5c4027ac6db034'),
        'createdDate': fields.String(required=True, description='Creation date of infraction',
                                     example='2019-02-17 02:29:08.929Z')
    }
)

pagination = api.model(
    'Pagination', {
        'next': fields.String(required=True, description='Url for the next batch of maching infractions',
                              example='https://mimir.int.godaddy.com/infractions?sourceDomainOrIp=abcs.com&limit=25&offset=25'),
        'prev': fields.String(required=True, description='Url for the previous batch of maching infractions',
                              example='https://mimir.int.godaddy.com/infractions?sourceDomainOrIp=abcs.com&limit=25&offset=0')

    }
)

infractions_response = api.model(
    'InfractionsResponse', {
        'infractions': fields.List(fields.Nested(infraction_id_result), required=True),
        'pagination': fields.Nested(pagination, required=True)
    }
)


def token_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        forbidden = {'message': 'Authenticated user is not allowed access'}, 403

        auth_groups = current_app.config.get('auth_groups')
        cn_whitelist = current_app.config.get('cn_whitelist')

        token_authority = current_app.config.get('token_authority')

        if not token_authority:  # bypass if no token authority is set
            return f(*args, **kwargs)

        token = request.headers.get('Authorization', '').strip() or request.cookies.get('auth_jomax')
        if not token:
            return {'message': 'Authorization header not provided'}, 401

        if token.startswith('sso-jwt'):
            token = token[8:].strip()

        try:
            token = token.encode() if isinstance(token, str) else token

            # Parse the payload without validating, and then parse and validate with the appropriate type
            payload = AuthToken.payload(token)
            typ = payload.get('typ')
            parsed = AuthToken.parse(token, token_authority, 'Mimir', typ)

            if typ == 'jomax':
                approved_groups = set(parsed.payload.get('groups', []))
                if not approved_groups.intersection(auth_groups):
                    return forbidden
            elif typ == 'cert':
                if parsed.subject.get('cn') not in cn_whitelist:
                    return forbidden
            else:
                return forbidden

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


@api.route('/infractions', endpoint='infractions')
class Infractions(Resource):
    _logger = logging.getLogger(__name__)

    # Initialize parser for parsing query string from <get> endpoint.
    parser = reqparse.RequestParser()
    parser.add_argument('sourceDomainOrIp', type=str, location='args', required=False,
                        help='Domain or IP address')
    parser.add_argument('hostingGuid', type=str, location='args', required=False,
                        help='Hosting account GUID')
    parser.add_argument('shopperId', type=str, location='args', required=False,
                        help='Shopper account number')
    parser.add_argument('infractionType', type=str, location='args', required=False,
                        help='One of {} infraction Types: {}'.format(len(infraction_types), infraction_types))
    parser.add_argument('startDate', type=str, location='args', required=False,
                        help='Date from which infractions are retrieved. Default 6 months prior to current date. Format: YYYY-MM-DD')
    parser.add_argument('endDate', type=str, location='args', required=False,
                        help='Date up to which infractions are retrieved. Default to current date. Format: YYYY-MM-DD')
    parser.add_argument('limit', type=int, location='args', required=False,
                        help='Number of infractions to be retrieved in every get request. This value is defaulted to 25')
    parser.add_argument('offset', type=int, location='args', required=False,
                        help='Index of the record from which the next batch of infractions is to be retrieved. This value is defaulted to 0.')

    QUERY_PARAMETERS = 4
    PATH = 2
    PAGINATION_LIMIT = 25
    PAGINATION_OFFSET = 0

    @api.expect(infraction_event)
    @api.marshal_with(infraction_result)
    @api.response(200, 'OK')
    @api.response(201, 'Created')
    @api.response(400, 'Bad Request')
    @api.response(401, 'Unauthorized')
    @api.response(403, 'Forbidden')
    @api.response(422, 'Validation Error')
    @api.doc(security='apikey')
    @token_required
    def post(self):
        """
        Returns the Event ID and 201 upon successful creation of Infraction Event
        Returns the Event ID and 200 upon attempted submission of duplicate data entered with the last 24 hours
        """
        data = request.json

        try:
            infraction_id, duplicate = query_helper.insert_infraction(data)

            status = 200 if duplicate else 201
            return {'infractionId': str(infraction_id) if infraction_id else ''}, status
        except (KeyError, TypeError, ValueError) as e:
            abort(422, e)
        except RedLockError as e:
            self._logger.warning('Error while acquiring the lock {}: {}'.format(data, e))
            abort(422, 'Error submitting request')
        except Exception as e:
            self._logger.warning('Error submitting {}: {}'.format(data, e))
            abort(422, 'Error submitting request')

    @api.expect(parser)
    @api.marshal_with(infractions_response)
    @api.response(200, 'OK')
    @api.response(401, 'Unauthorized')
    @api.response(403, 'Forbidden')
    @api.response(422, 'Validation Error')
    @api.doc(security='apikey')
    @token_required
    def get(self):
        """
        Returns a list infractions and the pagination information associated with the supplied infraction data.
        """
        tmp_args = self.parser.parse_args()

        # Check the parsed args from tmp_args create a new dict that only includes the k:v pairs where value is NOT None
        args = {k: v for k, v in tmp_args.items() if v}

        """
        Creating a copy of the query parameters passed in the request as the args dictionary gets modified in
        the dcdatabase library. For instance parameters like startDate and endDate are popped from the args
        dictionary in the input validation phase.
        """
        input_args = copy.deepcopy(args)

        response_dict = {}
        try:
            response_dict['infractions'] = query_helper.get_infractions(args)
            response_dict['pagination'] = self._create_paginated_links(self.api.base_url, self.endpoint, input_args)

        except (KeyError, TypeError, ValueError) as e:
            abort(422, e)
        except Exception as e:
            self._logger.warning('Error fetching {}: {}'.format(args, e))
            abort(422, 'Error submitting request')

        if not response_dict.get('infractions') or \
                len(response_dict.get('infractions', [])) < input_args.get('limit', self.PAGINATION_LIMIT):
            response_dict.get('pagination', {}).update({'next': None})

        return response_dict

    def _create_paginated_links(self, base_url, endpoint, args):
        """
        Method to create paginated links
        :param base_url: Base url mimir depending on the environment in which it is hosted
        :param endpoint: Actual endpoint that is currently being accessed
        :param args: Dictionary of query parameters that are passed in the http request.
        :return Dictionary of paginated links containing the next and previous url
        """
        args.update({'limit': args.get('limit', self.PAGINATION_LIMIT)})
        offset = args.pop('offset', self.PAGINATION_OFFSET)
        return {
            'next': '{}'.format(self._construct_next_url(base_url, endpoint, args, offset)),
            'prev': '{}'.format(self._construct_prev_url(base_url, endpoint, args, offset))
        }

    def _construct_next_url(self, base_url, endpoint, args, offset):
        """
        Method to construct the next url for pagination based on query parameters.
        This method uses urlparse method from urllib and breaks the url into 6 parts namely
        scheme (0), netloc (1), path (2), params= (3), query=(4), and fragment= (5)
        :param base_url: Base url for mimir depending on the environment in which it is hosted
        :param endpoint: Actual endpoint that is currently being accessed
        :param args: Dictionary of query parameters that are passed in the http request.
        :param offset: Index of the record from which the next batch of infractions is to be retrieved.
        :return Next url with the appropriate query parameters
        """
        args.update({'offset': offset + args.get('limit')})
        url_parts = list(urlparse(base_url))
        url_parts[self.PATH] = endpoint
        url_parts[self.QUERY_PARAMETERS] = urlencode(args)
        return urlunparse(url_parts)

    def _construct_prev_url(self, base_url, endpoint, args, offset):
        """
        Method to construct the previous url for pagination based on query parameters
        This method uses urlparse method from urllib and breaks the url into 6 parts namely
        scheme (0), netloc (1), path (2), params= (3), query=(4), and fragment= (5)
        :param base_url: Base url for mimir depending on the environment in which it is hosted
        :param endpoint: Actual endpoint that is currently being accessed
        :param args: Dictionary of query parameters that are passed in the http request.
        :param offset: Index of the record from which the next batch of infractions is to be retrieved.
        :return Next url with the appropriate query parameters
        """
        args.update({'offset': offset - args.get('limit')})
        if args.get('offset') < 0:
            args.update({'offset': 0})

        url_parts = list(urlparse(base_url))
        url_parts[self.PATH] = endpoint
        url_parts[self.QUERY_PARAMETERS] = urlencode(args)
        return urlunparse(url_parts)


@api.route('/infractions/<string:infractionId>', endpoint='get_infraction_id')
class GetInfractionId(Resource):
    _logger = logging.getLogger(__name__)

    @api.doc(params={'infractionId': 'the unique request id to retrieve information for a specific infraction'})
    @api.marshal_with(infraction_id_result)
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
