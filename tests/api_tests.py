import json

from flask import url_for
from flask_testing.utils import TestCase
from gd_auth.token import AuthToken
from mock import patch

import service.rest
from service.utils.query_helper import QueryHelper
from settings import config_by_name


class MockCertToken:
    subject = {
        'o': '',
        'ou': 'Domain Control Validated',
        'cn': 'dcu.zeus.int.test-godaddy.com'
    }

    payload = {
        'jti': 'CL4Q59OPLh1GcpGikV/jkQ==',
        'iat': 1557939758,
        'auth': 'basic',
        'typ': 'cert',
        'factors': {
            'p_cert': 1557939758
        },
        'sbj': subject
    }


class MockJomaxToken:
    payload = {
        'auth': 'basic',
        'ftc': 1,
        'iat': 1557932510,
        'typ': 'jomax',
        'vat': 1557932510,
        'accountName': 'test_user',
        'groups': ['DCU-Phishstory']
    }


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

    @patch.object(AuthToken, 'payload', return_value=MockCertToken.payload)
    @patch.object(AuthToken, 'parse', return_value=MockCertToken)
    @patch.object(QueryHelper, 'get_infraction_from_id')
    def test_infraction_from_id(self, get_infraction_from_id, parse, payload):
        get_infraction_from_id.return_value = {'infractionId': '1234', 'infractionType': 'SUSPENDED'}
        response = self.client.get(url_for('get_infraction_id', infractionId='1234'), headers=self.HEADERS)
        self.assertEqual(response.status_code, 200)

    @patch.object(AuthToken, 'payload', return_value=MockJomaxToken.payload)
    @patch.object(AuthToken, 'parse', return_value=MockJomaxToken)
    @patch.object(QueryHelper, 'get_infraction_from_id')
    def test_no_infraction_from_id(self, get_infraction_from_id, parse, payload):
        get_infraction_from_id.return_value = []
        response = self.client.get(url_for('get_infraction_id', infractionId='1234'), headers=self.HEADERS)
        self.assertEqual(response.status_code, 404)

    @patch.object(AuthToken, 'payload', return_value=MockJomaxToken.payload)
    @patch.object(AuthToken, 'parse', return_value=MockJomaxToken)
    @patch.object(QueryHelper, 'get_infraction_from_id')
    def test_infraction_id_validation_error(self, get_infraction_from_id, parse, payload):
        get_infraction_from_id.side_effect = TypeError()
        response = self.client.get(url_for('get_infraction_id', infractionId='1234'), headers=self.HEADERS)
        self.assertEqual(response.status_code, 422)

    '''Post New Infraction'''

    @patch.object(AuthToken, 'payload', return_value=MockJomaxToken.payload)
    @patch.object(AuthToken, 'parse', return_value=MockJomaxToken)
    @patch.object(QueryHelper, 'insert_infraction')
    def test_insert_new_infraction(self, insert_infraction, parse, payload):
        insert_infraction.return_value = '12345', False
        data = {'shopperId': '4388', 'ticketId': '128F', 'sourceDomainOrIp': 'test-domain.com',
                'hostingGuid': 'abc123-def456-ghv115', 'infractionType': 'CUSTOMER_WARNING'}
        response = self.client.post(url_for('infractions'), data=json.dumps(data), headers=self.HEADERS)
        self.assertEqual(response.status_code, 201)

    @patch.object(AuthToken, 'payload', return_value=MockJomaxToken.payload)
    @patch.object(AuthToken, 'parse', return_value=MockJomaxToken)
    @patch.object(QueryHelper, 'insert_infraction')
    def test_insert_dupe_infraction(self, insert_infraction, parse, payload):
        insert_infraction.return_value = '12345', True
        data = {'shopperId': '4388', 'ticketId': '128F', 'sourceDomainOrIp': 'test-domain.com',
                'hostingGuid': 'abc123-def456-ghv115', 'infractionType': 'CUSTOMER_WARNING'}
        response = self.client.post(url_for('infractions'), data=json.dumps(data), headers=self.HEADERS)
        self.assertEqual(response.status_code, 200)

    @patch.object(AuthToken, 'payload', return_value=MockJomaxToken.payload)
    @patch.object(AuthToken, 'parse', return_value=MockJomaxToken)
    @patch.object(QueryHelper, 'insert_infraction')
    def test_insert_infraction_validation_error(self, insert_infraction, parse, payload):
        insert_infraction.side_effect = TypeError()
        data = {'shopperId': '4388', 'ticketId': '128F', 'sourceDomainOrIp': 'test-domain.com',
                'hostingGuid': 'abc123-def456-ghv115', 'infractionType': 'Oops'}
        response = self.client.post(url_for('infractions'), data=json.dumps(data), headers=self.HEADERS)
        self.assertEqual(response.status_code, 400)

    @patch.object(AuthToken, 'payload', return_value=MockJomaxToken.payload)
    @patch.object(AuthToken, 'parse', return_value=MockJomaxToken)
    @patch.object(QueryHelper, 'insert_infraction')
    def test_insert_infraction_when_required_param_missing(self, insert_infraction, parse, payload):
        insert_infraction.side_effect = TypeError()
        data = {'shopperId': '4388', 'ticketId': '128F', 'sourceDomainOrIp': 'test-domain.com',
                'hostingGuid': 'abc123-def456-ghv115'}
        response = self.client.post(url_for('infractions'), data=json.dumps(data), headers=self.HEADERS)
        self.assertEqual(response.status_code, 400)

    @patch.object(AuthToken, 'payload', return_value=MockJomaxToken.payload)
    @patch.object(AuthToken, 'parse', return_value=MockJomaxToken)
    @patch.object(QueryHelper, 'insert_infraction')
    def test_insert_infraction_with_note(self, insert_infraction, parse, payload):
        insert_infraction.return_value = '12346', False
        data = {'shopperId': '4388', 'ticketId': '128F', 'sourceDomainOrIp': 'test-domain.com',
                'hostingGuid': 'abc123-def456-ghv115', 'infractionType': 'CUSTOMER_WARNING', 'note': 'manual note'}
        response = self.client.post(url_for('infractions'), data=json.dumps(data), headers=self.HEADERS)
        self.assertEqual(response.status_code, 201)

    @patch.object(AuthToken, 'payload', return_value=MockJomaxToken.payload)
    @patch.object(AuthToken, 'parse', return_value=MockJomaxToken)
    @patch.object(QueryHelper, 'insert_infraction')
    def test_insert_new_csam_infraction(self, insert_infraction, parse, payload):
        insert_infraction.return_value = '12345', False
        data = {'shopperId': '4388', 'ticketId': '128F', 'sourceDomainOrIp': 'test-csam-domain.com',
                'hostingGuid': 'abc123-def456-ghv115', 'infractionType': 'NCMEC_REPORT_SUBMITTED'}
        response = self.client.post(url_for('infractions'), data=json.dumps(data), headers=self.HEADERS)
        self.assertEqual(response.status_code, 201)

    '''Get Infractions Tests'''

    @patch.object(AuthToken, 'payload', return_value=MockJomaxToken.payload)
    @patch.object(AuthToken, 'parse', return_value=MockJomaxToken)
    @patch.object(QueryHelper, 'get_infractions')
    def test_get_matching_infractions(self, get_infractions, parse, payload):
        data = {'shopperId': '8675309'}
        get_infractions.return_value = [{'infractionId': '5c5cc2b85f627d8562e7f1f3', 'shopperId': '8675309',
                                         'ticketId': '1234', 'sourceDomainOrIp': 'abcs.com',
                                         'hostingGuid': 'abc123-def456-ghi789', 'infractionType': 'CUSTOMER_WARNING',
                                         'createdDate': '2019-02-07T23:43:52.471Z'}]
        response = self.client.get(url_for('infractions'), headers=self.HEADERS, query_string=data)
        self.assertEqual(response.status_code, 200)

    @patch.object(AuthToken, 'payload', return_value=MockJomaxToken.payload)
    @patch.object(AuthToken, 'parse', return_value=MockJomaxToken)
    @patch.object(QueryHelper, 'get_infractions')
    def test_get_no_matching_infractions(self, get_infractions, parse, payload):
        data = {'shopperId': '8675309'}
        get_infractions.return_value = []
        response = self.client.get(url_for('infractions'), headers=self.HEADERS, query_string=data)
        self.assertIsNone(response.json.get('pagination', {}).get('next'))

    @patch.object(AuthToken, 'payload', return_value=MockJomaxToken.payload)
    @patch.object(AuthToken, 'parse', return_value=MockJomaxToken)
    @patch.object(QueryHelper, 'get_infractions')
    def test_get_no_matching_infractions_error(self, get_infractions, parse, payload):
        data = {'infractionType': 'IT_BAD'}
        get_infractions.side_effect = TypeError()
        response = self.client.get(url_for('infractions'), headers=self.HEADERS, query_string=data)
        self.assertEqual(response.status_code, 422)

    @patch.object(AuthToken, 'payload', return_value=MockJomaxToken.payload)
    @patch.object(AuthToken, 'parse', return_value=MockJomaxToken)
    @patch.object(QueryHelper, 'get_infractions')
    def test_get_infraction_count_less_than_limit(self, get_infractions, parse, payload):
        data = {'shopperId': '8675309'}
        response = self.client.get(url_for('infractions'), headers=self.HEADERS, query_string=data)
        self.assertIsNone(response.json.get('pagination', {}).get('next'))

    @patch.object(AuthToken, 'payload', return_value=MockJomaxToken.payload)
    @patch.object(AuthToken, 'parse', return_value=MockJomaxToken)
    @patch.object(QueryHelper, 'get_infractions')
    def test_pagination_invalid_prev_url(self, get_infractions, parse, payload):
        data = {'shopperId': '8675309', 'offset': 0, 'limit': 2}
        get_infractions.return_value = [
            {'infractionId': '1', 'shopperId': '8675309', 'ticketId': '1234'},
            {'infractionId': '2', 'shopperId': '8675309', 'ticketId': '1235'},
            {'infractionId': '3', 'shopperId': '8675309', 'ticketId': '1236'},
            {'infractionId': '4', 'shopperId': '8675309', 'ticketId': '1237'}
        ]
        response = self.client.get(url_for('infractions'), headers=self.HEADERS, query_string=data)
        next_url = response.json.get('pagination', {}).get('next')
        prev_url = response.json.get('pagination', {}).get('prev')
        self.assertEqual(next_url, 'http://localhost/infractions?shopperId=8675309&limit=2&offset=2')
        self.assertEqual(prev_url, 'http://localhost/infractions?shopperId=8675309&limit=2&offset=0')

    @patch.object(AuthToken, 'payload', return_value=MockJomaxToken.payload)
    @patch.object(AuthToken, 'parse', return_value=MockJomaxToken)
    @patch.object(QueryHelper, 'get_infractions')
    def test_pagination_valid_prev_url(self, get_infractions, parse, payload):
        data = {'shopperId': '8675309', 'offset': 3, 'limit': 2}
        get_infractions.return_value = [
            {'infractionId': '1', 'shopperId': '8675309', 'ticketId': '1234'},
            {'infractionId': '2', 'shopperId': '8675309', 'ticketId': '1235'},
            {'infractionId': '3', 'shopperId': '8675309', 'ticketId': '1236'},
            {'infractionId': '4', 'shopperId': '8675309', 'ticketId': '1237'}
        ]
        response = self.client.get(url_for('infractions'), headers=self.HEADERS, query_string=data)
        next_url = response.json.get('pagination', {}).get('next')
        prev_url = response.json.get('pagination', {}).get('prev')
        self.assertEqual(next_url, 'http://localhost/infractions?shopperId=8675309&limit=2&offset=5')
        self.assertEqual(prev_url, 'http://localhost/infractions?shopperId=8675309&limit=2&offset=1')
