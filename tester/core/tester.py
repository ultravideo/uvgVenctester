from tester.core.cfg import *
from tester.core.csv import *
from tester.core.log import *
from tester.core.testconfig import *
from tester.core import ffmpeg
from tester.encoders.base import *

import subprocess
import time
import traceback


class TesterContext:
    def __init__(self, test_configurations: list, input_sequence_filepaths: list):

        self._configs: list = test_configurations

        self._configs_by_name: dict = {}
        for config in test_configurations:
            self._configs_by_name[config.get_short_name()] = config

        self._sequences: list = []
        for filepath in input_sequence_filepaths:
            self._sequences.append(VideoSequence(filepath))

    def get_configs(self) -> list:
        return self._configs

    def get_configs_by_name(self) -> dict:
        return self._configs_by_name

    def get_sequences(self) -> list:
        return self._sequences

    def validate_bottom(self):
        """Validates everything that can be validated without the encoder binaries
        having been built."""
        for config1 in self._configs:
            for config2 in self._configs:
                if config1 == config2 and not config1 is config2:
                    console_logger.error(f"Tester: Duplicate configurations: "
                                         f"'{config1.get_short_name()}', "
                                         f"'{config2.get_short_name()}'")
                    raise RuntimeError

        for config1 in self._configs:
            for config2 in self._configs:
                if config1.get_short_name() == config2.get_short_name() and config1 is not config2:
                    console_logger.error(f"Tester: Duplicate configuration name "
                                         f"'{config1.get_short_name()}'")
                    raise RuntimeError

        for config in self._configs:
            for anchor_name in config.get_anchor_names():
                if not anchor_name in self._configs_by_name.keys():
                    console_logger.error(f"Tester: Anchor '{anchor_name}' "
                                         f"of configuration '{config.get_short_name()}' "
                                         f"does not exist")
                    raise RuntimeError

    def validate_top(self):
        """Validates everything that can only be validated once the encoder binaries
        have been built."""
        for config in self._configs:
            for param_set in config.get_param_sets():
                if not config.get_encoder().dummy_run(param_set):
                    console_logger.error(f"Tester: Configuration '{config.get_short_name()}' "
                                         f"is invalid")
                    raise RuntimeError


