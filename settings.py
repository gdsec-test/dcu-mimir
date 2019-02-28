import os
import urllib


class AppConfig(object):
    DB = 'test'
    DB_USER = 'dbuser'
    DB_HOST = 'localhost'
    COLLECTION = 'infractions'

    def __init__(self):
        self.DB_PASS = urllib.parse.quote(os.getenv('DB_PASS', 'password'))
        self.DBURL = 'mongodb://{}:{}@{}/{}'.format(self.DB_USER, self.DB_PASS, self.DB_HOST, self.DB)


class ProductionAppConfig(AppConfig):
    TOKEN_AUTHORITY = 'sso.godaddy.com'
    CN_WHITELIST = {'dcu.zeus.int.prod-godaddy.com'}
    DB = 'phishstory'
    DB_HOST = '10.22.9.209'
    DB_USER = 'sau_p_phish'

    def __init__(self):
        super(ProductionAppConfig, self).__init__()


class OTEAppConfig(AppConfig):
    TOKEN_AUTHORITY = 'sso.ote-godaddy.com'
    CN_WHITELIST = {'dcu.zeus.int.ote-godaddy.com'}
    DB = 'otephishstory'
    DB_HOST = '10.22.9.209'
    DB_USER = 'sau_o_phish'

    def __init__(self):
        super(OTEAppConfig, self).__init__()


class DevelopmentAppConfig(AppConfig):
    TOKEN_AUTHORITY = 'sso.dev-godaddy.com'
    CN_WHITELIST = {'dcu.zeus.int.dev-godaddy.com'}
    DB = 'devphishstory'
    DB_HOST = '10.22.188.208'
    DB_USER = 'devuser'

    def __init__(self):
        super(DevelopmentAppConfig, self).__init__()


class TestingConfig(AppConfig):
    TOKEN_AUTHORITY = 'test'
    CN_WHITELIST = {'dcu.zeus.int.test-godaddy.com'}
    DBURL = 'mongodb://localhost/devphishstory'
    DB = 'test'
    COLLECTION = 'test'


config_by_name = {'dev': DevelopmentAppConfig,
                  'prod': ProductionAppConfig,
                  'ote': OTEAppConfig,
                  'test': TestingConfig}
