"""This module defines functionality related to testing."""
import os
import subprocess
import time
from enum import Enum
from pathlib import Path
from typing import Iterable, List
from multiprocessing import Pool, cpu_count
from PyPDF4 import PdfFileMerger
from tempfile import mkstemp
import matplotlib.pyplot as plt

import tester
import pdfkit
import tester.core.cmake as cmake
from tester.core import gcc, ffmpeg, system, vmaf, csv, git, vs, table, conformance, graphs
from tester.core.cfg import Cfg
from tester.core.log import console_log, log_exception
from tester.core.metrics import TestMetrics, SequenceMetrics
from tester.core.test import Test, EncodingRun
from tester.core.video import RawVideoSequence


class ResultTypes(Enum):
    CSV = 1
    TABLE = 2
    GRAPH = 3


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
            paths = [x for x in Cfg().tester_sequences_dir_path.glob(glob)]
            if not paths:
                console_log.error(f"Context: glob \"{glob}\" failed to expand into any sequences")
                raise RuntimeError
            for filepath in paths:
                self._input_sequences.append(
                    RawVideoSequence(
                        filepath=filepath.resolve(),
                    )
                )
        self._metrics: dict = {test.name: TestMetrics(test, self._input_sequences) for test in self._tests}
        self._metrics_calculated_for = []

    def get_tests(self) -> Iterable:
        return self._tests

    def get_metrics(self) -> dict:
        return self._metrics

    def get_test(self,
                 test_name: str) -> Test:
        assert test_name in self._tests_by_name.keys()
        return self._tests_by_name[test_name]

    def get_input_sequences(self) -> List[RawVideoSequence]:
        return self._input_sequences

    def add_metrics_calculated_for(self, type_: ResultTypes):
        self._metrics_calculated_for.append(type_)

    def get_metrics_calculate_for(self):
        return self._metrics_calculated_for

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
                if not subtest.encoder.dummy_run(subtest.param_set, None):
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
            ffmpeg.ffmpeg_validate_config()
            vmaf.vmaf_validate_config()
            vs.vs_validate_config()
            table.table_validate_config()
            conformance.validate_conformance()

            csv.csv_validate_config()

            # Only validate those encoders that are being used.
            for test in context.get_tests():
                test.encoder.validate_config(test)

        except Exception as exception:
            console_log.error("Tester: Configuration variable validation failed")
            log_exception(exception)
            exit(1)

        return context

    @staticmethod
    def run_tests(context: TesterContext,
                  parallel_runs: int = 1) -> None:

        try:
            Tester._create_base_directories_if_not_exist()

            console_log.info(f"Tester: Building encoders")
            context.validate_initial()
            for test in context.get_tests():
                console_log.info(f"Tester: Building encoder for test '{test.name}'")
                test.encoder.build()
                # TODO: Don't clean if the encoder wasn't built.
                if not test.encoder._use_prebuilt:
                    test.encoder.clean()
            context.validate_final()

            encoding_runs = []

            for sequence in context.get_input_sequences():
                for test in context.get_tests():
                    for subtest in test.subtests:
                        for round_ in range(1, test.rounds + 1):
                            name = f"{subtest.name}/{sequence.get_filepath().name} ({round_}/{test.rounds})"
                            encoding_run = EncodingRun(subtest, name, round_, test.encoder, subtest.param_set, sequence)
                            if encoding_run.needs_encoding:
                                encoding_runs.append(
                                    encoding_run
                                )
                            else:
                                console_log.info(f"{test.name}:"
                                                 f" File '{encoding_run.output_file.get_filepath().name}'"
                                                 f" already exists")

            if parallel_runs > 1:
                with Pool(parallel_runs) as p:
                    p.map(Tester._do_encoding_run, encoding_runs)
            else:
                for encoding_run in encoding_runs:
                    Tester._do_encoding_run(encoding_run)

        except Exception as exception:
            console_log.error(f"Tester: Failed to run tests")
            log_exception(exception)
            exit(1)

    @staticmethod
    def compute_metrics(context: TesterContext,
                        parallel_calculations: int = 1,
                        result_types: Iterable = (ResultTypes.CSV, ResultTypes.TABLE, ResultTypes.GRAPH)) -> None:
        result_t = []
        for r in result_types:
            if r not in context.get_metrics_calculate_for():
                result_t.append(r)

        if not result_t:
            return

        values = []
        parallel_calculations = max(parallel_calculations, 1)
        global_psnr = \
            (
                    any([csv.CsvField(csv.CsvFieldBaseType.PSNR | value) in Cfg().csv_enabled_fields
                         for value
                         in csv.CsvFieldValueType]) and ResultTypes.CSV in result_t
            ) or (
                    table.TableColumns.PSNR_BDBR in Cfg().table_enabled_columns and ResultTypes.TABLE in result_t
            ) or (
                    graphs.GraphMetrics.PSNR in Cfg().graph_enabled_metrics and ResultTypes.GRAPH in result_t
            )
        global_ssim = \
            (
                    any([csv.CsvField(csv.CsvFieldBaseType.SSIM | value) in Cfg().csv_enabled_fields
                         for value
                         in csv.CsvFieldValueType]) and ResultTypes.CSV in result_t
            ) or (
                    table.TableColumns.SSIM_BDBR in Cfg().table_enabled_columns and ResultTypes.TABLE in result_t
            ) or (
                    graphs.GraphMetrics.SSIM in Cfg().graph_enabled_metrics and ResultTypes.GRAPH in result_t
            )
        global_vmaf = \
            (
                    any([csv.CsvField(csv.CsvFieldBaseType.VMAF | value) in Cfg().csv_enabled_fields
                         for value
                         in csv.CsvFieldValueType]) and ResultTypes.CSV in result_t
            ) or (
                    table.TableColumns.VMAF_BDBR in Cfg().table_enabled_columns and ResultTypes.TABLE in result_t
            ) or (
                    graphs.GraphMetrics.VMAF in Cfg().graph_enabled_metrics and ResultTypes.GRAPH in result_t
            )
        global_conformance = csv.CsvField.CONFORMANCE in Cfg().csv_enabled_fields and ResultTypes.CSV in result_t
        
        if global_vmaf:
            for test in context.get_tests():
                ffmpeg.copy_vmaf_models(test)

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
                        needed_metrics = []
                        if "psnr" not in metric and global_psnr:
                            needed_metrics.append("psnr")
                        if "ssim" not in metric and global_ssim:
                            needed_metrics.append("ssim")
                        if "vmaf" not in metric and global_vmaf:
                            needed_metrics.append("vmaf")
                        conformance_needed = "conforms" not in metric and global_conformance
                        arguments = (encoding_run, metric, needed_metrics, conformance_needed,
                                     Cfg().remove_encodings_after_metric_calculation)
                        if parallel_calculations > 1:
                            values.append(arguments)
                        else:
                            Tester._calculate_metrics_for_one_run(arguments)

        if parallel_calculations > 1:
            with Pool(parallel_calculations) as p:
                p.map(Tester._calculate_metrics_for_one_run, values)

        for m in result_types:
            context.add_metrics_calculated_for(m)

        if global_vmaf:
            for test in context.get_tests():
                ffmpeg.remove_vmaf_models(test)

    @staticmethod
    def _calculate_metrics_for_one_run(in_args):
        encoding_run, metrics, needed_metrics, conf, remove_encoding = in_args
        try:
            console_log.info(f"Tester: Computing metrics for '{encoding_run.name}'")

            if encoding_run.qp_name not in [tester.QualityParam.QP, tester.QualityParam.CRF]:
                metrics["target_bitrate"] = encoding_run.qp_value

            if "bitrate" not in metrics:
                metrics["bitrate"] = encoding_run.output_file.get_bitrate()

            if conf and "conforms" not in metrics:
                if encoding_run.encoder.file_suffix == "hevc":
                    metrics["conforms"] = conformance.check_hevc_conformance(encoding_run)
                else:
                    # TODO: implement for other codecs
                    metrics["conforms"] = False

            if needed_metrics:
                res = ffmpeg.compute_metrics(
                    encoding_run,
                    needed_metrics
                )
                for m in needed_metrics:
                    metrics[m] = res[m]
            else:
                console_log.info(f"Tester: Metrics for '{encoding_run.name}' already exist")

            if encoding_run.output_file.get_filepath().exists() and remove_encoding:
                os.remove(encoding_run.output_file.get_filepath())

        except Exception as exception:
            console_log.error(f"Tester: Failed to compute metrics for '{encoding_run.name}'")
            if isinstance(exception, subprocess.CalledProcessError):
                console_log.error(exception.output.decode())
            log_exception(exception)
            console_log.info(f"Tester: Ignoring error")

    @staticmethod
    def generate_csv(context: TesterContext,
                     csv_filepath: str,
                     parallel_calculations=1) -> None:

        Tester.compute_metrics(context, parallel_calculations, (ResultTypes.CSV,))
        console_log.info(f"Tester: Generating CSV file '{csv_filepath}'")
        metrics = context.get_metrics()

        try:
            csvfile = csv.CsvFile(filepath=Path(csv_filepath))

            for sequence in context.get_input_sequences():
                for test in context.get_tests():
                    for anchor in [context.get_test(name) for name in test.anchor_names]:
                        for subtest, anchor_subtest in zip(test.subtests, anchor.subtests):

                            try:
                                csvfile.add_entry(metrics, test, subtest, anchor, anchor_subtest, sequence)

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
    def _do_encoding_run(encoding_run: EncodingRun) -> None:

        console_log.info(f"Tester: Running '{encoding_run.name}'")

        try:
            if encoding_run.needs_encoding:

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

    @staticmethod
    def create_tables(context: TesterContext,
                      table_filepath: str,
                      format_: [table.TableFormats, None] = None,
                      parallel_calculations=1,
                      first_page=None):
        Tester.compute_metrics(context, parallel_calculations, (ResultTypes.TABLE,))

        filepath = Path(table_filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        if format_ is None:
            try:
                format_ = {
                    ".html": table.TableFormats.HTML,
                    ".pdf": table.TableFormats.PDF
                }[filepath.suffix]
            except KeyError:
                raise ValueError("Can't detect table type from file suffix")

        if format_ == table.TableFormats.HTML:
            with open(filepath, "wb") as f:
                html, *_ = table.tablefy(context, first_page)
                f.write(html.encode("utf-8"))
        elif format_ == table.TableFormats.PDF:
            html, pixels, pages = table.tablefy(context)
            config = pdfkit.configuration(wkhtmltopdf=Cfg().wkhtmltopdf)
            options = {
                # Again something weird with the PDF generation and margins...
                'page-height': f"{pixels + 50 + (5 if Cfg().system_os_name == 'Linux' else 0)}px",
                'page-width': "1850px",
                'margin-top': "25px",
                'margin-bottom': "25px",
                'margin-right': "25px",
                'margin-left': "25px",
                "disable-smart-shrinking": None,
            }
            pdfkit.from_string(html, filepath, options=options, configuration=config)

            merger = PdfFileMerger()
            if first_page:
                a, temp_path = mkstemp()
                first_page_html = \
                    "\n" \
                    "<!DOCTYPE html>\n" \
                    "<html>\n" \
                    "   <head>\n" \
                    "   </head>\n" \
                    "   <body>\n" \
                    f"       <div> {first_page} </div>\n" \
                    f"  </body>\n" \
                    f"</html>\n"
                pdfkit.from_string(first_page_html, temp_path, options=options, configuration=config)
                merger.append(open(temp_path, "rb"))

            merger.append(open(filepath, "rb"), pages=(0, pages))
            merger.write(open(filepath, "wb"))

        else:
            raise ValueError("Invalid table type")

    @staticmethod
    def generate_rd_graphs(context: TesterContext,
                           basedir: Path,
                           parallel_generations: [int, None] = None,
                           parallel_calculations: int = 1):
        Tester.compute_metrics(context, parallel_calculations, (ResultTypes.GRAPH,))
        if not basedir.exists():
            basedir.mkdir()
        if not basedir.is_dir():
            raise TypeError(f"{str(basedir)} exists but it is not a directory")

        seqs = context.get_input_sequences()
        metrics = context.get_metrics()

        assert len(Cfg().graph_colors) >= len(metrics)

        enabled_metrics = []
        if graphs.GraphMetrics.PSNR in Cfg().graph_enabled_metrics:
            enabled_metrics.append("psnr")
        if graphs.GraphMetrics.SSIM in Cfg().graph_enabled_metrics:
            enabled_metrics.append("ssim")
        if graphs.GraphMetrics.VMAF in Cfg().graph_enabled_metrics:
            enabled_metrics.append("vmaf")

        figures = []
        for index, seq in enumerate(seqs):
            figures.append((basedir, context, enabled_metrics, index, metrics, seq))

        if parallel_generations == 1:
            for fig in figures:
                Tester._do_one_figure(fig)
        else:
            if parallel_generations is None:
                parallel_generations = cpu_count()
            with Pool(parallel_generations) as p:
                p.map(Tester._do_one_figure, figures)

    @staticmethod
    def _do_one_figure(args):
        basedir, context, enabled_metrics, index, metrics, seq = args
        console_log.info(f"Generating RD-graph for {seq.get_suffixless_name()}")
        plt.figure(index, [30, 35])
        video_name = seq.get_filepath().name
        plt.suptitle(video_name, size=50)
        for plot_index, metric in enumerate(enabled_metrics):
            plt.subplot(100 * len(enabled_metrics) + 10 + plot_index + 1)
            plt.title(metric.upper(), size=26)
            temp = []

            for test, color in zip(metrics, Cfg().graph_colors):
                video_data = [metrics[test][seq][subtest.param_set.get_quality_param_value()] for subtest in
                              context.get_test(test).subtests]
                rates = [data["bitrate_avg"] / 1000 for data in video_data]
                a = plt.plot(
                    rates,
                    [data[f"{metric}_avg"] for data in video_data],
                    marker="o",
                    color=color
                )
                temp.append(a[0])
                if "target_bitrate_avg" in video_data[0] and Cfg().graph_include_bitrate_targets:
                    for target in video_data:
                        plt.axvline(x=target["target_bitrate_avg"] / 1000)

            plt.legend(temp, metrics, fontsize=18)
            te = plt.gca()
            te.xaxis.set_tick_params(labelsize=16)
            te.yaxis.set_tick_params(labelsize=16)
            plt.xlim(left=0)
        plt.savefig((basedir / video_name).with_suffix(".png"))
        plt.close()
