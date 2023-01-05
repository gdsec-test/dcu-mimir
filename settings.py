import os
from urllib.parse import quote


class AppConfig(object):
    DB = 'test'
    DB_USER = 'dbuser'
    DB_HOST = 'localhost'
    COLLECTION = 'infractions'
    AUTH_GROUPS = {'DCU-Phishstory'}

    def __init__(self):
        self.DB_PASS = quote(os.getenv('DB_PASS', 'password'))
        self.CLIENT_CERT = os.getenv("MONGO_CLIENT_CERT", '')
        self.DBURL = f'mongodb://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}/?authSource={self.DB}&readPreference=primary&directConnection=true&tls=true&tlsCertificateKeyFile={self.CLIENT_CERT}'


class ProductionAppConfig(AppConfig):
    TOKEN_AUTHORITY = 'sso.gdcorp.tools'
    CN_WHITELIST = {'zeus.client.cset.int.gdcorp.tools', 'brandservice.client.cset.int.gdcorp.tools', 'phishstory.client.cset.int.gdcorp.tools'}
    DB = 'phishstory'
    DB_HOST = 'p3plsocritmdb00-00-f0.prod.phx3.gdg'
    DB_USER = 'sau_p_phishv2'

    def __init__(self):
        super(ProductionAppConfig, self).__init__()


class OTEAppConfig(AppConfig):
    TOKEN_AUTHORITY = 'sso.ote-gdcorp.tools'
    CN_WHITELIST = {'zeus.client.cset.int.ote-gdcorp.tools', 'brandservice.client.cset.int.ote-gdcorp.tools', 'phishstory.client.cset.int.ote-gdcorp.tools'}
    DB = 'otephishstory'
    DB_HOST = 'p3plsocritmdb00-00-f0.prod.phx3.gdg'
    DB_USER = 'sau_o_phish'

    def __init__(self):
        super(OTEAppConfig, self).__init__()


class DevelopmentAppConfig(AppConfig):
    TOKEN_AUTHORITY = 'sso.dev-gdcorp.tools'
    CN_WHITELIST = {'zeus.client.cset.int.dev-gdcorp.tools', 'brandservice.client.cset.int.dev-gdcorp.tools', 'phishstory.client.cset.int.dev-gdcorp.tools'}
    DB = 'devphishstory'
    DB_HOST = 'mongodb.cset.int.dev-gdcorp.tools'
    DB_USER = 'devuser'

    def __init__(self):
        super(DevelopmentAppConfig, self).__init__()


class TestAppConfig(AppConfig):
    TOKEN_AUTHORITY = 'sso.test-gdcorp.tools'
    CN_WHITELIST = {'zeus.client.cset.int.test-gdcorp.tools', 'brandservice.client.cset.int.test-gdcorp.tools', 'phishstory.client.cset.int.test-gdcorp.tools'}
    DB = 'testphishstory'
    DB_HOST = 'mongodb.cset.int.dev-gdcorp.tools'
    DB_USER = 'testuser'

    def __init__(self):
        super(TestAppConfig, self).__init__()


class UnitTestConfig(AppConfig):
    TOKEN_AUTHORITY = 'test'
    CN_WHITELIST = {'zeus.client.cset.int.test-gdcorp.tools'}
    DBURL = 'mongodb://localhost/devphishstory'
    DB = 'test'
    COLLECTION = 'test'


config_by_name = {'dev': DevelopmentAppConfig,
                  'prod': ProductionAppConfig,
                  'ote': OTEAppConfig,
                  'unit-test': UnitTestConfig,
                  'test': TestAppConfig}
