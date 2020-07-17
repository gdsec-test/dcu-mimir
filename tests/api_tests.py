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
    SHOPPER_ID1 = '8675309'
    SHOPPER_ID2 = '4388'
    SUSPENDED = 'SUSPENDED'
    CUSTOMER_WARNING = 'CUSTOMER_WARNING'
    TEST_DOMAIN = 'test-domain.com'
    GUID1 = 'abc123-def456-ghv115'
    PHISHING = 'PHISHING'
    CHILD_ABUSE = 'CHILD_ABUSE'
    HOSTED = 'HOSTED'
    REGISTERED = 'REGISTERED'

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
        get_infraction_from_id.return_value = {'infractionId': '12347', 'infractionType': self.SUSPENDED}
        response = self.client.get(url_for('get_infraction_id', infractionId='12347'), headers=self.HEADERS)
        self.assertEqual(response.status_code, 200)

    @patch.object(AuthToken, 'payload', return_value=MockJomaxToken.payload)
    @patch.object(AuthToken, 'parse', return_value=MockJomaxToken)
    @patch.object(QueryHelper, 'get_infraction_from_id')
    def test_no_infraction_from_id(self, get_infraction_from_id, parse, payload):
        get_infraction_from_id.return_value = []
        response = self.client.get(url_for('get_infraction_id', infractionId='12345'), headers=self.HEADERS)
        self.assertEqual(response.status_code, 404)

    @patch.object(AuthToken, 'payload', return_value=MockJomaxToken.payload)
    @patch.object(AuthToken, 'parse', return_value=MockJomaxToken)
    @patch.object(QueryHelper, 'get_infraction_from_id')
    def test_infraction_id_validation_error(self, get_infraction_from_id, parse, payload):
        get_infraction_from_id.side_effect = TypeError()
        response = self.client.get(url_for('get_infraction_id', infractionId='12346'), headers=self.HEADERS)
        self.assertEqual(response.status_code, 422)

    '''Post New Infraction'''

    @patch.object(AuthToken, 'payload', return_value=MockJomaxToken.payload)
    @patch.object(AuthToken, 'parse', return_value=MockJomaxToken)
    @patch.object(QueryHelper, 'insert_infraction')
    def test_insert_new_hosted_infraction(self, insert_infraction, parse, payload):
        insert_infraction.return_value = '12345', False
        data = {'shopperId': self.SHOPPER_ID2, 'ticketId': '133F', 'sourceDomainOrIp': self.TEST_DOMAIN,
                'hostedStatus': self.HOSTED, 'hostingGuid': self.GUID1, 'infractionType': self.CUSTOMER_WARNING,
                'abuseType': self.PHISHING}
        response = self.client.post(url_for('infractions'), data=json.dumps(data), headers=self.HEADERS)
        self.assertEqual(response.status_code, 201)

    @patch.object(AuthToken, 'payload', return_value=MockJomaxToken.payload)
    @patch.object(AuthToken, 'parse', return_value=MockJomaxToken)
    @patch.object(QueryHelper, 'insert_infraction')
    def test_insert_new_reg_infraction(self, insert_infraction, parse, payload):
        insert_infraction.return_value = '12345', False
        data = {'shopperId': self.SHOPPER_ID2, 'ticketId': '128F', 'sourceDomainOrIp': self.TEST_DOMAIN,
                'hostedStatus': self.REGISTERED, 'domainId': '1234', 'infractionType': self.CUSTOMER_WARNING,
                'abuseType': self.PHISHING}
        response = self.client.post(url_for('infractions'), data=json.dumps(data), headers=self.HEADERS)
        self.assertEqual(response.status_code, 201)

    @patch.object(AuthToken, 'payload', return_value=MockJomaxToken.payload)
    @patch.object(AuthToken, 'parse', return_value=MockJomaxToken)
    @patch.object(QueryHelper, 'insert_infraction')
    def test_insert_dupe_infraction(self, insert_infraction, parse, payload):
        insert_infraction.return_value = '12345', True
        data = {'shopperId': self.SHOPPER_ID2, 'ticketId': '129F', 'sourceDomainOrIp': self.TEST_DOMAIN,
                'hostedStatus': self.HOSTED, 'hostingGuid': self.GUID1, 'infractionType': self.CUSTOMER_WARNING,
                'abuseType': self.PHISHING}
        response = self.client.post(url_for('infractions'), data=json.dumps(data), headers=self.HEADERS)
        self.assertEqual(response.status_code, 200)

    @patch.object(AuthToken, 'payload', return_value=MockJomaxToken.payload)
    @patch.object(AuthToken, 'parse', return_value=MockJomaxToken)
    @patch.object(QueryHelper, 'insert_infraction')
    def test_insert_infraction_validation_error(self, insert_infraction, parse, payload):
        insert_infraction.side_effect = TypeError()
        data = {'shopperId': self.SHOPPER_ID2, 'ticketId': '130F', 'sourceDomainOrIp': self.TEST_DOMAIN,
                'hostedStatus': self.HOSTED, 'hostingGuid': self.GUID1, 'infractionType': 'Oops'}
        response = self.client.post(url_for('infractions'), data=json.dumps(data), headers=self.HEADERS)
        self.assertEqual(response.status_code, 400)

    @patch.object(AuthToken, 'payload', return_value=MockJomaxToken.payload)
    @patch.object(AuthToken, 'parse', return_value=MockJomaxToken)
    @patch.object(QueryHelper, 'insert_infraction')
    def test_insert_infraction_when_required_param_missing(self, insert_infraction, parse, payload):
        insert_infraction.side_effect = TypeError()
        data = {'shopperId': self.SHOPPER_ID2, 'ticketId': '131F', 'sourceDomainOrIp': self.TEST_DOMAIN,
                'hostedStatus': self.HOSTED, 'hostingGuid': self.GUID1}
        response = self.client.post(url_for('infractions'), data=json.dumps(data), headers=self.HEADERS)
        self.assertEqual(response.status_code, 400)

    @patch.object(AuthToken, 'payload', return_value=MockJomaxToken.payload)
    @patch.object(AuthToken, 'parse', return_value=MockJomaxToken)
    @patch.object(QueryHelper, 'insert_infraction')
    def test_insert_infraction_with_note(self, insert_infraction, parse, payload):
        insert_infraction.return_value = '12346', False
        data = {'shopperId': self.SHOPPER_ID2, 'ticketId': '132F', 'sourceDomainOrIp': self.TEST_DOMAIN,
                'hostedStatus': self.HOSTED, 'hostingGuid': self.GUID1, 'infractionType': self.CUSTOMER_WARNING,
                'note': 'manual note', 'abuseType': self.PHISHING}
        response = self.client.post(url_for('infractions'), data=json.dumps(data), headers=self.HEADERS)
        self.assertEqual(response.status_code, 201)

    @patch.object(AuthToken, 'payload', return_value=MockJomaxToken.payload)
    @patch.object(AuthToken, 'parse', return_value=MockJomaxToken)
    @patch.object(QueryHelper, 'insert_infraction')
    def test_insert_infraction_with_note_no_ticket_id(self, insert_infraction, parse, payload):
        insert_infraction.return_value = '12346', False
        data = {'shopperId': self.SHOPPER_ID2, 'sourceDomainOrIp': self.TEST_DOMAIN, 'hostedStatus': self.HOSTED,
                'hostingGuid': self.GUID1, 'infractionType': self.CUSTOMER_WARNING, 'note': 'manual note',
                'abuseType': self.PHISHING}
        response = self.client.post(url_for('infractions'), data=json.dumps(data), headers=self.HEADERS)
        self.assertEqual(response.status_code, 201)

    @patch.object(AuthToken, 'payload', return_value=MockJomaxToken.payload)
    @patch.object(AuthToken, 'parse', return_value=MockJomaxToken)
    @patch.object(QueryHelper, 'insert_infraction')
    def test_insert_new_csam_infraction(self, insert_infraction, parse, payload):
        insert_infraction.return_value = '12345', False
        data = {'shopperId': self.SHOPPER_ID2, 'ticketId': '128F', 'sourceDomainOrIp': 'test-csam-domain.com',
                'hostedStatus': self.HOSTED, 'hostingGuid': self.GUID1, 'infractionType': 'NCMEC_REPORT_SUBMITTED',
                'abuseType': self.CHILD_ABUSE}
        response = self.client.post(url_for('infractions'), data=json.dumps(data), headers=self.HEADERS)
        self.assertEqual(response.status_code, 201)

    '''Get Infractions Tests'''

    @patch.object(AuthToken, 'payload', return_value=MockJomaxToken.payload)
    @patch.object(AuthToken, 'parse', return_value=MockJomaxToken)
    @patch.object(QueryHelper, 'get_infractions')
    def test_get_matching_hosted_infractions(self, get_infractions, parse, payload):
        data = {'shopperId': self.SHOPPER_ID1}
        get_infractions.return_value = [{'infractionId': '5c5cc2b85f627d8562e7f1f3', 'shopperId': self.SHOPPER_ID1,
                                         'ticketId': '1234', 'sourceDomainOrIp': 'abcs.com',
                                         'hostingGuid': 'abc123-def456-ghi789', 'infractionType': self.CUSTOMER_WARNING,
                                         'createdDate': '2019-02-07T23:43:52.471Z'}]
        response = self.client.get(url_for('infractions'), headers=self.HEADERS, query_string=data)
        self.assertEqual(response.status_code, 200)

    @patch.object(AuthToken, 'payload', return_value=MockJomaxToken.payload)
    @patch.object(AuthToken, 'parse', return_value=MockJomaxToken)
    @patch.object(QueryHelper, 'get_infractions')
    def test_get_infractions_with_infraction_type(self, get_infractions, parse, payload):
        data = {'shopperId': self.SHOPPER_ID1, 'infractionTypes': [self.CUSTOMER_WARNING, self.SUSPENDED]}
        get_infractions.return_value = [{'infractionId': '5c5cc2b85f627d8562e7f1f3', 'shopperId': self.SHOPPER_ID1,
                                         'ticketId': '1234', 'sourceDomainOrIp': 'abcs.com',
                                         'hostingGuid': 'abc123-def456-ghi789', 'infractionType': self.CUSTOMER_WARNING,
                                         'createdDate': '2019-02-07T23:43:52.471Z'},
                                        {'infractionId': '5c5cc2b85f627d8562e7faaa', 'shopperId': self.SHOPPER_ID1,
                                         'ticketId': '1235', 'sourceDomainOrIp': 'abcs12.com',
                                         'hostingGuid': 'abc123-def456-ghi789', 'infractionType': self.SUSPENDED,
                                         'createdDate': '2019-03-07T23:43:52.471Z'}]
        response = self.client.get(url_for('infractions'), headers=self.HEADERS, query_string=data)
        self.assertEqual(response.status_code, 200)

    @patch.object(AuthToken, 'payload', return_value=MockJomaxToken.payload)
    @patch.object(AuthToken, 'parse', return_value=MockJomaxToken)
    @patch.object(QueryHelper, 'get_infractions')
    def test_get_matching_reg_infractions(self, get_infractions, parse, payload):
        data = {'shopperId': self.SHOPPER_ID1, 'hostedStatus': self.REGISTERED}
        get_infractions.return_value = [{'infractionId': '5c5cc2b85f627d8562e7f1f3', 'shopperId': self.SHOPPER_ID1,
                                         'ticketId': '1234', 'sourceDomainOrIp': 'abcs.com',
                                         'domainId': '12345', 'infractionType': 'CUSTOMER_WARNING',
                                         'createdDate': '2019-02-07T23:43:52.471Z'}]
        response = self.client.get(url_for('infractions'), headers=self.HEADERS, query_string=data)
        self.assertEqual(response.status_code, 200)

    @patch.object(AuthToken, 'payload', return_value=MockJomaxToken.payload)
    @patch.object(AuthToken, 'parse', return_value=MockJomaxToken)
    @patch.object(QueryHelper, 'get_infractions')
    def test_get_no_matching_infractions(self, get_infractions, parse, payload):
        data = {'shopperId': self.SHOPPER_ID1}
        get_infractions.return_value = []
        response = self.client.get(url_for('infractions'), headers=self.HEADERS, query_string=data)
        self.assertIsNone(response.json.get('pagination', {}).get('next'))

    @patch.object(AuthToken, 'payload', return_value=MockJomaxToken.payload)
    @patch.object(AuthToken, 'parse', return_value=MockJomaxToken)
    @patch.object(QueryHelper, 'get_infractions')
    def test_get_no_matching_infractions_error(self, get_infractions, parse, payload):
        data = {'infractionTypes': 'IT_BAD'}
        get_infractions.side_effect = TypeError()
        response = self.client.get(url_for('infractions'), headers=self.HEADERS, query_string=data)
        self.assertEqual(response.status_code, 422)

    @patch.object(AuthToken, 'payload', return_value=MockJomaxToken.payload)
    @patch.object(AuthToken, 'parse', return_value=MockJomaxToken)
    @patch.object(QueryHelper, 'get_infractions')
    def test_get_infraction_type_error(self, get_infractions, parse, payload):
        data = {'infractionTypes': 'INTENTIONALLY_MALICIOUS', 'shopperId': self.SHOPPER_ID1}
        get_infractions.side_effect = TypeError()
        response = self.client.get(url_for('infractions'), headers=self.HEADERS, query_string=data)
        self.assertEqual(response.status_code, 422)

    @patch.object(AuthToken, 'payload', return_value=MockJomaxToken.payload)
    @patch.object(AuthToken, 'parse', return_value=MockJomaxToken)
    @patch.object(QueryHelper, 'get_infractions')
    def test_get_none_infraction_type(self, get_infractions, parse, payload):
        data = {'infractionTypes': None}
        get_infractions.side_effect = TypeError()
        response = self.client.get(url_for('infractions'), headers=self.HEADERS, query_string=data)
        self.assertEqual(response.status_code, 422)

    @patch.object(AuthToken, 'payload', return_value=MockJomaxToken.payload)
    @patch.object(AuthToken, 'parse', return_value=MockJomaxToken)
    @patch.object(QueryHelper, 'get_infractions')
    def test_get_infraction_count_less_than_limit(self, get_infractions, parse, payload):
        data = {'shopperId': self.SHOPPER_ID1}
        response = self.client.get(url_for('infractions'), headers=self.HEADERS, query_string=data)
        self.assertIsNone(response.json.get('pagination', {}).get('next'))

    @patch.object(AuthToken, 'payload', return_value=MockJomaxToken.payload)
    @patch.object(AuthToken, 'parse', return_value=MockJomaxToken)
    @patch.object(QueryHelper, 'get_infractions')
    def test_pagination_invalid_prev_url(self, get_infractions, parse, payload):
        data = {'shopperId': self.SHOPPER_ID1, 'offset': 0, 'limit': 2}
        get_infractions.return_value = [
            {'infractionId': '1', 'shopperId': self.SHOPPER_ID1, 'ticketId': '1234'},
            {'infractionId': '2', 'shopperId': self.SHOPPER_ID1, 'ticketId': '1235'},
            {'infractionId': '3', 'shopperId': self.SHOPPER_ID1, 'ticketId': '1236'},
            {'infractionId': '4', 'shopperId': self.SHOPPER_ID1, 'ticketId': '1237'}
        ]
        response = self.client.get(url_for('infractions'), headers=self.HEADERS, query_string=data)
        next_url = response.json.get('pagination', {}).get('next')
        prev_url = response.json.get('pagination', {}).get('prev')
        self.assertEqual(next_url, 'http://localhost/infractions?shopperId={}&limit=2&offset=2'.format(self.SHOPPER_ID1))
        self.assertEqual(prev_url, 'http://localhost/infractions?shopperId={}&limit=2&offset=0'.format(self.SHOPPER_ID1))

    @patch.object(AuthToken, 'payload', return_value=MockJomaxToken.payload)
    @patch.object(AuthToken, 'parse', return_value=MockJomaxToken)
    @patch.object(QueryHelper, 'get_infractions')
    def test_pagination_valid_prev_url(self, get_infractions, parse, payload):
        data = {'shopperId': self.SHOPPER_ID1, 'offset': 3, 'limit': 2}
        get_infractions.return_value = [
            {'infractionId': '1', 'shopperId': self.SHOPPER_ID1, 'ticketId': '1334'},
            {'infractionId': '2', 'shopperId': self.SHOPPER_ID1, 'ticketId': '1335'},
            {'infractionId': '3', 'shopperId': self.SHOPPER_ID1, 'ticketId': '1336'},
            {'infractionId': '4', 'shopperId': self.SHOPPER_ID1, 'ticketId': '1337'}
        ]
        response = self.client.get(url_for('infractions'), headers=self.HEADERS, query_string=data)
        next_url = response.json.get('pagination', {}).get('next')
        prev_url = response.json.get('pagination', {}).get('prev')
        self.assertEqual(next_url, 'http://localhost/infractions?shopperId={}&limit=2&offset=5'.format(self.SHOPPER_ID1))
        self.assertEqual(prev_url, 'http://localhost/infractions?shopperId={}&limit=2&offset=1'.format(self.SHOPPER_ID1))
