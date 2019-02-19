from flask import url_for
from flask_testing.utils import TestCase
from mock import patch

import service.rest
from service.utils.query_helper import QueryHelper
from settings import config_by_name


class TestRest(TestCase):

    HEADERS = {'Content-Type': 'application/json'}

    def create_app(self):
        return service.rest.create_app(config_by_name['test']())

    def setup(self):
        self.client = self.app.test_client()

    '''Health Endpoint'''

    def test_live_health_endpoint(self):
        response = self.client.get(url_for('health'), headers=self.HEADERS)
        self.assertEqual(response.status_code, 200)

    '''Get Infraction by Infraction ID Tests'''

    @patch.object(QueryHelper, 'get_infraction_from_id')
    def test_infraction_from_id(self, get_infraction_from_id):
        get_infraction_from_id.return_value = {'infractionId': '1234', 'infractionType': 'SUSPENDED'}
        response = self.client.get(url_for('get_infraction_id', infractionId='1234'), headers=self.HEADERS)
        self.assertEqual(response.status_code, 200)

    @patch.object(QueryHelper, 'get_infraction_from_id')
    def test_no_infraction_from_id(self, get_infraction_from_id):
        get_infraction_from_id.return_value = []
        response = self.client.get(url_for('get_infraction_id', infractionId='1234'), headers=self.HEADERS)
        self.assertEqual(response.status_code, 404)

    @patch.object(QueryHelper, 'get_infraction_from_id')
    def test_infraction_id_validation_error(self, get_infraction_from_id):
        get_infraction_from_id.side_effect = TypeError()
        response = self.client.get(url_for('get_infraction_id', infractionId='1234'), headers=self.HEADERS)
        self.assertEqual(response.status_code, 422)
