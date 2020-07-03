from .cfg import *
from .csvfile import *
from .metrics import *
import test

import time

class Tester:
    def __init__(self):
        Cfg().read_userconfig()
        Cfg().validate_all()
        self.create_directories()
        self.configs: list = []
        self.configs_by_name: dict = {}
        self.sequences: list = []
        self.metrics: dict = {}

    def create_directories(self):
        for path in Cfg().binaries_dir_path,\
                    Cfg().encoding_output_dir_path,\
                    Cfg().reports_dir_path,\
                    Cfg().sources_dir_path:
            if not os.path.exists(path):
                console_logger.debug(f"Tester: Creating directory '{path}'")
                os.makedirs(path)

    def run(self, configs: list, input_sequence_filepaths: list):
        """Runs all tests."""

        self.sequences = [test.VideoSequence(filepath) for filepath in input_sequence_filepaths]
        self.configs = configs
        for config in self.configs:
            self.configs_by_name[config.get_name()] = config

        try:
            self.create_directories()

            if not self.configs_are_unique(self.configs):
                console_logger.error("Aborting test run")
                return False

            for config1 in self.configs:
                for config2 in self.configs:
                    if config1.get_name() == config2.get_name() and config1 is not config2:
                        console_logger.error(f"Tester: Duplicate configuration name '{config1.get_name()}'")
                        console_logger.error("Aborting test run")
                        raise RuntimeError

            for config in self.configs:
                for anchor_name in config.get_anchor_names():
                    if not anchor_name in self.configs_by_name.keys():
                        console_logger.error(f"Tester: Anchor '{anchor_name}'"
                                             f" of configuration '{config.get_name()}' does not exist")
                        console_logger.error("Aborting test run")
                        raise RuntimeError

            for config in self.configs:
                config.get_encoder_instance().build()

            for config in self.configs:
                for param_set in config.get_encoding_param_sets():
                    if not config.get_encoder_instance().dummy_run(param_set):
                        console_logger.error(f"Test configuration '{config.get_name()}' is invalid")
                        console_logger.error("Aborting test run")
                        raise RuntimeError

            for config in self.configs:
                for param_set in config.get_encoding_param_sets():
                    for sequence in self.sequences:
                        self.metrics[(config, param_set, sequence)] =\
                            Metrics(config.get_encoder_instance(), param_set, sequence)

            for config in self.configs:
                for param_set in config.get_encoding_param_sets():
                    for sequence in self.sequences:
                        console_logger.debug(f"Encoding sequence '{sequence.get_input_filename()}'"
                                             f" with configuration '{config.get_name()}'")
                        metrics = self.metrics[(config, param_set, sequence)]
                        if not metrics.exists():
                            start_time: float = time.perf_counter()
                            config.get_encoder_instance().encode(sequence, param_set)
                            seconds: float = round(time.perf_counter() - start_time, 6)
                            metrics.set_encoder_name(config.get_encoder_instance().get_encoder_name())
                            metrics.set_encoder_revision(config.get_encoder_instance().get_revision())
                            metrics.set_encoder_defines(config.get_encoder_instance().get_defines())
                            metrics.set_encoder_cmdline(param_set.to_cmdline_str())
                            metrics.set_encoding_input(sequence.get_input_filename())
                            metrics.set_encoding_output(f"{sequence.get_input_filename(include_extension=False)}.hevc")
                            metrics.set_encoding_resolution(f"{sequence.width}x{sequence.height}")
                            metrics.set_encoding_time(seconds)
                        else:
                            console_logger.info(f"Sequence '{sequence.get_input_filename()}'"
                                                f" has already been encoded with configuration '{config.get_name()}'"
                                                f" - aborting encoding")
        except:
            raise

    def generate_csv(self, configs: list, input_sequence_filepaths: list, csv_filepath: str):

        try:
            csvfile = CsvFile(csv_filepath)
            csvfile.set_header_names([
                "Sequence",
                "Seq class",
                "Encoder",
                "Revision",
                "Defines",
                "Command line",
                "Quality parameter",
                "Quality parameter value",
                "Name",
                "Anchor",
                "Time (s)",
                "Speedup",
            ])
            for sequence in self.sequences:
                for config in configs:
                    for anchor_name in config.get_anchor_names():
                        anchor_config = self.configs_by_name[anchor_name]
                        for param_set_index in range(len(config.get_encoding_param_sets())):
                            param_set = config.get_encoding_param_sets()[param_set_index]
                            anchor_param_set = anchor_config.get_encoding_param_sets()[param_set_index]
                            metrics = self.metrics[(config, param_set, sequence)]
                            anchor_metrics = self.metrics[(anchor_config), anchor_param_set, sequence]
                            csvfile.add_entry([
                                sequence.get_input_filename(),
                                sequence.get_class(),
                                config.get_encoder_instance().get_encoder_name(),
                                config.get_encoder_instance().get_revision(),
                                config.get_encoder_instance().get_defines(),
                                param_set.to_cmdline_str(),
                                param_set.get_quality_param_name(),
                                param_set.get_quality_param_value(),
                                config.get_name(),
                                anchor_name if anchor_name != config.get_name() else "-",
                                metrics.get_encoding_time(),
                                str(round(metrics.get_speedup_relative_to(anchor_metrics), 2))
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
