from .cfg import *

class Tester:
    def __init__(self):
        pass

    def run(self, tests: list) -> int:
        """Runs all tests. Returns True on success, False otherwise."""

        try:
            Cfg().read_userconfig()
            Cfg().validate_all()

            if not self.tests_are_unique(tests):
                console_logger.error("Aborting test run")
                return False

            for instance in tests:
                instance.build()

            return True
        except:
            raise

    def tests_are_unique(self, tests: list):
        """Checks that no two test instances are the same. Returns True if so, False otherwise."""
        for instance1 in tests:
            for instance2 in tests:
                if instance1 == instance2 and not instance1 is instance2:
                    console_logger.error(f"Duplicate test configuration: '{instance1.get_name()}', '{instance2.get_name()}'")
                    for instance in instance1, instance2:
                        console_logger.error(f"Configuration '{instance.get_name()}':"
                                             f" encoder_name='{instance.get_encoder_name()}',"
                                             f" revision='{instance.get_revision()}',"
                                             f" cl_args='{instance.get_cl_args()}',"
                                             f" defines={instance.get_defines()}")
                    return False

        return True