class Tester:
    def __init__(self):
        try:
            console_logger.info("Tester: Initializing")
            Cfg()._read_userconfig()
            Cfg()._validate_all()
            self._create_base_directories_if_not_exist()
        except Exception as exception:
            console_logger.error("Tester: Failed to initialize")
            self._log_exception(exception)
            exit(1)

    def create_context(self,
                       test_configurations: list,
                       input_sequence_filepaths: list) -> TesterContext:
        console_logger.info("Tester: Creating new context")
        try:
            return TesterContext(test_configurations, input_sequence_filepaths)
        except Exception as exception:
            self._log_exception(exception)
            exit(1)

    def run_tests(self, context:TesterContext):

        try:
            console_logger.info(f"Tester: Building encoders")
            context.validate_bottom()
            for config in context.get_configs():
                console_logger.info(f"Tester: Building encoder for configuration '{config.get_short_name()}'")
                config.get_encoder().build()
                config.get_encoder().clean()
            context.validate_top()

            for sequence in context.get_sequences():
                for config in context.get_configs():
                    for param_set in config.get_param_sets():
                        self._run_subtest(config, param_set, sequence)

        except Exception as exception:
            console_logger.error(f"Tester: Failed to run tests")
            self._log_exception(exception)
            exit(1)

    def compute_metrics(self, context: TesterContext):

        try:
            for sequence in context.get_sequences():
                for config in context.get_configs():
                    metrics = config.get_metrics(sequence)
                    for param_set_index in range(len(config.get_param_sets())):
                        param_set = config.get_param_sets()[param_set_index]

                        console_logger.info(f"Tester: Computing metrics")
                        console_logger.info(f"Tester: Sequence: '{sequence.get_input_filename()}'")
                        console_logger.info(f"Tester: Test: '{config.get_long_name(param_set)}'")

                        metrics_file = metrics.get_metrics_file(param_set)

                        psnr, ssim = ffmpeg.compute_psnr_and_ssim(
                            sequence.get_input_filepath(),
                            sequence.get_output_filepath(config.get_encoder(), param_set),
                            sequence.get_width(),
                            sequence.get_height(),
                        )

                        metrics_file.set_psnr_avg(psnr)
                        metrics_file.set_ssim_avg(ssim)

        except Exception as exception:
            console_logger.error(f"Tester: Failed to compute metrics")
            if isinstance(exception, subprocess.CalledProcessError):
                console_logger.error(exception.output.decode())
            self._log_exception(exception)
            exit(1)

    def generate_csv(self, context: TesterContext, csv_filepath: str):

        console_logger.info(f"Tester: Generating CSV file '{csv_filepath}'")

        try:
            csvfile = CsvFile(filepath=csv_filepath)

            for sequence in context.get_sequences():
                for config in context.get_configs():
                    metrics = config.get_metrics(sequence)
                    for anchor_name in config.get_anchor_names():
                        anchor_config = context.get_configs_by_name()[anchor_name]
                        anchor_metrics = anchor_config.get_metrics(sequence)
                        for param_set_index in range(len(config.get_param_sets())):

                            param_set = config.get_param_sets()[param_set_index]
                            metrics_file = metrics.get_metrics_file(param_set)

                            anchor_param_set = anchor_config.get_param_sets()[param_set_index]
                            anchor_metrics_file = anchor_metrics.get_metrics_file(anchor_param_set)

                            csvfile.add_entry({
                                CsvFieldId.SEQUENCE_NAME: sequence.get_input_filename(),
                                CsvFieldId.SEQUENCE_CLASS: sequence.get_sequence_class(),
                                CsvFieldId.SEQUENCE_FRAMECOUNT: sequence.get_framecount(),
                                CsvFieldId.ENCODER_NAME: config.get_encoder().get_name(),
                                CsvFieldId.ENCODER_REVISION: config.get_encoder().get_short_revision(),
                                CsvFieldId.ENCODER_DEFINES: config.get_encoder().get_defines(),
                                CsvFieldId.ENCODER_CMDLINE: param_set.to_cmdline_str(),
                                CsvFieldId.QUALITY_PARAM_NAME: param_set.get_quality_param_name(),
                                CsvFieldId.QUALITY_PARAM_VALUE: param_set.get_quality_param_value(),
                                CsvFieldId.CONFIG_NAME: config.get_short_name(),
                                CsvFieldId.ANCHOR_NAME: anchor_config.get_short_name(),
                                CsvFieldId.TIME_SECONDS: metrics_file.get_encoding_time(),
                                CsvFieldId.SPEEDUP: metrics_file.get_speedup_relative_to(anchor_metrics_file),
                                CsvFieldId.PSNR_AVG: metrics_file.get_psnr_avg(),
                                CsvFieldId.SSIM_AVG: metrics_file.get_ssim_avg(),
                                CsvFieldId.BDBR_PSNR: metrics.get_bdbr_psnr(anchor_metrics),
                                CsvFieldId.BDBR_SSIM: metrics.get_bdbr_ssim(anchor_metrics),
                            })

        except Exception as exception:
            console_logger.error(f"Tester: Failed to generate CSV file '{csv_filepath}'")
            self._log_exception(exception)
            exit(1)

    def _run_subtest(self,
                     config: TestConfig,
                     param_set: ParamSetBase,
                     sequence: VideoSequence):
        console_logger.info(f"Tester: Running test '{config.get_long_name(param_set)}' "
                            f"for sequence '{sequence.get_input_filename()}'")

        try:
            metrics_file = config.get_metrics(sequence).get_metrics_file(param_set)

            if not metrics_file.exists():
                start_time: float = time.perf_counter()
                config.get_encoder().encode(sequence, param_set)
                seconds: float = round(time.perf_counter() - start_time, 6)

                metrics_file.set_encoder_name(config.get_encoder().get_name())
                metrics_file.set_encoder_revision(config.get_encoder().get_revision())
                metrics_file.set_encoder_defines(config.get_encoder().get_defines())
                metrics_file.set_encoder_cmdline(param_set.to_cmdline_str())
                metrics_file.set_encoding_input(sequence.get_input_filename())
                metrics_file.set_encoding_resolution(f"{sequence.width}x{sequence.height}")
                metrics_file.set_encoding_time(seconds)
            else:
                console_logger.info(f"Tester: File "
                                    f"'{sequence.get_output_filename(config.get_encoder(), param_set)}' "
                                    f"already exists")
        except Exception as exception:
            console_logger.error(f"Tester: Test failed")
            self._log_exception(exception)
            exit(1)

    def _create_base_directories_if_not_exist(self):
        for path in Cfg().binaries_dir_path,\
                    Cfg().encoding_output_dir_path,\
                    Cfg().sources_dir_path:
            if not os.path.exists(path):
                console_logger.debug(f"Tester: Creating directory '{path}'")
                try:
                    os.makedirs(path)
                except Exception as exception:
                    console_logger.error(f"Tester: Failed to create directory '{path}'")
                    self._log_exception(exception)
                    exit(1)

    def _log_exception(self, exception: Exception):
        console_logger.error(f"Tester: An exception of type '{type(exception).__name__}' was caught: "
                             f"{str(exception)}")
        console_logger.error(f"Tester: {traceback.format_exc()}")
