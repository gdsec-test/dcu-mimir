import os

from redlock import RedLockFactory


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class Lock(metaclass=Singleton):

    def __init__(self):
        redis = os.getenv('REDIS', 'localhost')
        pool = [{"host": x} for x in redis.split(':')]
        self.lock = RedLockFactory(connection_details=pool)
