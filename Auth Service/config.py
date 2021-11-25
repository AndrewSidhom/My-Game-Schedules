class Config(object):
    SQLALCHEMY_DATABASE_URI = r"sqlite:///user.sqlite"
    SECRET = "8fa70fd8b74bd9533537088f7e9d64ea"
    SECRETS = {'front_end': 'f0fdeb1f1584fd5431c4250b2e859457', 'schedule_retriever': 'a0adec1f1544fd3431c1120b2e859457', 'db_management': 'd1haeb1f1584fd5431c4250b2e859457'}


class ProdConfig(Config):
    pass


class DevConfig(Config):
    DEBUG = True


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = r"sqlite:///tests/test_user.sqlite"
