from dcdatabase.mimir.mongo import MimirMongo
from flask_testing.utils import TestCase
from mock import MagicMock, patch
from nose.tools import assert_equal
from redlock import RedLock

import service.rest
from service.utils.query_helper import QueryHelper
from settings import config_by_name


class TestQueryHelper(TestCase):
    test_config = config_by_name['test']()

    def create_app(self):
        return service.rest.create_app(self.test_config)

    @classmethod
    def setup_class(cls):
        cls._qh = QueryHelper(cls.test_config)
        cls._infraction_obj = {
            'infractionType': 'CUSTOMER_WARNING',
            'sourceDomainOrIp': 'abc.com',
            'hostingGuid': None,
            'ticketId': 'DCU1111',
            'shopperId': '11111133'
        }

    @patch('redlock.RedLockFactory.create_lock')
    @patch.object(MimirMongo, 'get_duplicate_infractions_before_add', return_value='aaaa1111')
    def test_insert_infraction_duplicate(self, mimir_mongo, redlock):
        redlock.return_value = MagicMock(spec=RedLock, acquire=lambda: True,
                                         create_lock=lambda x: True, release=lambda: True)
        result = self._qh.insert_infraction(self._infraction_obj)
        assert_equal(result, ('aaaa1111', True))

    @patch('redlock.RedLockFactory.create_lock')
    @patch.object(MimirMongo, 'get_duplicate_infractions_before_add', return_value=None)
    @patch.object(MimirMongo, 'add_infraction', return_value='bbbb22222')
    def test_insert_infraction(self, mimir_add, mimir_dupe, redlock):
        redlock.return_value = MagicMock(spec=RedLock, acquire=lambda: True,
                                         create_lock=lambda x: True, release=lambda: True)
        result = self._qh.insert_infraction(self._infraction_obj)
        assert_equal(result, ('bbbb22222', False))
