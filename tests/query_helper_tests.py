from copy import deepcopy
from datetime import datetime
from unittest import TestCase as UnitTestTestCase

import mongomock
from bson import ObjectId
from dcdatabase.mimir.mongo import MimirMongo
from flask_testing.utils import TestCase
from mock import MagicMock, patch
from redlock import RedLock

import service.rest
from service.utils.query_helper import QueryHelper
from settings import config_by_name


class TestQueryHelper(TestCase, UnitTestTestCase):
    test_config = config_by_name['unit-test']()
    ABUSE_TYPE = 'PHISHING'
    DOMAIN = 'abc.com'
    DOMAIN_ID = '10101'
    GUID = 'some-guid'
    INFRACTION_TYPE = 'CUSTOMER_WARNING'
    OBJECT_ID = ObjectId('666f6f2d6261722d71757578')
    SHOPPER_ID = '11111133'
    TEST_DATE = datetime.strptime('2021-05-01', '%Y-%m-%d')
    TICKET_ID = 'DCU1111'

    def create_app(self):
        return service.rest.create_app(self.test_config)

    @patch.object(MimirMongo, '__init__', return_value=None)
    def setUp(self, mockMimirMongo):
        self._qh = QueryHelper(self.test_config)
        self._qh._mongo = mongomock.MongoClient()
        self._infraction_obj = {
            'infractionType': self.INFRACTION_TYPE,
            'sourceDomainOrIp': self.DOMAIN,
            'hostingGuid': None,
            'ticketId': self.TICKET_ID,
            'shopperId': self.SHOPPER_ID
        }
        self._infraction_obj2 = {
            'infractionType': self.INFRACTION_TYPE,
            'sourceDomainOrIp': self.DOMAIN,
            'hostingGuid': None,
            'shopperId': self.SHOPPER_ID
        }
        self._infraction_obj_host = {
            'abuseType': self.ABUSE_TYPE,
            'infractionType': self.INFRACTION_TYPE,
            'sourceDomainOrIp': self.DOMAIN,
            'hostingGuid': self.GUID,
            'ticketId': self.TICKET_ID,
            'shopperId': self.SHOPPER_ID,
        }
        self._infraction_obj_domain = {
            'abuseType': self.ABUSE_TYPE,
            'infractionType': self.INFRACTION_TYPE,
            'sourceDomainOrIp': self.DOMAIN,
            'domainId': self.DOMAIN_ID,
            'ticketId': self.TICKET_ID,
            'shopperId': self.SHOPPER_ID
        }
        self._infraction_obj_other = {
            'abuseType': self.ABUSE_TYPE,
            'infractionType': self.INFRACTION_TYPE,
            'sourceDomainOrIp': self.DOMAIN,
            'ticketId': self.TICKET_ID,
            'shopperId': self.SHOPPER_ID
        }
        self._infraction_obj_lists = {
            'abuseType': self.ABUSE_TYPE,
            'infractionType': self.INFRACTION_TYPE,
            'hostedStatus': 'HOSTED'
        }
        self._infraction_from_id = {
            '_id': self.OBJECT_ID,
            'createdDate': self.TEST_DATE
        }

    def test_create_composite_key_host(self):
        composite_key = QueryHelper._create_composite_key(self._infraction_obj_host)
        self.assertEqual(f'{self.DOMAIN},{self.SHOPPER_ID},{self.GUID},{self.INFRACTION_TYPE},{self.ABUSE_TYPE}', composite_key)

    def test_create_composite_key_domain(self):
        composite_key = QueryHelper._create_composite_key(self._infraction_obj_domain)
        self.assertEqual(f'{self.DOMAIN},{self.SHOPPER_ID},{self.DOMAIN_ID},{self.INFRACTION_TYPE},{self.ABUSE_TYPE}', composite_key)

    def test_create_composite_key_other(self):
        composite_key = QueryHelper._create_composite_key(self._infraction_obj_other)
        self.assertEqual(f'{self.DOMAIN},{self.SHOPPER_ID},,{self.INFRACTION_TYPE},{self.ABUSE_TYPE}', composite_key)

    @patch.object(MimirMongo, 'get_duplicate_infractions_before_add', return_value=TICKET_ID)
    def test_check_duplicate_and_persist_duplicate_infraction(self, mock_dup):
        self.assertEqual((self.TICKET_ID, True), self._qh._check_duplicate_and_persist(self._infraction_obj_lists))
        mock_dup.assert_called()

    @patch.object(MimirMongo, 'add_infraction', return_value=TICKET_ID)
    @patch.object(MimirMongo, 'get_duplicate_infractions_before_add', return_value=None)
    def test_check_duplicate_and_persist_unique_infraction(self, mock_dup, mock_add):
        self.assertEqual((self.TICKET_ID, False), self._qh._check_duplicate_and_persist(self._infraction_obj_lists))
        mock_dup.assert_called()
        mock_add.assert_called()

    @patch.object(MimirMongo, 'get_infraction')
    def test_get_infraction_from_id_success(self, mock_get):
        mock_get.return_value = deepcopy(self._infraction_from_id)
        expected = {'infractionId': str(self.OBJECT_ID), 'createdDate': str(self.TEST_DATE)}
        self.assertEqual(expected, self._qh.get_infraction_from_id(''))
        mock_get.assert_called()

    @patch.object(MimirMongo, 'get_infraction', return_value=None)
    def test_get_infraction_from_id_fail(self, mock_get):
        self.assertIsNone(self._qh.get_infraction_from_id(''))
        mock_get.assert_called()

    @patch('redlock.RedLockFactory.create_lock')
    @patch.object(MimirMongo, 'get_duplicate_infractions_before_add', return_value='aaaa1111')
    def test_insert_infraction_duplicate(self, mimir_mongo, redlock):
        redlock.return_value = MagicMock(spec=RedLock, acquire=lambda: True,
                                         create_lock=lambda x: True, release=lambda: True)
        result = self._qh.insert_infraction(self._infraction_obj)
        self.assertEqual(result, ('aaaa1111', True))
        mimir_mongo.assert_called()
        redlock.assert_called()

    @patch('redlock.RedLockFactory.create_lock')
    @patch.object(MimirMongo, 'get_duplicate_infractions_before_add', return_value=None)
    @patch.object(MimirMongo, 'add_infraction', return_value='bbbb22222')
    def test_insert_infraction(self, mimir_add, mimir_dupe, redlock):
        redlock.return_value = MagicMock(spec=RedLock, acquire=lambda: True,
                                         create_lock=lambda x: True, release=lambda: True)
        result = self._qh.insert_infraction(self._infraction_obj)
        self.assertEqual(result, ('bbbb22222', False))
        mimir_add.assert_called()
        mimir_dupe.assert_called()
        redlock.assert_called()

    @patch('redlock.RedLockFactory.create_lock')
    @patch.object(MimirMongo, 'get_duplicate_infractions_before_add', return_value=None)
    @patch.object(MimirMongo, 'add_infraction', return_value='cccc33333')
    def test_insert_infraction_no_ticket_id(self, mimir_add, mimir_dupe, redlock):
        redlock.return_value = MagicMock(spec=RedLock, acquire=lambda: True,
                                         create_lock=lambda x: True, release=lambda: True)
        result = self._qh.insert_infraction(self._infraction_obj2)
        self.assertEqual(result, ('cccc33333', False))
        mimir_add.assert_called()
        mimir_dupe.assert_called()
        redlock.assert_called()

    @patch.object(MimirMongo, 'get_history')
    def test_get_history_success(self, mock_get):
        mock_get.return_value = [deepcopy(self._infraction_from_id)]
        result = self._qh.get_history({})
        expected = [{'infractionId': str(self.OBJECT_ID), 'createdDate': str(self.TEST_DATE)}]
        self.assertEqual(expected, result)
        mock_get.assert_called()
