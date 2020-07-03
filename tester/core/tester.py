from .cfg import *
from .csvfile import *
from .metrics import *
from .testercontext import *
import test

import time
import traceback

class Tester:
    def __init__(self):
        Cfg().read_userconfig()
        Cfg().validate_all()
        self.create_base_directories_if_not_exist()

    def create_context(self, test_configurations: list, input_sequence_filepaths: list) -> TesterContext:
        # TODO: Copy by value, not by reference.
        context: TesterContext = TesterContext()
        context.configs = test_configurations

        for config in test_configurations:
            context.configs_by_name[config.get_name()] = config

        for filepath in input_sequence_filepaths:
            context.sequences.append(test.VideoSequence(filepath))

        for config in test_configurations:
            for param_set in config.get_encoding_param_sets():
                for sequence in context.sequences:
                    context.metrics[(config, param_set, sequence)] = \
                        Metrics(config.get_encoder_instance(), param_set, sequence)

        return context

    def log_exception(self, exception: Exception):
        console_logger.error(f"Tester: An exception of type '{type(exception).__name__}' was caught:"
                             f" {str(exception)}")
        console_logger.error(f"Tester: {traceback.format_exc()}")

    def validate_context_bottom(self, context: TesterContext):
        for config1 in context.configs:
            for config2 in context.configs:
                if config1 == config2 and not config1 is config2:
                    console_logger.error(f"Tester: Duplicate configurations:"
                                         f" '{config1.get_name()}', '{config2.get_name()}'")
                    raise RuntimeError

        for config1 in context.configs:
            for config2 in context.configs:
                if config1.get_name() == config2.get_name() and config1 is not config2:
                    console_logger.error(f"Tester: Duplicate configuration name '{config1.get_name()}'")
                    raise RuntimeError

        for config in context.configs:
            for anchor_name in config.get_anchor_names():
                if not anchor_name in context.configs_by_name.keys():
                    console_logger.error(f"Tester: Anchor '{anchor_name}'"
                                         f" of configuration '{config.get_name()}' does not exist")
                    raise RuntimeError

    def validate_context_top(self, context: TesterContext):
        for config in context.configs:
            for param_set in config.get_encoding_param_sets():
                if not config.get_encoder_instance().dummy_run(param_set):
                    console_logger.error(f"Tester: Configuration '{config.get_name()}' is invalid")
                    raise RuntimeError

    def create_base_directories_if_not_exist(self):
        for path in Cfg().binaries_dir_path,\
                    Cfg().encoding_output_dir_path,\
                    Cfg().reports_dir_path,\
                    Cfg().sources_dir_path:
            if not os.path.exists(path):
                console_logger.debug(f"Tester: Creating directory '{path}'")
                os.makedirs(path)

    def run_tests(self, context:TesterContext):
        try:
            self.validate_context_bottom(context)
            self.create_base_directories_if_not_exist()

            for config in context.configs:
                config.get_encoder_instance().build()

            self.validate_context_top(context)

            for config in context.configs:
                for param_set_index in (range(len(config.get_encoding_param_sets()))):
                    param_set = config.get_encoding_param_sets()[param_set_index]
                    for sequence in context.sequences:
                        console_logger.debug(f"Tester: Encoding sequence '{sequence.get_input_filename()}'"
                                             f" with configuration '{config.get_name()}'/"
                                             f"{param_set.get_quality_param_name()} {param_set.get_quality_param_value()}")
                        metrics = context.metrics[(config, param_set, sequence)]
                        if not metrics.file_exists():
                            start_time: float = time.perf_counter()
                            config.get_encoder_instance().encode(sequence, param_set)
                            seconds: float = round(time.perf_counter() - start_time, 6)
                            metrics.set_encoder_name(config.get_encoder_instance().get_encoder_name())
                            metrics.set_encoder_revision(config.get_encoder_instance().get_revision())
                            metrics.set_encoder_defines(config.get_encoder_instance().get_defines())
                            metrics.set_encoder_cmdline(param_set.to_cmdline_str())
                            metrics.set_encoding_input(sequence.get_input_filename())
                            metrics.set_encoding_resolution(f"{sequence.width}x{sequence.height}")
                            metrics.set_encoding_time(seconds)
                        else:
                            console_logger.info(f"Tester: Sequence '{sequence.get_input_filename()}'"
                                                f" has already been encoded with configuration '{config.get_name()}'/"
                                                f"{param_set.get_quality_param_name()} {param_set.get_quality_param_value()}"
                                                f" - skipping encoding")
        except Exception as exception:
            self.log_exception(exception)
            exit(1)

    def generate_csv(self, context: TesterContext, csv_filepath: str):
        console_logger.info(f"Generating CSV output file '{csv_filepath}'")
        try:
            csvfile = CsvFile(csv_filepath)
            csvfile.set_header_names([
                "Sequence",
                "Sequence class",
                "Encoder",
                "Revision",
                "Defines",
                "Command line",
                "Quality parameter",
                "Quality parameter value",
                "Configuration name",
                "Anchor name",
                "Time (s)",
                "Speedup",
            ])
            for sequence in context.sequences:
                for config in context.configs:
                    for anchor_name in config.get_anchor_names():
                        anchor_config = context.configs_by_name[anchor_name]
                        for param_set_index in range(len(config.get_encoding_param_sets())):
                            param_set = config.get_encoding_param_sets()[param_set_index]
                            anchor_param_set = anchor_config.get_encoding_param_sets()[param_set_index]
                            metrics = context.metrics[(config, param_set, sequence)]
                            anchor_metrics = context.metrics[(anchor_config), anchor_param_set, sequence]

                            encoding_time = metrics.get_encoding_time()
                            encoding_time = str(encoding_time).replace(".", Cfg().csv_decimal_point)
                            speedup = round(metrics.get_speedup_relative_to(anchor_metrics), 3)
                            speedup = str(speedup).replace(".", Cfg().csv_decimal_point)

                            csvfile.add_entry([
                                sequence.get_input_filename(),
                                sequence.get_class(),
                                config.get_encoder_instance().get_encoder_name(),
                                config.get_encoder_instance().get_short_revision(),
                                config.get_encoder_instance().get_defines(),
                                param_set.to_cmdline_str(),
                                param_set.get_quality_param_name(),
                                param_set.get_quality_param_value(),
                                config.get_name(),
                                anchor_name if anchor_name != config.get_name() else "-",
                                encoding_time,
                                speedup,
                            ])
        except Exception as exception:
            console_logger.error(f"Tester: Failed to create CSV file '{csv_filepath}'")
            self.log_exception(exception)
            exit(1)
