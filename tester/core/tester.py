"""This module defines functionality related to testing."""

from tester.core.cfg import *
from tester.core.csv import *
from tester.core.log import *
from tester.core.test import *
from tester.core import ffmpeg
from tester.encoders.base import *

import subprocess
import time
import traceback
from pathlib import Path


class TesterContext:
    """Contains the state of the tester. The intention is to make the Tester class itself
    stateless for flexibility."""

    def __init__(self,
                 tests: list,
                 input_sequence_globs: list):

        self._tests: list = tests

        self._tests_by_name: dict = {}
        for test in tests:
            self._tests_by_name[test.get_name()] = test

        self._input_sequences: list = []
        for glob in input_sequence_globs:
            for filepath in Cfg().sequences_dir_path.glob(glob):
                self._input_sequences.append(
                    RawVideoSequence(
                        filepath=filepath.resolve(),
                        # TODO: Figure out a better way to do this.
                        seek=self._tests[0].get_subtests()[0].get_param_set().get_seek(),
                        frames=self._tests[0].get_subtests()[0].get_param_set().get_frames(),
                    )
                )

    def get_tests(self) -> list:
        return self._tests

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
                if test1 == test2 and not test1 is test2:
                    console_log.error(f"Tester: Duplicate tests: "
                                         f"'{test1.get_name()}', "
                                         f"'{test2.get_name()}'")
                    raise RuntimeError

        for test1 in self._tests:
            for test2 in self._tests:
                if test1.get_name() == test2.get_name() and test1 is not test2:
                    console_log.error(f"Tester: Duplicate test name "
                                         f"'{test1.get_name()}'")
                    raise RuntimeError

        for test in self._tests:
            for anchor_name in test.get_anchor_names():
                if not anchor_name in self._tests_by_name.keys():
                    console_log.error(f"Tester: Anchor '{anchor_name}' "
                                         f"of test '{test.get_name()}' "
                                         f"does not exist")
                    raise RuntimeError

    def validate_final(self) -> None:
        """Validates everything that can only be validated once the encoder binaries
        have been built."""
        for test in self._tests:
            for subtest in test.get_subtests():
                if not test.get_encoder().dummy_run(subtest.get_param_set()):
                    console_log.error(f"Tester: Test '{test.get_name()}' "
                                         f"is invalid")
                    raise RuntimeError


