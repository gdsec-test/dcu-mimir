import copy
import logging
import os
from functools import wraps
from urllib.parse import urlencode, urlparse, urlunparse

from flask import abort, current_app, request
from flask_restplus import Namespace, Resource, fields, reqparse
from gd_auth.token import AuthToken
from redlock import RedLockError

from service.utils.query_helper import QueryHelper
from settings import config_by_name

env = os.getenv('sysenv', 'dev')
settings = config_by_name[env]()

query_helper = QueryHelper(settings)

api = Namespace('v1', title='DCU Repeat Infractions API', description='')

infraction_types = ['CONTENT_REMOVED',
                    'CUSTOMER_WARNING',
                    'EXTENSIVE_COMPROMISE',
                    'INTENTIONALLY_MALICIOUS',
                    'MALWARE_SCANNER_NOTICE',
                    'MANUAL_NOTE',
                    'NCMEC_REPORT_SUBMITTED',
                    'REPEAT_OFFENDER',
                    'SHOPPER_COMPROMISE',
                    'SUSPENDED',
                    'SUSPENDED_CSAM',
                    'USERGEN_WARNING']

abuse_types = ['A_RECORD',
               'CHILD_ABUSE',
               'CONTENT',
               'FRAUD_WIRE',
               'IP_BLOCK',
               'MALWARE',
               'NETWORK_ABUSE',
               'PHISHING',
               'SPAM']

infraction_record_type = 'INFRACTION'
non_inf_record_types = ['NOTE', 'NCMEC_REPORT']
hosting_status_types = ['HOSTED', 'REGISTERED']

KEY_INFRACTIONS = 'infractions'
KEY_INFRACTION_TYPES = 'infractionTypes'
KEY_LIMIT = 'limit'
KEY_OFFSET = 'offset'
KEY_NEXT = 'next'
KEY_PAGINATION = 'pagination'
KEY_PREV = 'prev'
KEY_RECORD_TYPE = 'recordType'

# Initialize parser for parsing query string from the "infractions" and "infraction_count" <get> endpoint.
parser = reqparse.RequestParser()
parser.add_argument('sourceDomainOrIp', type=str, location='args', required=False,
                    help='Domain or IP address')
parser.add_argument('hostingGuid', type=str, location='args', required=False,
                    help='Hosting account GUID')
parser.add_argument('domainId', type=str, location='args', required=False,
                    help='ID of domain name')
parser.add_argument('shopperId', type=str, location='args', required=False,
                    help='Shopper account number')
parser.add_argument(KEY_INFRACTION_TYPES, type=str, location='args', required=False, action='append',
                    help='List containing zero or more of {} infraction types: {}'.format(len(infraction_types),
                                                                                          infraction_types))
parser.add_argument('abuseTypes', type=str, location='args', required=False, action='append',
                    help='List containing zero or more of {} abuse types: {}'.format(len(abuse_types), abuse_types))
parser.add_argument('startDate', type=str, location='args', required=False,
                    help='Date from which infractions are retrieved. Default 6 months prior to current date. Format: YYYY-MM-DD')
parser.add_argument('endDate', type=str, location='args', required=False,
                    help='Date up to which infractions are retrieved. Default to current date. Format: YYYY-MM-DD')
parser.add_argument(KEY_LIMIT, type=int, location='args', required=False,
                    help='Number of infractions to be retrieved in every get request. This value is defaulted to 25')
parser.add_argument(KEY_OFFSET, type=int, location='args', required=False,
                    help='Index of the record from which the next batch of infractions is to be retrieved. This value is defaulted to 0.')
parser.add_argument('note', type=str, location='args', required=False,
                    help='Any note associated with the infraction')
parser.add_argument('ncmecReportID', type=str, location='args', required=False,
                    help='ncmecReportID associated with NCMEC Report submission')

infraction_event = api.model(
    'InfractionEvent', {
        'infractionType': fields.String(required=True, description='the infraction type', enum=infraction_types),
        KEY_RECORD_TYPE: fields.String(require=True, description='the type of record', example=infraction_record_type),
        'ticketId': fields.String(require=False, description='ticket or incident associated with the infraction'),
        'sourceDomainOrIp': fields.String(required=True, description='domain associated with the infraction',
                                          example='godaddy.com'),
        'sourceSubDomain': fields.String(required=False, description='subdomain associated with the infraction',
                                         example='abc.godaddy.com'),
        'hostedStatus': fields.String(required=True, description='domain hosting status', enum=hosting_status_types),
        'domainId': fields.String(required=False, description='domain ID for the domain associated with the infraction',
                                  example='123456'),
        'hostingGuid': fields.String(required=False, description='hosting guid associated with the infraction',
                                     example='testguid-test-guid-test-guidtest1234'),
        'shopperId': fields.String(required=True, description='shopper account associated with the infraction',
                                   example='abc123'),
        'note': fields.String(required=False, description='note associated with the infraction',
                              example='ticket sent to ncmec'),
        'ncmecReportID': fields.String(required=False, description='ncmecReportID associated with the NCMEC_REPORT_SUBMITTED infraction',
                                       example='1234'),
        'abuseType': fields.String(required=True, description='the abuse type', enum=abuse_types)
    })

