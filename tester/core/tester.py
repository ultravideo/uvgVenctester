from .cfg import *
from .csvfile import *
from .metrics import *
from .testercontext import *
import test

import subprocess
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

    def compute_results(self, context: TesterContext):
        for sequence in context.sequences:
            for config in context.configs:
                for param_set_index in range(len(config.get_encoding_param_sets())):
                    param_set = config.get_encoding_param_sets()[param_set_index]
                    encoder_instance: test.EncoderInstanceBase = config.get_encoder_instance()
                    metrics: Metrics = context.metrics[(config, param_set, sequence)]
                    ssim_log_filename = sequence.get_ssim_log_filename(encoder_instance, param_set)
                    psnr_log_filename = sequence.get_psnr_log_filename(encoder_instance, param_set)
                    ffmpeg_command: tuple = (
                        "(", "cd", encoder_instance.get_output_subdir(param_set),
                             "&&", "ffmpeg",
                                   "-pix_fmt", "yuv420p",
                                   "-r", "25",
                                   "-s:v", f"{sequence.get_width()}x{sequence.get_height()}",
                                   "-i", sequence.get_input_filepath(),
                                   "-r", "25",
                                   "-i", sequence.get_output_filepath(encoder_instance, param_set),
                                   "-c:v", "rawvideo",

                                   "-filter_complex", f"[0:v]split=2[in1_1][in1_2];"
                                                      f"[1:v]split=2[in2_1][in2_2];"
                                                      f"[in2_1][in1_1]ssim=stats_file={ssim_log_filename};"
                                                      f"[in2_2][in1_2]psnr=stats_file={psnr_log_filename}",
                                   "-f",  "null", "-",
                             "&&", "exit", "0"
                        ")", "||", "exit", "1"
                    )

                    try:
                        console_logger.debug(f"Tester: Computing metrics for configuration"
                                             f" '{config.get_name()}'/"
                                             f"{param_set.get_quality_param_name()} {param_set.get_quality_param_value()}")
                        subprocess.check_output(ffmpeg_command, stderr=subprocess.STDOUT, shell=True)

                        psnr_log_filepath: str = sequence.get_psnr_log_filepath(encoder_instance, param_set)
                        ssim_log_filepath: str = sequence.get_ssim_log_filepath(encoder_instance, param_set)

                        # TODO: Eliminate duplicate code?

                        with open(psnr_log_filepath, "r") as psnr_log_file:
                            psnr_avg: float = 0
                            line_count: int = 0
                            pattern = re.compile(r".*psnr_avg:([0-9]+.[0-9]+).*", re.DOTALL)
                            for line in psnr_log_file.readlines():
                                line_count += 1
                                for item in pattern.fullmatch(line).groups():
                                    psnr_avg += float(item)
                            psnr_avg /= line_count
                            metrics.set_psnr_avg(psnr_avg)

                        with open(ssim_log_filepath, "r") as ssim_log_file:
                            ssim_avg: float = 0
                            line_count: int = 0
                            pattern = re.compile(r".*All:([0-9]+.[0-9]+).*", re.DOTALL)
                            for line in ssim_log_file.readlines():
                                line_count += 1
                                for item in pattern.fullmatch(line).groups():
                                    ssim_avg += float(item)
                            ssim_avg /= line_count
                            metrics.set_ssim_avg(ssim_avg)

                    except Exception as exception:
                        console_logger.error(f"Tester: Failed to compute metrics for configuration"
                                             f" '{config.get_name()}'/"
                                             f"{param_set.get_quality_param_name()} {param_set.get_quality_param_value()}")
                        if isinstance(exception, subprocess.CalledProcessError):
                            console_logger.error(exception.output.decode())
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
                "PSNR average",
                "SSIM average",
                "PSNR BD-BR",
                "SSIM BD-BR",
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
                            psnr_avg = round(metrics.get_psnr_avg(), 3)
                            psnr_avg = str(psnr_avg).replace(".", Cfg().csv_decimal_point)
                            ssim_avg = round(metrics.get_ssim_avg(), 3)
                            ssim_avg = str(ssim_avg).replace(".", Cfg().csv_decimal_point)
                            psnr_bdbr = round(metrics.get_psnr_bdbr(config, anchor_config, sequence), 6)
                            psnr_bdbr = str(psnr_bdbr).replace(".", Cfg().csv_decimal_point)
                            ssim_bdbr = round(metrics.get_ssim_bdbr(config, anchor_config, sequence), 6)
                            ssim_bdbr = str(ssim_bdbr).replace(".", Cfg().csv_decimal_point)

                            csvfile.add_entry([
                                sequence.get_input_filename(),
                                sequence.get_sequence_class(),
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
                                psnr_avg,
                                ssim_avg,
                                psnr_bdbr,
                                ssim_bdbr,
                            ])

        except Exception as exception:
            console_logger.error(f"Tester: Failed to create CSV file '{csv_filepath}'")
            self.log_exception(exception)
            exit(1)