class Tester:
    """The tester class the methods of which the user will call."""

    def __init__(self):
        try:
            console_log.info("Tester: Initializing")
            Cfg().read_userconfig()
            Cfg().validate_all()
            self._create_base_directories_if_not_exist()
        except Exception as exception:
            console_log.error("Tester: Failed to initialize")
            self._log_exception(exception)
            exit(1)

    def create_context(self,
                       tests: list,
                       input_sequence_globs: list) -> TesterContext:
        console_log.info("Tester: Creating context")
        try:
            return TesterContext(tests, input_sequence_globs)
        except Exception as exception:
            console_log.info("Tester: Failed to create context")
            self._log_exception(exception)
            exit(1)

    def run_tests(self,
                  context:TesterContext) -> None:

        try:
            console_log.info(f"Tester: Building encoders")
            context.validate_initial()
            for test in context.get_tests():
                console_log.info(f"Tester: Building encoder for test '{test.get_name()}'")
                test.get_encoder().build()
                test.get_encoder().clean()
            context.validate_final()

            for sequence in context.get_input_sequences():
                for test in context.get_tests():
                    for subtest in test.get_subtests():
                        self._run_subtest(subtest, sequence)

        except Exception as exception:
            console_log.error(f"Tester: Failed to run tests")
            self._log_exception(exception)
            exit(1)

    def compute_metrics(self,
                        context: TesterContext) -> None:
        try:
            for sequence in context.get_input_sequences():
                for test in context.get_tests():
                    for subtest in test.get_subtests():

                        console_log.info(f"Tester: Computing metrics")
                        console_log.info(f"Tester: Sequence: '{sequence.get_filepath().name}'")
                        console_log.info(f"Tester: Subtest: '{subtest.get_name()}'")

                        psnr_avg, ssim_avg = ffmpeg.compute_psnr_and_ssim(
                            sequence,
                            test.get_encoder().get_output_file(sequence, subtest.get_param_set())
                        )
                        subtest.get_metrics(sequence).set_psnr_avg(psnr_avg)
                        subtest.get_metrics(sequence).set_ssim_avg(ssim_avg)

        except Exception as exception:
            console_log.error(f"Tester: Failed to compute metrics")
            if isinstance(exception, subprocess.CalledProcessError):
                console_log.error(exception.output.decode())
            self._log_exception(exception)
            exit(1)

    def generate_csv(self,
                     context: TesterContext,
                     csv_filepath: str) -> None:

        console_log.info(f"Tester: Generating CSV file '{csv_filepath}'")

        try:
            csvfile = CsvFile(filepath=Path(csv_filepath))

            for sequence in context.get_input_sequences():
                for test in context.get_tests():
                    for anchor_test in [context.get_test(name) for name in test.get_anchor_names()]:
                        for subtest_index, subtest in enumerate(test.get_subtests()):

                            anchor_subtest = anchor_test.get_subtests()[subtest_index]

                            test_metrics = test.get_metrics(sequence)
                            subtest_metrics = subtest.get_metrics(sequence)

                            anchor_test_metrics = anchor_test.get_metrics(sequence)
                            anchor_subtest_metrics = anchor_subtest.get_metrics(sequence)

                            encoder = subtest.get_encoder()
                            param_set = subtest.get_param_set()

                            csvfile.add_entry(
                                {
                                    CsvFieldId.SEQUENCE_NAME: sequence.get_filepath().name,
                                    CsvFieldId.SEQUENCE_CLASS: sequence.get_sequence_class(),
                                    CsvFieldId.SEQUENCE_FRAMECOUNT: sequence.get_framecount(),
                                    CsvFieldId.ENCODER_NAME: encoder.get_name(),
                                    CsvFieldId.ENCODER_REVISION: encoder.get_short_revision(),
                                    CsvFieldId.ENCODER_DEFINES: encoder.get_defines(),
                                    CsvFieldId.ENCODER_CMDLINE: param_set.to_cmdline_str(),
                                    CsvFieldId.QUALITY_PARAM_NAME: param_set.get_quality_param_name(),
                                    CsvFieldId.QUALITY_PARAM_VALUE: param_set.get_quality_param_value(),
                                    CsvFieldId.CONFIG_NAME: test.get_name(),
                                    CsvFieldId.ANCHOR_NAME: anchor_test.get_name(),
                                    CsvFieldId.TIME_SECONDS: subtest_metrics.get_encoding_time(),
                                    CsvFieldId.SPEEDUP: subtest_metrics.get_speedup_relative_to(anchor_subtest_metrics),
                                    CsvFieldId.PSNR_AVG: subtest_metrics.get_psnr_avg(),
                                    CsvFieldId.SSIM_AVG: subtest_metrics.get_ssim_avg(),
                                    CsvFieldId.BDBR_PSNR: test_metrics.get_bdbr_psnr(anchor_test_metrics),
                                    CsvFieldId.BDBR_SSIM: test_metrics.get_bdbr_ssim(anchor_test_metrics),
                                }
                            )

        except Exception as exception:
            console_log.error(f"Tester: Failed to generate CSV file '{csv_filepath}'")
            self._log_exception(exception)
            exit(1)

    def _run_subtest(self,
                     subtest: SubTest,
                     input_sequence: RawVideoSequence) -> None:

        console_log.info(f"Tester: Running subtest '{subtest.get_name()}' "
                            f"for sequence '{input_sequence.get_filepath().name}'")

        param_set = subtest.get_param_set()
        encoder = subtest.get_encoder()
        subtest_metrics = subtest.get_metrics(input_sequence)

        try:
            metrics_file = subtest.get_metrics(input_sequence)

            if not metrics_file.exists():

                start_time: float = time.perf_counter()
                subtest.get_encoder().encode(input_sequence, subtest.get_param_set())
                encoding_time_seconds: float = round(time.perf_counter() - start_time, 6)

                subtest_metrics.set_encoder_name(encoder.get_name())
                subtest_metrics.set_encoder_revision(encoder.get_revision())
                subtest_metrics.set_encoder_defines(encoder.get_defines())
                subtest_metrics.set_encoder_cmdline(param_set.to_cmdline_str())
                subtest_metrics.set_encoding_input(input_sequence.get_filepath().name)
                subtest_metrics.set_encoding_resolution(f"{input_sequence.get_width()}x{input_sequence.get_height()}")
                subtest_metrics.set_encoding_time(encoding_time_seconds)

            else:
                console_log.info(f"Tester: Results for subtest '{subtest.get_name()}', "
                                    f"sequence '{input_sequence.get_filepath().name}' already exist")

        except Exception as exception:
            console_log.error(f"Tester: Test failed")
            self._log_exception(exception)
            exit(1)

    def _create_base_directories_if_not_exist(self) -> None:
        for path in [
            Cfg().binaries_dir_path,
            Cfg().encoding_output_dir_path,
            Cfg().sources_dir_path
        ]:
            if not path.exists():
                console_log.debug(f"Tester: Creating directory '{path}'")
                try:
                    path.mkdir(parents=True)
                except Exception as exception:
                    console_log.error(f"Tester: Failed to create directory '{path}'")
                    self._log_exception(exception)
                    exit(1)

    def _log_exception(self,
                       exception: Exception) -> None:
        console_log.error(f"Tester: An exception of type '{type(exception).__name__}' was caught: "
                             f"{str(exception)}")
        console_log.error(f"Tester: {traceback.format_exc()}")