non_infraction_event = api.model(
    'NonInfractionEvent', {
        'infractionType': fields.String(required=False, description='the infraction type', enum=infraction_types),
        'ticketId': fields.String(require=False, description='ticket or incident associated with the infraction'),
        'sourceDomainOrIp': fields.String(required=True, description='domain associated with the infraction',
                                          example='godaddy.com'),
        'hostedStatus': fields.String(required=False, description='domain hosting status', enum=hosting_status_types),
        'domainId': fields.String(required=False, description='domain ID for the domain associated with the infraction',
                                  example='123456'),
        'hostingGuid': fields.String(required=False, description='hosting guid associated with the infraction',
                                     example='testguid-test-guid-test-guidtest1234'),
        'shopperId': fields.String(required=True, description='shopper account associated with the infraction',
                                   example='abc123'),
        KEY_RECORD_TYPE: fields.String(required=True, description='the record type', enum=non_inf_record_types),
        'abuseType': fields.String(required=True, description='the abuse type', enum=abuse_types)
    })

infraction_result = api.model(
    'InfractionCreationResponse', {
        'infractionId': fields.String(required=True, description='monotonically increasing request id',
                                      example='f9c8e07373d4471cac5c4027ac6db034')
    }
)

non_infraction_result = api.model(
    'NonInfractionCreationResponse', {
        'recordId': fields.String(required=True, description='monotonically increasing request id',
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
        KEY_NEXT: fields.String(required=True, description='Url for the next batch of maching infractions',
                                example='https://mimir.int.godaddy.com/infractions?sourceDomainOrIp=abcs.com&limit=25&offset=25'),
        KEY_PREV: fields.String(required=True, description='Url for the previous batch of maching infractions',
                                example='https://mimir.int.godaddy.com/infractions?sourceDomainOrIp=abcs.com&limit=25&offset=0')

    }
)

infractions_response = api.model(
    'InfractionsResponse', {
        KEY_INFRACTIONS: fields.List(fields.Nested(infraction_id_result), required=True),
        KEY_PAGINATION: fields.Nested(pagination, required=True)
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


class PaginationLinks(Resource):
    PAGINATION_LIMIT = 25
    PAGINATION_OFFSET = 0
    PATH = 2
    QUERY_PARAMETERS = 4

    def _create_paginated_links(self, _args):
        """
        Method to create paginated links
        :param _args: Dictionary of query parameters that are passed in the http request.
        :return: Dictionary of paginated links containing the next and previous url
        """
        _args.update({KEY_LIMIT: _args.get(KEY_LIMIT, self.PAGINATION_LIMIT)})
        _offset = _args.pop(KEY_OFFSET, self.PAGINATION_OFFSET)
        _namespace = ''
        for _ns in self.api.namespaces:
            if _ns.path:
                _namespace = '{}{}/'.format(_namespace, _ns.path)
        return self._construct_urls(_namespace, _args, _offset)

    @staticmethod
    def _handle_infraction_types(_args):
        """
        Since the infractionTypes field is crated as a list, we need to iterate the list to create a URL comprised
        of one infractionType per entry in the list
        :param _args: dict of arguments
        :return: string of infractionType parameters
        """
        _infraction_type_string = ''
        if isinstance(_args, dict):
            _infraction_types = _args.pop(KEY_INFRACTION_TYPES, None)
            if _infraction_types:
                for _type in _infraction_types:
                    _infraction_type_string += '&{}={}'.format(KEY_INFRACTION_TYPES, _type)
        return _infraction_type_string

    def _construct_urls(self, _namespace, _args, _offset):
        """
        Method to create the URL with parameters which are common between previous and next links.  Then
        create next and prev links using the offsets pertaining to each.
        :param _namespace: String representing api namespace
        :param _args: Dictionary of query parameters that are passed in the http request.
        :param _offset: Index of the record from which the next batch of infractions is to be retrieved.
        :return: URL with the appropriate query parameters
        """
        _infraction_type_string = PaginationLinks._handle_infraction_types(_args)
        url_parts = list(urlparse(self.api.base_url))
        url_parts[self.PATH] = '{}{}'.format(_namespace, self.endpoint)
        _args.update({KEY_OFFSET: _offset + _args.get(KEY_LIMIT)})
        url_parts[self.QUERY_PARAMETERS] = urlencode(_args) + _infraction_type_string
        _next_url = urlunparse(url_parts)
        _args.update({KEY_OFFSET: _offset - _args.get(KEY_LIMIT)})
        if _args.get(KEY_OFFSET) < 0:
            _args.update({KEY_OFFSET: 0})
        url_parts[self.QUERY_PARAMETERS] = urlencode(_args) + _infraction_type_string
        _prev_url = urlunparse(url_parts)
        return {
            KEY_NEXT: '{}'.format(_next_url),
            KEY_PREV: '{}'.format(_prev_url)
        }


@api.route('/health', endpoint='health')
class Health(Resource):
    @api.response(200, 'OK')
    def get(self):
        """
        Health check endpoint
        """
        return 'OK', 200


@api.route('/infractions', endpoint='infractions')
class Infractions(PaginationLinks):
    _logger = logging.getLogger(__name__)

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

        if data.get(KEY_RECORD_TYPE) != infraction_record_type:
            message = 'Record type must be {}'.format(infraction_record_type)
            self._logger.error('{}: {}'.format(message, data))
            abort(400, message)

        try:
            infraction_id, duplicate = query_helper.insert_infraction(data)

            status = 200 if duplicate else 201
            return {'infractionId': str(infraction_id) if infraction_id else ''}, status
        except (KeyError, TypeError, ValueError) as e:
            self._logger.error('Validation error {}: {}'.format(data, e))
            abort(422, e)
        except RedLockError as e:
            self._logger.error('Error while acquiring the lock {}: {}'.format(data, e))
            abort(422, 'Error submitting request')
        except Exception as e:
            self._logger.error('Error submitting {}: {}'.format(data, e))
            abort(422, 'Error submitting request')


@api.route('/infraction_count', endpoint='infraction_count')
class InfractionCount(Resource):
    _logger = logging.getLogger(__name__)

    @api.expect(parser)
    @api.response(200, 'OK')
    @api.response(401, 'Unauthorized')
    @api.response(403, 'Forbidden')
    @api.response(422, 'Validation Error')
    @api.doc(security='apikey')
    @token_required
    def get(self):
        """
        Returns an integer of the count of infractions which match the supplied infraction data.
        """
        tmp_args = parser.parse_args()

        # Check the parsed args from tmp_args create a new dict that only includes the k:v pairs where value is NOT None
        args = {k: v for k, v in tmp_args.items() if v}

        infraction_count = 0
        try:
            if args:
                infraction_count = query_helper.count_infractions(args)
            else:
                raise Exception('No parameters provided in query')

        except Exception as e:
            self._logger.warning('Error fetching {}: {}'.format(args, e))
            abort(422, 'Error submitting request')

        return infraction_count, 200


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
        query = None
        try:
            query = query_helper.get_infraction_from_id(infractionId)

        except Exception as e:
            self._logger.warning('Error fetching {}: {}'.format(infractionId, e))
            abort(422, 'Error submitting request')

        if not query:
            abort(404, 'Infraction ID: {} not found'.format(infractionId))

        return query, 200


@api.route('/non-infraction', endpoint='non-infraction')
class NonInfractions(Resource):
    _logger = logging.getLogger(__name__)

    @api.expect(non_infraction_event)
    @api.marshal_with(non_infraction_result)
    @api.response(201, 'Created')
    @api.response(400, 'Bad Request')
    @api.response(401, 'Unauthorized')
    @api.response(403, 'Forbidden')
    @api.response(422, 'Validation Error')
    @api.doc(security='apikey')
    @token_required
    def post(self):
        """
        Returns the Event ID and 201 upon successful creation of Non-Infraction Event (Note, NCMEC Report)
        """
        data = request.json

        try:
            record_id = query_helper.insert_non_infraction(data)
            return {'recordId': str(record_id) if record_id else ''}, 201
        except (KeyError, TypeError, ValueError) as e:
            self._logger.error('Validation error {}: {}'.format(data, e))
            abort(422, e)
        except Exception as e:
            self._logger.error('Error submitting {}: {}'.format(data, e))
            abort(422, 'Error submitting request')


@api.route('/history', endpoint='history')
class History(PaginationLinks):
    _logger = logging.getLogger(__name__)

    @api.expect(parser)
    @api.marshal_with(infractions_response)
    @api.response(200, 'OK')
    @api.response(400, 'Bad Request')
    @api.response(401, 'Unauthorized')
    @api.response(403, 'Forbidden')
    @api.response(422, 'Validation Error')
    @api.doc(security='apikey')
    @token_required
    def get(self):
        """
        Returns Mimir history and the pagination information associated with the supplied request data.
        """
        tmp_args = parser.parse_args()

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
            response_dict[KEY_INFRACTIONS] = query_helper.get_history(args)
            response_dict[KEY_PAGINATION] = self._create_paginated_links(input_args)

        except Exception as e:
            self._logger.warning('Error fetching {}: {}'.format(args, e))
            abort(422, 'Error submitting request')

        if not response_dict.get(KEY_INFRACTIONS) or \
                len(response_dict.get(KEY_INFRACTIONS, [])) < input_args.get(KEY_LIMIT, self.PAGINATION_LIMIT):
            response_dict.get(KEY_PAGINATION, {}).update({KEY_NEXT: None})

        return response_dict
