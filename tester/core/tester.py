"""This module defines functionality related to testing."""
import subprocess
import time
from pathlib import Path
from typing import Iterable
from multiprocessing import Pool

import tester
import tester.core.cmake as cmake
from tester.core import gcc, ffmpeg, system, vmaf, csv, git, vs
from tester.core.cfg import Cfg
from tester.core.log import console_log, log_exception
from tester.core.metrics import TestMetrics
from tester.core.test import Test, EncodingRun
from tester.core.video import RawVideoSequence


class TesterContext:
    """Contains the state of the tester. The intention is to make the Tester class itself
    stateless for flexibility."""

    def __init__(self,
                 tests: Iterable,
                 input_sequence_globs: list):

        self._tests: list = list(tests)

        self._tests_by_name: dict = {test.name: test for test in self._tests}

        self._input_sequences: list = []
        for glob in input_sequence_globs:
            for filepath in Cfg().tester_sequences_dir_path.glob(glob):
                self._input_sequences.append(
                    RawVideoSequence(
                        filepath=filepath.resolve(),
                    )
                )
        self._metrics: dict = {test.name: TestMetrics(test, self._input_sequences) for test in self._tests}

    def get_tests(self) -> Iterable:
        return self._tests

    def get_metrics(self) -> dict:
        return self._metrics

    def get_test(self,
                 test_name: str) -> Test:
        assert test_name in self._tests_by_name.keys()
        return self._tests_by_name[test_name]

    def get_input_sequences(self) -> list:
        return self._input_sequences

    def validate_initial(self) -> None:
        """Validates everything that can be validated without the encoder binaries
        having been built."""
        for test1 in self._tests:
            for test2 in self._tests:
                if test1 == test2 and test1 is not test2:
                    console_log.error(f"Tester: Duplicate tests: "
                                      f"'{test1.name}', "
                                      f"'{test2.name}'")
                    raise RuntimeError

        for test1 in self._tests:
            for test2 in self._tests:
                if test1.name == test2.name and test1 is not test2:
                    console_log.error(f"Tester: Duplicate test name "
                                      f"'{test1.name}'")
                    raise RuntimeError

        for test in self._tests:
            for anchor_name in test.anchor_names:
                if anchor_name not in self._tests_by_name.keys():
                    console_log.error(f"Tester: Anchor '{anchor_name}' "
                                      f"of test '{test.name}' "
                                      f"does not exist")
                    raise RuntimeError

    def validate_final(self) -> None:
        """Validates everything that can only be validated once the encoder binaries
        have been built."""
        for test in self._tests:
            for subtest in test.subtests:
                if not subtest.encoder.dummy_run(subtest.param_set):
                    console_log.error(f"Tester: Test '{test.name}' "
                                      f"is invalid")
                    raise RuntimeError


