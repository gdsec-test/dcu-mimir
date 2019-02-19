import os
import logging

from flask_restplus import Namespace, Resource, abort
from settings import config_by_name
from service.utils.query_helper import QueryHelper

settings = config_by_name[os.getenv('sysenv', 'dev')]()

query_helper = QueryHelper(settings)

api = Namespace('v1', title='DCU Repeat Infractions API', description='')


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
