from .cfg import *

class Tester:
    def __init__(self):
        pass

    def run(self, tests: list):
        Cfg().read_userconfig()
        Cfg().validate_all()

        for instance in tests:
            instance.build()
