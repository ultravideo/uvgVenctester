from .cfg import *
from .csvfile import *
from .metrics import *
from .testercontext import *
from . import ffmpeg
import test

import subprocess
import time
import traceback

class Tester:
    def __init__(self):
        Cfg()._read_userconfig()
        Cfg()._validate_all()
        self.create_base_directories_if_not_exist()

    def create_context(self, test_configurations: list, input_sequence_filepaths: list) -> TesterContext:
        # TODO: Copy by value, not by reference.
        context: TesterContext = TesterContext()
        context.configs = test_configurations

        for config in test_configurations:
            context.configs_by_name[config.get_short_name()] = config

        for filepath in input_sequence_filepaths:
            context.sequences.append(VideoSequence(filepath))

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
                                         f" '{config1.get_short_name()}', '{config2.get_short_name()}'")
                    raise RuntimeError

        for config1 in context.configs:
            for config2 in context.configs:
                if config1.get_short_name() == config2.get_short_name() and config1 is not config2:
                    console_logger.error(f"Tester: Duplicate configuration name '{config1.get_short_name()}'")
                    raise RuntimeError

        for config in context.configs:
            for anchor_name in config.get_anchor_names():
                if not anchor_name in context.configs_by_name.keys():
                    console_logger.error(f"Tester: Anchor '{anchor_name}'"
                                         f" of configuration '{config.get_short_name()}' does not exist")
                    raise RuntimeError

    def validate_context_top(self, context: TesterContext):
        for config in context.configs:
            for param_set in config.get_param_sets():
                if not config.get_encoder().dummy_run(param_set):
                    console_logger.error(f"Tester: Configuration '{config.get_short_name()}' is invalid")
                    raise RuntimeError

    def create_base_directories_if_not_exist(self):
        for path in Cfg().binaries_dir_path,\
                    Cfg().encoding_output_dir_path,\
                    Cfg().sources_dir_path:
            if not os.path.exists(path):
                console_logger.debug(f"Tester: Creating directory '{path}'")
                os.makedirs(path)

    def run_tests(self, context:TesterContext):
        try:
            self.validate_context_bottom(context)
            self.create_base_directories_if_not_exist()

            for config in context.configs:
                config.get_encoder().build()

            self.validate_context_top(context)

            for config in context.configs:
                for param_set in config.get_param_sets():
                    for sequence in context.sequences:
                        console_logger.debug(f"Tester: Encoding sequence '{sequence.get_input_filename()}' with configuration '{config.get_long_name(param_set)}'")
                        metrics_file = config.get_metrics(sequence).get_metrics_file(param_set)
                        if not metrics_file.exists():
                            start_time: float = time.perf_counter()
                            config.get_encoder().encode(sequence, param_set)
                            seconds: float = round(time.perf_counter() - start_time, 6)
                            metrics_file.set_encoder_name(config.get_encoder().get_encoder_name())
                            metrics_file.set_encoder_revision(config.get_encoder().get_revision())
                            metrics_file.set_encoder_defines(config.get_encoder().get_defines())
                            metrics_file.set_encoder_cmdline(param_set.to_cmdline_str())
                            metrics_file.set_encoding_input(sequence.get_input_filename())
                            metrics_file.set_encoding_resolution(f"{sequence.width}x{sequence.height}")
                            metrics_file.set_encoding_time(seconds)
                        else:
                            console_logger.info(f"Tester: Sequence '{sequence.get_input_filename(param_set)}'"
                                                f" has already been encoded with configuration '{config.get_long_name(param_set)}'"
                                                f" - skipping encoding")
        except Exception as exception:
            self.log_exception(exception)
            exit(1)

    def compute_metrics(self, context: TesterContext):
        for sequence in context.sequences:
            for config in context.configs:
                metrics = config.get_metrics(sequence)
                for param_set_index in range(len(config.get_param_sets())):
                    param_set = config.get_param_sets()[param_set_index]
                    metrics_file = metrics.get_metrics_file(param_set)

                    console_logger.debug(f"Tester: Computing metrics for configuration"
                                         f" '{config.get_long_name(param_set)}'")

                    try:
                        psnr, ssim = ffmpeg.compute_psnr_and_ssim(
                            sequence.get_input_filepath(),
                            sequence.get_output_filepath(config.get_encoder(), param_set),
                            sequence.get_width(),
                            sequence.get_height(),
                        )

                        metrics_file.set_psnr_avg(psnr)
                        metrics_file.set_ssim_avg(ssim)

                    except Exception as exception:
                        console_logger.error(f"Tester: Failed to compute metrics for configuration"
                                             f" '{config.get_long_name(param_set)}'")
                        if isinstance(exception, subprocess.CalledProcessError):
                            console_logger.error(exception.output.decode())
                        self.log_exception(exception)
                        exit(1)

    def generate_csv(self, context: TesterContext, csv_filepath: str):
        console_logger.info(f"Generating CSV output file '{csv_filepath}'")

        try:
            csvfile = CsvFile(filepath=csv_filepath,
                              field_names=[
                                  "Sequence",
                                  "Sequence class",
                                  "Frames",
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
                                  "PSNR average",
                                  "SSIM average",
                                  "PSNR BD-BR",
                                  "SSIM BD-BR",
                            ],
            )

            for sequence in context.sequences:
                for config in context.configs:
                    metrics = config.get_metrics(sequence)
                    for anchor_name in config.get_anchor_names():
                        anchor_config = context.configs_by_name[anchor_name]
                        anchor_metrics = anchor_config.get_metrics(sequence)
                        for param_set_index in range(len(config.get_param_sets())):

                            param_set = config.get_param_sets()[param_set_index]
                            metrics_file = metrics.get_metrics_file(param_set)

                            anchor_param_set = anchor_config.get_param_sets()[param_set_index]
                            anchor_metrics_file = anchor_metrics.get_metrics_file(anchor_param_set)

                            encoding_time = metrics_file.get_encoding_time()
                            encoding_time = str(encoding_time).replace(".", Cfg().csv_decimal_point)
                            speedup = round(metrics_file.get_speedup_relative_to(anchor_metrics_file), 3)
                            speedup = str(speedup).replace(".", Cfg().csv_decimal_point)
                            psnr_avg = round(metrics_file.get_psnr_avg(), 3)
                            psnr_avg = str(psnr_avg).replace(".", Cfg().csv_decimal_point)
                            ssim_avg = round(metrics_file.get_ssim_avg(), 3)
                            ssim_avg = str(ssim_avg).replace(".", Cfg().csv_decimal_point)

                            psnr_bdbr = round(metrics.get_bdbr_psnr(anchor_metrics), 6)
                            psnr_bdbr = str(psnr_bdbr).replace(".", Cfg().csv_decimal_point)
                            ssim_bdbr = round(metrics.get_bdbr_ssim(anchor_metrics), 6)
                            ssim_bdbr = str(ssim_bdbr).replace(".", Cfg().csv_decimal_point)

                            csvfile.new_row([
                                sequence.get_input_filename(),
                                sequence.get_sequence_class(),
                                sequence.get_framecount(),
                                config.get_encoder().get_encoder_name(),
                                config.get_encoder().get_short_revision(),
                                config.get_encoder().get_defines(),
                                param_set.to_cmdline_str(),
                                param_set.get_quality_param_name(),
                                param_set.get_quality_param_value(),
                                config.get_short_name(),
                                anchor_name if anchor_name != config.get_short_name() else "-",
                                encoding_time,
                                speedup,
                                psnr_avg,
                                ssim_avg,
                                psnr_bdbr,
                                ssim_bdbr,
                            ])

        except Exception as exception:
            console_logger.error(f"Tester: Failed to create CSV file '{csv_filepath}'")
            self.log_exception(exception)
            exit(1)
