import json

from dcdatabase.mimir.mongo import MimirMongo
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
        'cn': 'zeus.client.cset.int.test-gdcorp.tools'
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

    def is_expired(self, _):
        return False


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

    def is_expired(self, _):
        return False


@patch.object(MimirMongo, '__init__', return_value=None)
class TestRest(TestCase):
    CHILD_ABUSE = 'CHILD_ABUSE'
    CUSTOMER_WARNING = 'CUSTOMER_WARNING'
    GET_HISTORY_URL = 'http://localhost/v1/history'
    GUID1 = 'abc123-def456-ghv115'
    HEADERS = {'Content-Type': 'application/json', 'Authorization': 'fake_jwt'}
    HOSTED = 'HOSTED'
    KEY_INFRACTION_ID = 'infractionId'
    KEY_NEXT = 'next'
    KEY_PAGINATION = 'pagination'
    KEY_PREV = 'prev'
    KEY_SHOPPER_ID = 'shopperId'
    KEY_TICKET_ID = 'ticketId'
    PHISHING = 'PHISHING'
    REGISTERED = 'REGISTERED'
    SHOPPER_ID1 = '8675309'
    SHOPPER_ID2 = '4388'
    SUSPENDED = 'SUSPENDED'
    TEST_DOMAIN = 'test-domain.com'

    def create_app(self):
        return service.rest.create_app(config_by_name['unit-test']())

    def setup(self):
        self.client = self.app.test_client()

    '''Health Endpoint'''

    def test_live_health_endpoint(self, mockMimirMongoCon):
        response = self.client.get(url_for('health'), headers={'Content-Type': 'application/json'})
        self.assertEqual(response.status_code, 200)

    '''Get Infraction by Infraction ID Tests'''

    @patch.object(AuthToken, 'payload', return_value=MockCertToken.payload)
    @patch.object(AuthToken, 'parse', return_value=MockCertToken())
    @patch.object(QueryHelper, 'get_infraction_from_id')
    def test_infraction_from_id(self, get_infraction_from_id, parse, payload, mockMimirMongoCon):
        get_infraction_from_id.return_value = {self.KEY_INFRACTION_ID: '12347', 'infractionType': self.SUSPENDED}
        response = self.client.get(url_for('get_infraction_id', infractionId='12347'), headers=self.HEADERS)
        self.assertEqual(response.status_code, 200)
        get_infraction_from_id.assert_called()
        parse.assert_called()
        payload.assert_called()

    @patch.object(AuthToken, 'payload', return_value=MockJomaxToken.payload)
    @patch.object(AuthToken, 'parse', return_value=MockJomaxToken())
    @patch.object(service.rest.api, 'validate_group', return_value=True)
    @patch.object(QueryHelper, 'get_infraction_from_id')
    def test_no_infraction_from_id(self, get_infraction_from_id, validate_group, parse, payload, mockMimirMongoCon):
        get_infraction_from_id.return_value = []
        response = self.client.get(url_for('get_infraction_id', infractionId='12345'), headers=self.HEADERS)
        self.assertEqual(response.status_code, 404)
        get_infraction_from_id.assert_called()
        parse.assert_called()
        payload.assert_called()

    @patch.object(AuthToken, 'payload', return_value=MockJomaxToken.payload)
    @patch.object(AuthToken, 'parse', return_value=MockJomaxToken())
    @patch.object(service.rest.api, 'validate_group', return_value=True)
    @patch.object(QueryHelper, 'get_infraction_from_id')
    def test_infraction_id_validation_error(self, get_infraction_from_id, validate_group, parse, payload, mockMimirMongoCon):
        get_infraction_from_id.side_effect = TypeError()
        response = self.client.get(url_for('get_infraction_id', infractionId='12346'), headers=self.HEADERS)
        self.assertEqual(response.status_code, 422)
        get_infraction_from_id.assert_called()
        parse.assert_called()
        payload.assert_called()

    '''Post New Infraction'''

    @patch.object(AuthToken, 'payload', return_value=MockJomaxToken.payload)
    @patch.object(AuthToken, 'parse', return_value=MockJomaxToken())
    @patch.object(service.rest.api, 'validate_group', return_value=True)
    @patch.object(QueryHelper, 'insert_infraction')
    def test_insert_new_hosted_infraction(self, insert_infraction, validate_group, parse, payload, mockMimirMongoCon):
        insert_infraction.return_value = '12345', False
        data = {self.KEY_SHOPPER_ID: self.SHOPPER_ID2, self.KEY_TICKET_ID: '133F', 'sourceDomainOrIp': self.TEST_DOMAIN,
                'hostedStatus': self.HOSTED, 'hostingGuid': self.GUID1, 'infractionType': self.CUSTOMER_WARNING,
                'abuseType': self.PHISHING, 'recordType': 'INFRACTION'}
        response = self.client.post(url_for('infractions'), data=json.dumps(data), headers=self.HEADERS)
        self.assertEqual(response.status_code, 201)
        insert_infraction.assert_called()
        parse.assert_called()
        payload.assert_called()

    @patch.object(AuthToken, 'payload', return_value=MockJomaxToken.payload)
    @patch.object(AuthToken, 'parse', return_value=MockJomaxToken())
    @patch.object(service.rest.api, 'validate_group', return_value=True)
    @patch.object(QueryHelper, 'insert_infraction')
    def test_insert_new_reg_infraction(self, insert_infraction, validate_group, parse, payload, mockMimirMongoCon):
        insert_infraction.return_value = '12345', False
        data = {self.KEY_SHOPPER_ID: self.SHOPPER_ID2, self.KEY_TICKET_ID: '128F', 'sourceDomainOrIp': self.TEST_DOMAIN,
                'hostedStatus': self.REGISTERED, 'domainId': '1234', 'infractionType': self.CUSTOMER_WARNING,
                'abuseType': self.PHISHING, 'recordType': 'INFRACTION'}
        response = self.client.post(url_for('infractions'), data=json.dumps(data), headers=self.HEADERS)
        self.assertEqual(response.status_code, 201)
        insert_infraction.assert_called()
        parse.assert_called()
        payload.assert_called()

    @patch.object(AuthToken, 'payload', return_value=MockJomaxToken.payload)
    @patch.object(AuthToken, 'parse', return_value=MockJomaxToken())
    @patch.object(service.rest.api, 'validate_group', return_value=True)
    @patch.object(QueryHelper, 'insert_infraction')
    def test_insert_dupe_infraction(self, insert_infraction, validate_group, parse, payload, mockMimirMongoCon):
        insert_infraction.return_value = '12345', True
        data = {self.KEY_SHOPPER_ID: self.SHOPPER_ID2, self.KEY_TICKET_ID: '129F', 'sourceDomainOrIp': self.TEST_DOMAIN,
                'hostedStatus': self.HOSTED, 'hostingGuid': self.GUID1, 'infractionType': self.CUSTOMER_WARNING,
                'abuseType': self.PHISHING, 'recordType': 'INFRACTION'}
        response = self.client.post(url_for('infractions'), data=json.dumps(data), headers=self.HEADERS)
        self.assertEqual(response.status_code, 200)
        insert_infraction.assert_called()
        parse.assert_called()
        payload.assert_called()

    def test_insert_infraction_validation_error(self, mockMimirMongoCon):
        data = {self.KEY_SHOPPER_ID: self.SHOPPER_ID2, self.KEY_TICKET_ID: '130F', 'sourceDomainOrIp': self.TEST_DOMAIN,
                'hostedStatus': self.HOSTED, 'hostingGuid': self.GUID1, 'infractionType': 'Oops',
                'recordType': 'INFRACTION'}
        response = self.client.post(url_for('infractions'), data=json.dumps(data), headers=self.HEADERS)
        self.assertEqual(response.status_code, 400)

    def test_insert_infraction_when_required_param_missing(self, mockMimirMongoCon):
        data = {self.KEY_SHOPPER_ID: self.SHOPPER_ID2, self.KEY_TICKET_ID: '131F', 'sourceDomainOrIp': self.TEST_DOMAIN,
                'hostedStatus': self.HOSTED, 'hostingGuid': self.GUID1, 'recordType': 'INFRACTION'}
        response = self.client.post(url_for('infractions'), data=json.dumps(data), headers=self.HEADERS)
        self.assertEqual(response.status_code, 400)

    @patch.object(AuthToken, 'payload', return_value=MockJomaxToken.payload)
    @patch.object(AuthToken, 'parse', return_value=MockJomaxToken())
    @patch.object(service.rest.api, 'validate_group', return_value=True)
    @patch.object(QueryHelper, 'insert_infraction')
    def test_insert_infraction_with_note_no_ticket_id(self, insert_infraction, validate_group, parse, payload, mockMimirMongoCon):
        insert_infraction.return_value = '12346', False
        data = {self.KEY_SHOPPER_ID: self.SHOPPER_ID2, 'sourceDomainOrIp': self.TEST_DOMAIN, 'hostedStatus': self.HOSTED,
                'hostingGuid': self.GUID1, 'infractionType': self.CUSTOMER_WARNING, 'note': 'manual note',
                'abuseType': self.PHISHING, 'recordType': 'INFRACTION'}
        response = self.client.post(url_for('infractions'), data=json.dumps(data), headers=self.HEADERS)
        self.assertEqual(response.status_code, 201)
        insert_infraction.assert_called()
        parse.assert_called()
        payload.assert_called()

    @patch.object(AuthToken, 'payload', return_value=MockJomaxToken.payload)
    @patch.object(AuthToken, 'parse', return_value=MockJomaxToken())
    @patch.object(service.rest.api, 'validate_group', return_value=True)
    @patch.object(QueryHelper, 'insert_infraction')
    def test_insert_new_csam_infraction(self, insert_infraction, validate_group, parse, payload, mockMimirMongoCon):
        insert_infraction.return_value = '12345', False
        data = {self.KEY_SHOPPER_ID: self.SHOPPER_ID2, self.KEY_TICKET_ID: '128F',
                'sourceDomainOrIp': 'test-csam-domain.com', 'hostedStatus': self.HOSTED, 'hostingGuid': self.GUID1,
                'infractionType': 'NCMEC_REPORT_SUBMITTED', 'abuseType': self.CHILD_ABUSE, 'recordType': 'INFRACTION'}
        response = self.client.post(url_for('infractions'), data=json.dumps(data), headers=self.HEADERS)
        self.assertEqual(response.status_code, 201)
        insert_infraction.assert_called()
        parse.assert_called()
        payload.assert_called()

    @patch.object(AuthToken, 'payload', return_value=MockJomaxToken.payload)
    @patch.object(AuthToken, 'parse', return_value=MockJomaxToken())
    @patch.object(service.rest.api, 'validate_group', return_value=True)
    def test_insert_non_infraction_record_type(self, validate_group, parse, payload, mockMimirMongoCon):
        data = {self.KEY_SHOPPER_ID: self.SHOPPER_ID2, self.KEY_TICKET_ID: '133F', 'sourceDomainOrIp': self.TEST_DOMAIN,
                'hostedStatus': self.HOSTED, 'hostingGuid': self.GUID1, 'infractionType': self.CUSTOMER_WARNING,
                'abuseType': self.PHISHING, 'recordType': 'NOTE'}
        response = self.client.post(url_for('infractions'), data=json.dumps(data), headers=self.HEADERS)
        self.assertEqual(response.status_code, 400)
        parse.assert_called()
        payload.assert_called()

    '''Post Non Infraction Tests'''

    @patch.object(AuthToken, 'payload', return_value=MockJomaxToken.payload)
    @patch.object(AuthToken, 'parse', return_value=MockJomaxToken())
    @patch.object(service.rest.api, 'validate_group', return_value=True)
    @patch.object(QueryHelper, 'insert_non_infraction')
    def test_insert_non_infraction_with_note(self, insert_infraction, validate_group, parse, payload, mockMimirMongoCon):
        insert_infraction.return_value = '12346', False
        data = {self.KEY_SHOPPER_ID: self.SHOPPER_ID2, 'recordType': 'NOTE', 'sourceDomainOrIp': self.TEST_DOMAIN,
                'note': 'manual note', 'abuseType': self.PHISHING}
        response = self.client.post(url_for('non-infraction'), data=json.dumps(data), headers=self.HEADERS)
        self.assertEqual(response.status_code, 201)
        insert_infraction.assert_called()
        parse.assert_called()
        payload.assert_called()

    @patch.object(AuthToken, 'payload', return_value=MockJomaxToken.payload)
    @patch.object(AuthToken, 'parse', return_value=MockJomaxToken())
    @patch.object(service.rest.api, 'validate_group', return_value=True)
    @patch.object(QueryHelper, 'insert_non_infraction')
    def test_insert_non_infraction_ncmec(self, insert_infraction, validate_group, parse, payload, mockMimirMongoCon):
        insert_infraction.return_value = '12346', False
        data = {self.KEY_SHOPPER_ID: self.SHOPPER_ID2, 'recordType': 'NCMEC_REPORT',
                'sourceDomainOrIp': self.TEST_DOMAIN, 'note': 'manual note', 'abuseType': self.PHISHING}
        response = self.client.post(url_for('non-infraction'), data=json.dumps(data), headers=self.HEADERS)
        self.assertEqual(response.status_code, 201)
        insert_infraction.assert_called()
        parse.assert_called()
        payload.assert_called()

    def test_insert_non_infraction_required_param_missing(self, mockMimirMongoCon):
        data = {self.KEY_SHOPPER_ID: self.SHOPPER_ID2, 'sourceDomainOrIp': self.TEST_DOMAIN,
                'note': 'manual note', 'abuseType': self.PHISHING}
        response = self.client.post(url_for('non-infraction'), data=json.dumps(data), headers=self.HEADERS)
        self.assertEqual(response.status_code, 400)

    '''Get Infractions Tests'''

    @patch.object(AuthToken, 'payload', return_value=MockJomaxToken.payload)
    @patch.object(AuthToken, 'parse', return_value=MockJomaxToken())
    @patch.object(service.rest.api, 'validate_group', return_value=True)
    @patch.object(QueryHelper, 'get_history')
    def test_get_matching_hosted_history(self, get_history, validate_group, parse, payload, mockMimirMongoCon):
        data = {self.KEY_SHOPPER_ID: self.SHOPPER_ID1}
        get_history.return_value = [
            {self.KEY_INFRACTION_ID: '5c5cc2b85f627d8562e7f1f3', self.KEY_SHOPPER_ID: self.SHOPPER_ID1,
             self.KEY_TICKET_ID: '1234', 'sourceDomainOrIp': 'abcs.com', 'hostingGuid': 'abc123-def456-ghi789',
             'infractionType': self.CUSTOMER_WARNING, 'createdDate': '2019-02-07T23:43:52.471Z'}
        ]
        response = self.client.get(url_for('history'), headers=self.HEADERS, query_string=data)
        self.assertEqual(response.status_code, 200)
        get_history.assert_called()
        parse.assert_called()
        payload.assert_called()

    @patch.object(AuthToken, 'payload', return_value=MockJomaxToken.payload)
    @patch.object(AuthToken, 'parse', return_value=MockJomaxToken())
    @patch.object(service.rest.api, 'validate_group', return_value=True)
    @patch.object(QueryHelper, 'get_history')
    def test_get_history_with_infraction_type(self, get_history, validate_group, parse, payload, mockMimirMongoCon):
        data = {self.KEY_SHOPPER_ID: self.SHOPPER_ID1, 'infractionTypes': [self.CUSTOMER_WARNING, self.SUSPENDED]}
        get_history.return_value = [
            {self.KEY_INFRACTION_ID: '5c5cc2b85f627d8562e7f1f3', self.KEY_SHOPPER_ID: self.SHOPPER_ID1,
             self.KEY_TICKET_ID: '1234', 'sourceDomainOrIp': 'abcs.com', 'hostingGuid': 'abc123-def456-ghi789',
             'infractionType': self.CUSTOMER_WARNING, 'createdDate': '2019-02-07T23:43:52.471Z'},
            {self.KEY_INFRACTION_ID: '5c5cc2b85f627d8562e7faaa', self.KEY_SHOPPER_ID: self.SHOPPER_ID1,
             self.KEY_TICKET_ID: '1235', 'sourceDomainOrIp': 'abcs12.com', 'hostingGuid': 'abc123-def456-ghi789',
             'infractionType': self.SUSPENDED, 'createdDate': '2019-03-07T23:43:52.471Z'}
        ]
        response = self.client.get(url_for('history'), headers=self.HEADERS, query_string=data)
        self.assertEqual(response.status_code, 200)
        get_history.assert_called()
        parse.assert_called()
        payload.assert_called()

    @patch.object(AuthToken, 'payload', return_value=MockJomaxToken.payload)
    @patch.object(AuthToken, 'parse', return_value=MockJomaxToken())
    @patch.object(service.rest.api, 'validate_group', return_value=True)
    @patch.object(QueryHelper, 'get_history')
    def test_get_matching_reg_history(self, get_history, validate_group, parse, payload, mockMimirMongoCon):
        data = {self.KEY_SHOPPER_ID: self.SHOPPER_ID1, 'hostedStatus': self.REGISTERED}
        get_history.return_value = [
            {self.KEY_INFRACTION_ID: '5c5cc2b85f627d8562e7f1f3', self.KEY_SHOPPER_ID: self.SHOPPER_ID1,
             self.KEY_TICKET_ID: '1234', 'sourceDomainOrIp': 'abcs.com', 'domainId': '12345',
             'infractionType': 'CUSTOMER_WARNING', 'createdDate': '2019-02-07T23:43:52.471Z'}
        ]
        response = self.client.get(url_for('history'), headers=self.HEADERS, query_string=data)
        self.assertEqual(response.status_code, 200)
        get_history.assert_called()
        parse.assert_called()
        payload.assert_called()

    @patch.object(AuthToken, 'payload', return_value=MockJomaxToken.payload)
    @patch.object(AuthToken, 'parse', return_value=MockJomaxToken())
    @patch.object(service.rest.api, 'validate_group', return_value=True)
    @patch.object(QueryHelper, 'get_history')
    def test_get_no_matching_history(self, get_history, validate_group, parse, payload, mockMimirMongoCon):
        data = {self.KEY_SHOPPER_ID: self.SHOPPER_ID1}
        get_history.return_value = []
        response = self.client.get(url_for('history'), headers=self.HEADERS, query_string=data)
        self.assertIsNone(response.json.get(self.KEY_PAGINATION, {}).get(self.KEY_NEXT))
        get_history.assert_called()
        parse.assert_called()
        payload.assert_called()

    @patch.object(AuthToken, 'payload', return_value=MockJomaxToken.payload)
    @patch.object(AuthToken, 'parse', return_value=MockJomaxToken())
    @patch.object(service.rest.api, 'validate_group', return_value=True)
    @patch.object(QueryHelper, 'get_history')
    def test_get_no_matching_history_error(self, get_history, validate_group, parse, payload, mockMimirMongoCon):
        data = {'infractionTypes': 'IT_BAD'}
        get_history.side_effect = TypeError()
        response = self.client.get(url_for('history'), headers=self.HEADERS, query_string=data)
        self.assertEqual(response.status_code, 422)
        get_history.assert_called()
        parse.assert_called()
        payload.assert_called()

    @patch.object(AuthToken, 'payload', return_value=MockJomaxToken.payload)
    @patch.object(AuthToken, 'parse', return_value=MockJomaxToken())
    @patch.object(service.rest.api, 'validate_group', return_value=True)
    @patch.object(QueryHelper, 'get_history')
    def test_get_history_type_error(self, get_history, validate_group, parse, payload, mockMimirMongoCon):
        data = {'infractionTypes': 'INTENTIONALLY_MALICIOUS', self.KEY_SHOPPER_ID: self.SHOPPER_ID1}
        get_history.side_effect = TypeError()
        response = self.client.get(url_for('history'), headers=self.HEADERS, query_string=data)
        self.assertEqual(response.status_code, 422)
        get_history.assert_called()
        parse.assert_called()
        payload.assert_called()

    @patch.object(AuthToken, 'payload', return_value=MockJomaxToken.payload)
    @patch.object(AuthToken, 'parse', return_value=MockJomaxToken())
    @patch.object(service.rest.api, 'validate_group', return_value=True)
    @patch.object(QueryHelper, 'get_history')
    def test_get_none_infraction_type(self, get_history, validate_group, parse, payload, mockMimirMongoCon):
        data = {'infractionTypes': None}
        get_history.side_effect = TypeError()
        response = self.client.get(url_for('history'), headers=self.HEADERS, query_string=data)
        self.assertEqual(response.status_code, 422)
        get_history.assert_called()
        parse.assert_called()
        payload.assert_called()

    @patch.object(AuthToken, 'payload', return_value=MockJomaxToken.payload)
    @patch.object(AuthToken, 'parse', return_value=MockJomaxToken())
    @patch.object(service.rest.api, 'validate_group', return_value=True)
    @patch.object(QueryHelper, 'get_history')
    def test_get_infraction_count_less_than_limit(self, get_history, validate_group, parse, payload, mockMimirMongoCon):
        data = {self.KEY_SHOPPER_ID: self.SHOPPER_ID1}
        response = self.client.get(url_for('history'), headers=self.HEADERS, query_string=data)
        self.assertIsNone(response.json.get(self.KEY_PAGINATION, {}).get(self.KEY_NEXT))
        get_history.assert_called()
        parse.assert_called()
        payload.assert_called()

    @patch.object(AuthToken, 'payload', return_value=MockJomaxToken.payload)
    @patch.object(AuthToken, 'parse', return_value=MockJomaxToken())
    @patch.object(service.rest.api, 'validate_group', return_value=True)
    @patch.object(QueryHelper, 'get_history')
    def test_history_pagination_invalid_prev_url(self, get_history, validate_group, parse, payload, mockMimirMongoCon):
        data = {self.KEY_SHOPPER_ID: self.SHOPPER_ID1, 'offset': 0, 'limit': 2}
        get_history.return_value = [
            {self.KEY_INFRACTION_ID: '1', self.KEY_SHOPPER_ID: self.SHOPPER_ID1, self.KEY_TICKET_ID: '1234'},
            {self.KEY_INFRACTION_ID: '2', self.KEY_SHOPPER_ID: self.SHOPPER_ID1, self.KEY_TICKET_ID: '1235'},
            {self.KEY_INFRACTION_ID: '3', self.KEY_SHOPPER_ID: self.SHOPPER_ID1, self.KEY_TICKET_ID: '1236'},
            {self.KEY_INFRACTION_ID: '4', self.KEY_SHOPPER_ID: self.SHOPPER_ID1, self.KEY_TICKET_ID: '1237'}
        ]
        response = self.client.get(url_for('history'), headers=self.HEADERS, query_string=data)
        next_url = response.json.get(self.KEY_PAGINATION, {}).get(self.KEY_NEXT)
        prev_url = response.json.get(self.KEY_PAGINATION, {}).get(self.KEY_PREV)
        self.assertEqual(next_url, f'{self.GET_HISTORY_URL}?shopperId={self.SHOPPER_ID1}&limit=2&offset=2')
        self.assertEqual(prev_url, f'{self.GET_HISTORY_URL}?shopperId={self.SHOPPER_ID1}&limit=2&offset=0')
        get_history.assert_called()
        parse.assert_called()
        payload.assert_called()

    @patch.object(AuthToken, 'payload', return_value=MockJomaxToken.payload)
    @patch.object(AuthToken, 'parse', return_value=MockJomaxToken())
    @patch.object(service.rest.api, 'validate_group', return_value=True)
    @patch.object(QueryHelper, 'get_history')
    def test_history_pagination_valid_prev_url(self, get_history, validate_group, parse, payload, mockMimirMongoCon):
        data = {self.KEY_SHOPPER_ID: self.SHOPPER_ID1, 'offset': 3, 'limit': 2}
        get_history.return_value = [
            {self.KEY_INFRACTION_ID: '1', self.KEY_SHOPPER_ID: self.SHOPPER_ID1, self.KEY_TICKET_ID: '1334'},
            {self.KEY_INFRACTION_ID: '2', self.KEY_SHOPPER_ID: self.SHOPPER_ID1, self.KEY_TICKET_ID: '1335'},
            {self.KEY_INFRACTION_ID: '3', self.KEY_SHOPPER_ID: self.SHOPPER_ID1, self.KEY_TICKET_ID: '1336'},
            {self.KEY_INFRACTION_ID: '4', self.KEY_SHOPPER_ID: self.SHOPPER_ID1, self.KEY_TICKET_ID: '1337'}
        ]
        response = self.client.get(url_for('history'), headers=self.HEADERS, query_string=data)
        next_url = response.json.get(self.KEY_PAGINATION, {}).get(self.KEY_NEXT)
        prev_url = response.json.get(self.KEY_PAGINATION, {}).get(self.KEY_PREV)
        self.assertEqual(next_url, f'{self.GET_HISTORY_URL}?shopperId={self.SHOPPER_ID1}&limit=2&offset=5')
        self.assertEqual(prev_url, f'{self.GET_HISTORY_URL}?shopperId={self.SHOPPER_ID1}&limit=2&offset=1')
        get_history.assert_called()
        parse.assert_called()
        payload.assert_called()

    '''Infraction Count Tests'''

    @patch.object(AuthToken, 'payload', return_value=MockJomaxToken.payload)
    @patch.object(AuthToken, 'parse', return_value=MockJomaxToken())
    @patch.object(service.rest.api, 'validate_group', return_value=True)
    @patch.object(QueryHelper, 'count_infractions')
    def test_count_infractions_pass_nonzero_count(self, count_infractions, validate_group, parse, payload, mockMimirMongoCon):
        data = {self.KEY_SHOPPER_ID: self.SHOPPER_ID1}
        count_infractions.return_value = 12
        response = self.client.get(url_for('infraction_count'), headers=self.HEADERS, query_string=data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(int(response.data), 12)
        count_infractions.assert_called()
        parse.assert_called()
        payload.assert_called()

    @patch.object(AuthToken, 'payload', return_value=MockJomaxToken.payload)
    @patch.object(AuthToken, 'parse', return_value=MockJomaxToken())
    @patch.object(service.rest.api, 'validate_group', return_value=True)
    @patch.object(QueryHelper, 'count_infractions')
    def test_count_infractions_pass_zero_count(self, count_infractions, validate_group, parse, payload, mockMimirMongoCon):
        data = {self.KEY_SHOPPER_ID: self.SHOPPER_ID1}
        count_infractions.return_value = 0
        response = self.client.get(url_for('infraction_count'), headers=self.HEADERS, query_string=data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(int(response.data), 0)
        count_infractions.assert_called()
        parse.assert_called()
        payload.assert_called()

    @patch.object(AuthToken, 'payload', return_value=MockJomaxToken.payload)
    @patch.object(AuthToken, 'parse', return_value=MockJomaxToken())
    @patch.object(service.rest.api, 'validate_group', return_value=True)
    def test_count_infractions_fail_empty_query(self, validate_group, parse, payload, mockMimirMongoCon):
        response = self.client.get(url_for('infraction_count'), headers=self.HEADERS, query_string={})
        self.assertEqual(response.status_code, 422)
        parse.assert_called()
        payload.assert_called()

    @patch.object(AuthToken, 'payload', return_value=MockJomaxToken.payload)
    @patch.object(AuthToken, 'parse', return_value=MockJomaxToken())
    @patch.object(service.rest.api, 'validate_group', return_value=True)
    @patch.object(QueryHelper, 'count_infractions')
    def test_count_infractions_pass_unknown_key_query(self, count_infractions, validate_group, parse, payload, mockMimirMongoCon):
        data = {'unknownKey': 'Value for Unknown Key', self.KEY_SHOPPER_ID: self.SHOPPER_ID1}
        count_infractions.return_value = 12
        response = self.client.get(url_for('infraction_count'), headers=self.HEADERS, query_string=data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(int(response.data), 12)
        count_infractions.assert_called()
        parse.assert_called()
        payload.assert_called()

    @patch.object(AuthToken, 'payload', return_value=MockJomaxToken.payload)
    @patch.object(AuthToken, 'parse', return_value=MockJomaxToken())
    @patch.object(service.rest.api, 'validate_group', return_value=True)
    @patch.object(QueryHelper, 'count_infractions')
    def test_count_infractions_fail_type_error(self, count_infractions, validate_group, parse, payload, mockMimirMongoCon):
        data = {'infractionTypes': 'INTENTIONALLY_MALICIOUS', self.KEY_SHOPPER_ID: self.SHOPPER_ID1}
        count_infractions.side_effect = TypeError()
        response = self.client.get(url_for('infraction_count'), headers=self.HEADERS, query_string=data)
        self.assertEqual(response.status_code, 422)
        count_infractions.assert_called()
        parse.assert_called()
        payload.assert_called()
