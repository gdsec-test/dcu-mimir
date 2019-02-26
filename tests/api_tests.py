import service.rest
from settings import config_by_name
from mock import patch
from service.utils.query_helper import QueryHelper
from flask import url_for
from gd_auth.token import AuthToken
from flask_testing.utils import TestCase


class MockToken:
    subject = {'cn': 'dcu.zeus.int.test-godaddy.com'}
    payload = {'groups': ['test_group']}


class TestRest(TestCase):

    HEADERS = {'Content-Type': 'application/json', 'Authorization': 'fake_jwt'}

    def create_app(self):
        return service.rest.create_app(config_by_name['test']())

    def setup(self):
        self.client = self.app.test_client()

    '''Health Endpoint'''

    def test_live_health_endpoint(self):  
        response = self.client.get(url_for('health'), headers={'Content-Type': 'application/json'})
        self.assertEqual(response.status_code, 200)

    '''Get Infraction by Infraction ID Tests'''

    @patch.object(AuthToken, 'parse', return_value=MockToken)
    @patch.object(QueryHelper, 'get_infraction_from_id')
    def test_infraction_from_id(self, get_infraction_from_id, parse):
        get_infraction_from_id.return_value = {'infractionId': '1234', 'infractionType': 'SUSPENDED'}
        response = self.client.get(url_for('get_infraction_id', infractionId='1234'), headers=self.HEADERS)
        self.assertEqual(response.status_code, 200)

    @patch.object(AuthToken, 'parse', return_value=MockToken)
    @patch.object(QueryHelper, 'get_infraction_from_id')
    def test_no_infraction_from_id(self, get_infraction_from_id, parse):
        get_infraction_from_id.return_value = []
        response = self.client.get(url_for('get_infraction_id', infractionId='1234'), headers=self.HEADERS)
        self.assertEqual(response.status_code, 404)

    @patch.object(AuthToken, 'parse', return_value=MockToken)
    @patch.object(QueryHelper, 'get_infraction_from_id')
    def test_infraction_id_validation_error(self, get_infraction_from_id, parse):
        get_infraction_from_id.side_effect = TypeError()
        response = self.client.get(url_for('get_infraction_id', infractionId='1234'), headers=self.HEADERS)
        self.assertEqual(response.status_code, 422)

    '''Get Infractions Tests'''

    @patch.object(AuthToken, 'parse', return_value=MockToken)
    @patch.object(QueryHelper, 'get_infractions')
    def test_get_matching_infractions(self, get_infractions, parse):
        data = {'shopperId': '8675309'}
        get_infractions.return_value = [{'infractionId': '5c5cc2b85f627d8562e7f1f3', 'shopperId': '8675309',
                                         'ticketId': '1234', 'sourceDomainOrIp': 'abcs.com',
                                         'hostingGuid': 'abc123-def456-ghi789', 'infractionType': 'CUSTOMER_WARNING',
                                         'createdDate': '2019-02-07T23:43:52.471Z'}]
        response = self.client.get(url_for('get_infractions'), headers=self.HEADERS, query_string=data)
        self.assertEqual(response.status_code, 200)

    @patch.object(AuthToken, 'parse', return_value=MockToken)
    @patch.object(QueryHelper, 'get_infractions')
    def test_get_no_matching_infractions(self, get_infractions, parse):
        data = {'shopperId': '8675309'}
        get_infractions.return_value = []
        response = self.client.get(url_for('get_infractions'), headers=self.HEADERS, query_string=data)
        self.assertEqual(response.status_code, 404)

    @patch.object(AuthToken, 'parse', return_value=MockToken)
    @patch.object(QueryHelper, 'get_infractions')
    def test_get_no_matching_infractions(self, get_infractions, parse):
        data = {'infractionType': 'IT_BAD'}
        get_infractions.side_effect = TypeError()
        response = self.client.get(url_for('get_infractions'), headers=self.HEADERS, query_string=data)
        self.assertEqual(response.status_code, 422)
        