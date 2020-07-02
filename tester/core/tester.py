from .cfg import *
from .csvfile import *
from .metricsfile import *
import test

import time

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

        sequences = [test.VideoSequence(filepath) for filepath in input_sequence_filepaths]
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
                    for sequence in sequences:
                        console_logger.debug(f"Encoding sequence '{sequence.get_input_filename()}'"
                                             f" with configuration '{config.get_name()}'")
                        metrics_file = MetricsFile(config.get_encoder_instance(), param_set, sequence)
                        if not os.path.exists(metrics_file.get_filepath()):
                            start_time: float = time.perf_counter()
                            config.get_encoder_instance().encode(sequence, param_set)
                            seconds: float = round(time.perf_counter() - start_time, 6)
                            metrics_file.set_encoder_name(config.get_encoder_instance().get_encoder_name())
                            metrics_file.set_encoder_revision(config.get_encoder_instance().get_revision())
                            metrics_file.set_encoder_defines(config.get_encoder_instance().get_defines())
                            metrics_file.set_encoder_cmdline(param_set.to_cmdline_str())
                            metrics_file.set_encoding_input(sequence.get_input_filename())
                            metrics_file.set_encoding_output(f"{sequence.get_input_filename(include_extension=False)}.hevc")
                            metrics_file.set_encoding_resolution(f"{sequence.width}x{sequence.height}")
                            metrics_file.set_encoding_time(seconds)
                        else:
                            console_logger.info(f"Sequence '{sequence.get_input_filename()}'"
                                                f" has already been encoded with configuration '{config.get_name()}'"
                                                f" - aborting encoding")
            return True
        except:
            raise

    def generate_csv(self, configs: list, input_sequence_filepaths: list, csv_filepath: str):

        sequences = [test.VideoSequence(filepath) for filepath in input_sequence_filepaths]
        try:
            csvfile = CsvFile(csv_filepath)
            csvfile.set_header_names([
                "Sequence",
                "Seq class",
                "Config name",
                "Encoder",
                "Revision",
                "Defines",
                "Command line",
                "Quality parameter",
                "Quality parameter value",
                "Time (s)",
            ])
            for sequence in sequences:
                for config in configs:
                    for param_set in config.get_encoding_param_sets():
                        metrics_file = MetricsFile(config.get_encoder_instance(),
                                                   param_set,
                                                   sequence)
                        csvfile.add_entry([
                            sequence.get_input_filename(),
                            sequence.get_class(),
                            config.get_name(),
                            config.get_encoder_instance().get_encoder_name(),
                            config.get_encoder_instance().get_revision(),
                            config.get_encoder_instance().get_defines(),
                            param_set.to_cmdline_str(),
                            param_set.get_quality_param_name(),
                            param_set.get_quality_param_value(),
                            metrics_file.get_encoding_time()
                        ])
        except:
            console_logger.error(f"Failed to write metrics to file '{csv_filepath}'")
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
