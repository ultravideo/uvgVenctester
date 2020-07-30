"""This module defines functionality related to testing."""

from tester.core.cfg import *
from tester.core.csv import *
from tester.core.log import *
from tester.core.test import *
from tester.core.video import *
from tester.encoders.base import *
from tester.core import ffmpeg

import subprocess
import time
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
            self._tests_by_name[test.name] = test

        self._input_sequences: list = []
        for glob in input_sequence_globs:
            for filepath in Cfg().sequences_dir_path.glob(glob):
                self._input_sequences.append(
                    RawVideoSequence(
                        filepath=filepath.resolve(),
                        # TODO: Figure out a better way to do this.
                        seek=self._tests[0].seek,
                        frames=self._tests[0].frames,
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
                if not anchor_name in self._tests_by_name.keys():
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
    """The tester class the methods of which the user will call."""

    def __init__(self):
        try:
            console_log.info("Tester: Initializing")
            Cfg().read_userconfig()
            Cfg().validate_all()
            self._create_base_directories_if_not_exist()
        except Exception as exception:
            console_log.error("Tester: Failed to initialize")
            log_exception(exception)
            exit(1)

    def create_context(self,
                       tests: list,
                       input_sequence_globs: list) -> TesterContext:
        console_log.info("Tester: Creating context")
        try:
            return TesterContext(tests, input_sequence_globs)
        except Exception as exception:
            console_log.info("Tester: Failed to create context")
            log_exception(exception)
            exit(1)

    def run_tests(self,
                  context:TesterContext) -> None:

        try:
            console_log.info(f"Tester: Building encoders")
            context.validate_initial()
            for test in context.get_tests():
                console_log.info(f"Tester: Building encoder for test '{test.name}'")
                test.encoder.build()
                test.encoder.clean()
            context.validate_final()

            for sequence in context.get_input_sequences():
                for test in context.get_tests():
                    for subtest in test.subtests:
                        for encoding_run in subtest.encoding_runs[sequence]:
                            self._do_encoding_run(encoding_run)

        except Exception as exception:
            console_log.error(f"Tester: Failed to run tests")
            log_exception(exception)
            exit(1)

    def compute_metrics(self,
                        context: TesterContext) -> None:

        for sequence in context.get_input_sequences():
            for test in context.get_tests():
                for subtest in test.subtests:
                    for encoding_run in subtest.encoding_runs[sequence]:

                        try:
                            console_log.info(f"Tester: Computing metrics for '{encoding_run.name}'")

                            metrics = test.metrics[subtest][encoding_run]
                            if metrics.psnr_avg is None\
                               or metrics.ssim_avg is None\
                               or metrics.bitrate is None:

                                psnr_avg, ssim_avg = ffmpeg.compute_psnr_and_ssim(
                                    encoding_run
                                )

                                metrics.psnr_avg = psnr_avg
                                metrics.ssim_avg = ssim_avg
                                metrics.bitrate = encoding_run.output_file.get_bitrate()

                            else:
                                console_log.info(f"Tester: Metrics for '{encoding_run.name}' already exist")

                        except Exception as exception:
                            console_log.error(f"Tester: Failed to compute metrics for '{encoding_run.name}'")
                            if isinstance(exception, subprocess.CalledProcessError):
                                console_log.error(exception.output.decode())
                            log_exception(exception)
                            console_log.info(f"Tester: Ignoring error")

    def generate_csv(self,
                     context: TesterContext,
                     csv_filepath: str) -> None:

        console_log.info(f"Tester: Generating CSV file '{csv_filepath}'")

        try:
            csvfile = CsvFile(filepath=Path(csv_filepath))

            for sequence in context.get_input_sequences():
                for test in context.get_tests():
                    for anchor in [context.get_test(name) for name in test.anchor_names]:
                        for i, subtest in enumerate(test.subtests):

                            try:
                                sub_anchor = anchor.subtests[i]

                                console_log.info(f"Tester: Adding CSV entry for "
                                                 f"'{subtest.name}/{sequence.get_filepath().name}'")

                                csvfile.add_entry(
                                    {
                                        CsvFieldId.SEQUENCE_NAME: sequence.get_filepath().name,
                                        CsvFieldId.SEQUENCE_CLASS: sequence.get_sequence_class(),
                                        CsvFieldId.SEQUENCE_FRAMECOUNT: sequence.get_framecount(),
                                        CsvFieldId.ENCODER_NAME: test.encoder.get_pretty_name(),
                                        CsvFieldId.ENCODER_REVISION: test.encoder.get_short_revision(),
                                        CsvFieldId.ENCODER_DEFINES: test.encoder.get_defines(),
                                        CsvFieldId.ENCODER_CMDLINE: subtest.param_set.to_cmdline_str(),
                                        CsvFieldId.QUALITY_PARAM_NAME: subtest.param_set.get_quality_param_type().pretty_name,
                                        CsvFieldId.QUALITY_PARAM_VALUE: subtest.param_set.get_quality_param_value(),
                                        CsvFieldId.CONFIG_NAME: test.name,
                                        CsvFieldId.ANCHOR_NAME: anchor.name,
                                        CsvFieldId.TIME_SECONDS: test.metrics[subtest].encoding_time_avg,
                                        CsvFieldId.TIME_STD_DEVIATION: test.metrics[subtest].encoding_time_std_deviation,
                                        CsvFieldId.BITRATE: test.metrics[subtest].bitrate_avg,
                                        CsvFieldId.BITRATE_STD_DEVIATION: test.metrics[subtest].bitrate_std_deviation,
                                        CsvFieldId.SPEEDUP: test.metrics[subtest].get_speedup(anchor.metrics[sub_anchor]),
                                        CsvFieldId.PSNR_AVG: test.metrics[subtest].psnr_avg,
                                        CsvFieldId.SSIM_AVG: test.metrics[subtest].ssim_avg,
                                        CsvFieldId.BDBR_PSNR: test.metrics.get_bdbr_psnr(anchor.metrics),
                                        CsvFieldId.BDBR_SSIM: test.metrics.get_bdbr_ssim(anchor.metrics),
                                    }
                                )

                            except Exception as exception:
                                console_log.error(f"Tester: Failed to add CSV entry for "
                                                  f"'{subtest.name}/{sequence.get_filepath().name}'")
                                log_exception(exception)
                                console_log.info(f"Tester: Ignoring error")

        except Exception as exception:
            console_log.error(f"Tester: Failed to generate CSV file '{csv_filepath}'")
            log_exception(exception)
            exit(1)

    def _do_encoding_run(self,
                         encoding_run) -> None:

        console_log.info(f"Tester: Running '{encoding_run.name}'")

        try:
            if not encoding_run.output_file.get_filepath().exists():

                start_time: float = time.perf_counter()
                encoding_run.encoder.encode(encoding_run)
                encoding_time_seconds: float = round(time.perf_counter() - start_time, 6)

                subtest = encoding_run.parent
                test = subtest.parent

                metrics = test.metrics[subtest][encoding_run]
                metrics.encoding_time = encoding_time_seconds
            else:
                console_log.info(f"Tester: Encoding output for '{encoding_run.name}' already exists")

        except Exception as exception:
            console_log.error(f"Tester: Test failed")
            log_exception(exception)
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
                    log_exception(exception)
                    exit(1)
