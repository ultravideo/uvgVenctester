from .cfg import *
import test

class Tester:
    def __init__(self):
        Cfg().read_userconfig()
        Cfg().validate_all()
        self.create_directories()

    def create_directories(self):
        for path in Cfg().binaries_dir_path,\
                    Cfg().encoding_output_dir_path,\
                    Cfg().reports_dir_path,\
                    Cfg().sources_dir_path:
            if not os.path.exists(path):
                console_logger.debug(f"Tester: Creating directory '{path}'")
                os.makedirs(path)

    def run(self, configs: list, input_sequence_filepaths: list) -> bool:
        """Runs all tests. Returns True on success, False otherwise."""
        input_sequences = [test.VideoSequence(filepath) for filepath in input_sequence_filepaths]
        try:
            self.create_directories()

            if not self.configs_are_unique(configs):
                console_logger.error("Aborting test run")
                return False

            for config in configs:
                config.get_encoder_instance().build()

            for config in configs:
                for param_set in config.get_encoding_param_sets():
                    if not config.get_encoder_instance().dummy_run(param_set):
                        console_logger.error(f"Test configuration '{config.get_name()}' is invalid")
                        console_logger.error("Aborting test run")
                        return False

            for config in configs:
                for param_set in config.get_encoding_param_sets():
                    for sequence in input_sequences:
                        config.get_encoder_instance().encode(sequence, param_set, "out.hevc")

            return True
        except:
            raise

    def configs_are_unique(self, configs: list):
        """Checks that no two test configurations are the same. Returns True if not, False otherwise."""
        for config1 in configs:
            for config2 in configs:
                if config1 == config2 and not config1 is config2:
                    console_logger.error(f"Tester: Duplicate test configurations:"
                                         f" '{config1.get_name()}', '{config2.get_name()}'")
                    return False
        return True