class Tester:
    """Represents the tester. The end user primarily interacts with this class."""

    @staticmethod
    def create_context(tests: Iterable,
                       input_sequence_globs: list) -> TesterContext:

        console_log.info("Tester: Creating context")

        try:
            context = TesterContext(tests, input_sequence_globs)
        except Exception as exception:
            console_log.error("Tester: Failed to create context")
            log_exception(exception)
            exit(1)

        try:
            console_log.info("Tester: Validating configuration variables")

            # Test the validity of external tools first because the validation of internal
            # stuff might depend on these (for example Git remote existence checking).
            system.system_validate_config()
            git.git_validate_config()
            cmake.cmake_validate_config()
            gcc.gcc_validate_config()
            # ffmpeg.ffmpeg_validate_config()
            vmaf.vmaf_validate_config()
            vs.vs_validate_config()

            csv.csv_validate_config()

            # Only validate those encoders that are being used.
            for test in context.get_tests():
                test.encoder.validate_config(test)

        except Exception as exception:
            console_log.error("Tester: Configuration variable validation failed")
            log_exception(exception)
            exit(1)

        return context

    def run_tests(self,
                  context: TesterContext,
                  parallel_runs: int = 1) -> None:

        try:
            self._create_base_directories_if_not_exist()

            console_log.info(f"Tester: Building encoders")
            context.validate_initial()
            for test in context.get_tests():
                console_log.info(f"Tester: Building encoder for test '{test.name}'")
                test.encoder.build()
                # TODO: Don't clean if the encoder wasn't built. This is slow for HM, at least.
                if not test.encoder._use_prebuilt:
                    test.encoder.clean()
            context.validate_final()

            encoding_runs = []

            for sequence in context.get_input_sequences():
                for test in context.get_tests():
                    for subtest in test.subtests:
                        for round_ in range(1, test.rounds + 1):
                            name = f"{subtest.name}/{sequence.get_filepath().name} ({round_}/{test.rounds})"
                            encoding_runs.append(
                                EncodingRun(
                                    subtest,
                                    name,
                                    round_,
                                    test.encoder,
                                    subtest.param_set,
                                    sequence
                                )
                            )

            if parallel_runs > 1:
                with Pool(parallel_runs) as p:
                    p.map(Tester._do_encoding_run, encoding_runs)
            else:
                for encoding_run in encoding_runs:
                    self._do_encoding_run(encoding_run)

        except Exception as exception:
            console_log.error(f"Tester: Failed to run tests")
            log_exception(exception)
            exit(1)

    def compute_metrics(self,
                        context: TesterContext,
                        parallel_calculations: int = 1) -> None:

        values = []
        parallel_calculations = max(parallel_calculations, 1)
        for sequence in context.get_input_sequences():
            for test in context.get_tests():
                for subtest in test.subtests:
                    for round_ in range(1, test.rounds + 1):
                        name = f"{subtest.name}/{sequence.get_filepath().name} ({round_}/{test.rounds})"
                        encoding_run = EncodingRun(
                            subtest,
                            name,
                            round_,
                            test.encoder,
                            subtest.param_set,
                            sequence
                        )

                        metric = encoding_run.metrics
                        psnr_needed = "psnr" not in metric \
                                      and (csv.CsvField.PSNR_AVG in Cfg().csv_enabled_fields
                                           or csv.CsvField.PSNR_STDEV in Cfg().csv_enabled_fields
                                           or csv.CsvField.BDBR_PSNR in Cfg().csv_enabled_fields)
                        ssim_needed = "ssim" not in metric \
                                      and (csv.CsvField.SSIM_AVG in Cfg().csv_enabled_fields
                                           or csv.CsvField.SSIM_STDEV in Cfg().csv_enabled_fields
                                           or csv.CsvField.BDBR_SSIM in Cfg().csv_enabled_fields)
                        vmaf_needed = "vmaf" not in metric \
                                      and (csv.CsvField.VMAF_AVG in Cfg().csv_enabled_fields
                                           or csv.CsvField.VMAF_STDEV in Cfg().csv_enabled_fields
                                           or csv.CsvField.BDBR_VMAF in Cfg().csv_enabled_fields)
                        arguments = (encoding_run, metric, psnr_needed, ssim_needed, vmaf_needed)
                        if parallel_calculations > 1:
                            values.append(arguments)
                        else:
                            self._calculate_metrics_for_one_run(arguments)

        if parallel_calculations > 1:
            with Pool(parallel_calculations) as p:
                p.map(Tester._calculate_metrics_for_one_run, values)

    @staticmethod
    def _calculate_metrics_for_one_run(in_args):
        encoding_run, metrics, psnr_needed, ssim_needed, vmaf_needed = in_args
        try:
            console_log.info(f"Tester: Computing metrics for '{encoding_run.name}'")

            metrics["bitrate"] = encoding_run.output_file.get_bitrate()
            if encoding_run.qp_name != tester.QualityParam.QP:
                metrics["target_bitrate"] = encoding_run.qp_value

            if psnr_needed or ssim_needed or vmaf_needed:
                psnr_avg, ssim_avg, vmaf_avg = ffmpeg.compute_metrics(
                    encoding_run,
                    psnr=psnr_needed,
                    ssim=ssim_needed,
                    vmaf=vmaf_needed
                )
                if psnr_needed:
                    metrics["psnr"] = psnr_avg
                if ssim_needed:
                    metrics["ssim"] = ssim_avg
                if vmaf_needed:
                    metrics["vmaf"] = vmaf_avg
            else:
                console_log.info(f"Tester: Metrics for '{encoding_run.name}' already exist")

        except Exception as exception:
            console_log.error(f"Tester: Failed to compute metrics for '{encoding_run.name}'")
            if isinstance(exception, subprocess.CalledProcessError):
                console_log.error(exception.output.decode())
            log_exception(exception)
            console_log.info(f"Tester: Ignoring error")

    @staticmethod
    def generate_csv(context: TesterContext,
                     csv_filepath: str) -> None:

        console_log.info(f"Tester: Generating CSV file '{csv_filepath}'")
        metrics = context.get_metrics()

        try:
            csvfile = csv.CsvFile(filepath=Path(csv_filepath))

            for sequence in context.get_input_sequences():
                for test in context.get_tests():
                    for anchor in [context.get_test(name) for name in test.anchor_names]:
                        for i, subtest in enumerate(test.subtests):

                            try:
                                Tester.__add_csv_line(anchor, csvfile, sequence, subtest, test, metrics)

                            except Exception as exception:
                                console_log.error(f"Tester: Failed to add CSV entry for "
                                                  f"'{subtest.name}/{sequence.get_filepath().name}'")
                                log_exception(exception)
                                console_log.info(f"Tester: Ignoring error")

        except Exception as exception:
            console_log.error(f"Tester: Failed to generate CSV file '{csv_filepath}'")
            log_exception(exception)
            exit(1)

    @staticmethod
    def __add_csv_line(anchor, csvfile, sequence, subtest, test, metrics):
        console_log.info(f"Tester: Adding CSV entry for "
                         f"'{subtest.name}/{sequence.get_filepath().name}'")
        metric = metrics[test.name][sequence][subtest.param_set.get_quality_param_value()]
        anchor_metric = metrics[anchor.name][sequence][subtest.param_set.get_quality_param_value()]
        csvfile.add_entry(
            {
                csv.CsvField.SEQUENCE_NAME: lambda: sequence.get_filepath().name,
                csv.CsvField.SEQUENCE_CLASS: lambda: sequence.get_sequence_class(),
                csv.CsvField.SEQUENCE_FRAMECOUNT: lambda: sequence.get_framecount(),
                csv.CsvField.ENCODER_NAME: lambda: test.encoder.get_pretty_name(),
                csv.CsvField.ENCODER_REVISION: lambda: test.encoder.get_short_revision(),
                csv.CsvField.ENCODER_DEFINES: lambda: test.encoder.get_defines(),
                csv.CsvField.ENCODER_CMDLINE: lambda: subtest.param_set.to_cmdline_str(),
                csv.CsvField.QUALITY_PARAM_NAME: lambda: subtest.param_set.get_quality_param_type().pretty_name,
                csv.CsvField.QUALITY_PARAM_VALUE: lambda: subtest.param_set.get_quality_param_value()
                if "target_bitrate_avg" not in metric
                else metric["target_bitrate_avg"],
                csv.CsvField.CONFIG_NAME: lambda: test.name,
                csv.CsvField.ANCHOR_NAME: lambda: anchor.name,
                csv.CsvField.TIME_SECONDS: lambda: metric["encoding_time_avg"],
                csv.CsvField.TIME_STDEV: lambda: metric["encoding_time_stdev"],
                csv.CsvField.BITRATE: lambda: metric["bitrate_avg"],
                csv.CsvField.BITRATE_STDEV: lambda: metric["bitrate_stdev"],
                csv.CsvField.SPEEDUP: lambda: metric.speedup(anchor_metric),
                csv.CsvField.PSNR_AVG: lambda: metric["psnr_avg"],
                csv.CsvField.PSNR_STDEV: lambda: metric["psnr_stdev"],
                csv.CsvField.SSIM_AVG: lambda: metric["ssim_avg"],
                csv.CsvField.SSIM_STDEV: lambda: metric["ssim_stdev"],
                csv.CsvField.VMAF_AVG: lambda: metric["vmaf_avg"],
                csv.CsvField.VMAF_STDEV: lambda: metric["vmaf_stdev"],
                csv.CsvField.BDBR_PSNR: lambda: metrics[test.name][sequence].compute_bdbr_to_anchor(
                    metrics[anchor.name][sequence], "psnr"),
                csv.CsvField.BDBR_SSIM: lambda: metrics[test.name][sequence].compute_bdbr_to_anchor(
                    metrics[anchor.name][sequence], "ssim"),
                csv.CsvField.BDBR_VMAF: lambda: metrics[test.name][sequence].compute_bdbr_to_anchor(
                    metrics[anchor.name][sequence], "vmaf"),
                csv.CsvField.BITRATE_ERROR: lambda: -1 + metric["bitrate_avg"] / metric[
                    "target_bitrate_avg"] if "target_bitrate_avg" in metric else "-"
            }
        )

    @staticmethod
    def _do_encoding_run(encoding_run: EncodingRun) -> None:

        console_log.info(f"Tester: Running '{encoding_run.name}'")

        try:
            if not encoding_run.output_file.get_filepath().exists() or \
                    "encoding_time" not in encoding_run.metrics:

                start_time: float = time.perf_counter()
                encoding_run.encoder.encode(encoding_run)
                encoding_time_seconds: float = round(time.perf_counter() - start_time, 6)

                encoding_run.metrics.clear()
                encoding_run.metrics["encoding_time"] = encoding_time_seconds
            else:
                console_log.info(f"Tester: Encoding output for '{encoding_run.name}' already exists")

        except Exception as exception:
            console_log.error(f"Tester: Test failed")
            log_exception(exception)
            exit(1)

    @staticmethod
    def _create_base_directories_if_not_exist() -> None:
        for path in [
            Cfg().tester_binaries_dir_path,
            Cfg().tester_output_dir_path,
            Cfg().tester_sources_dir_path
        ]:
            if not path.exists():
                console_log.debug(f"Tester: Creating directory '{path}'")
                try:
                    path.mkdir(parents=True)
                except Exception as exception:
                    console_log.error(f"Tester: Failed to create directory '{path}'")
                    log_exception(exception)
                    exit(1)
