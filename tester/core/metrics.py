"""This module defines functionality related video quality metrics."""

from __future__ import annotations

from tester.core.test import *
from tester.core.cfg import *
from tester.core.video import *
from tester.encoders.base import *

import functools
import json
import statistics
from pathlib import Path
from vmaf.tools.bd_rate_calculator import BDrateCalculator


class EncodingRunMetrics:

    def __init__(self,
                 parent: SubTestMetrics,
                 encoding_run: EncodingRun):

        self.parent: SubTestMetrics = parent
        self.encoding_run: EncodingRun = encoding_run
        self.filepath: Path = encoding_run.metrics_path

        self.result_bitrate: float = None
        self.result_encoding_time: float = None
        self.result_psnr_avg: float = None
        self.result_ssim_avg: float = None

        if self.filepath.exists():
            self._read_in()

    @property
    def encoding_time(self) -> float:
        if self.filepath.exists():
            self._read_in()
        return self.result_encoding_time

    @encoding_time.setter
    def encoding_time(self,
                      encoding_time_as_seconds: float) -> None:
        self.result_encoding_time = encoding_time_as_seconds
        self._write_out()

    @property
    def psnr_avg(self) -> float:
        if self.filepath.exists():
            self._read_in()
        return self.result_psnr_avg

    @psnr_avg.setter
    def psnr_avg(self,
                 psnr_avg: float) -> None:
        self.result_psnr_avg = psnr_avg
        self._write_out()

    @property
    def ssim_avg(self) -> float:
        if self.filepath.exists():
            self._read_in()
        return self.result_ssim_avg

    @ssim_avg.setter
    def ssim_avg(self,
                 ssim_avg: float) -> None:
        self.result_ssim_avg = ssim_avg
        self._write_out()

    @property
    def bitrate(self) -> float:
        if self.filepath.exists():
            self._read_in()
        return self.result_bitrate

    @bitrate.setter
    def bitrate(self,
                bitrate: float) -> None:
        self.result_bitrate = bitrate
        self._write_out()

    def _write_out(self) -> None:
        with self.filepath.open("w") as file:
            json_dict = {}
            for attribute_name in self.__dict__:
                if attribute_name.startswith("result"):
                    json_dict[attribute_name] = getattr(self, attribute_name)
            json.dump(json_dict, file)

    def _read_in(self) -> None:
        with self.filepath.open("r") as file:
            json_dict = json.load(file)
            for attribute_name in json_dict.keys():
                setattr(self, attribute_name, json_dict[attribute_name])


class SubTestMetrics:

    def __init__(self,
                 parent: TestMetrics,
                 subtest: SubTest):

        self.parent: TestMetrics = parent
        self.subtest: SubTest = subtest
        # Key: EncodingRun, value: EncodingRunMetrics
        # Populated dynamically in __getitem__
        self.run_metrics: dict = {}

    def __getitem__(self,
                    item: EncodingRun) -> EncodingRunMetrics:
        if not item in self.run_metrics.keys():
            self.run_metrics[item] = EncodingRunMetrics(self, item)
        return self.run_metrics[item]

    @property
    def bitrate_avg(self) -> float:
        bitrates = [metrics.bitrate for metrics in self.run_metrics.values()]
        return sum(bitrates) / len(bitrates)

    @property
    def bitrate_std_deviation(self) -> float:
        bitrates = [metrics.bitrate for metrics in self.run_metrics.values()]
        if len(bitrates) > 1:
            return statistics.stdev(bitrates)
        return 0.0

    @property
    def encoding_time_avg(self) -> float:
        encoding_times = [metrics.encoding_time for metrics in self.run_metrics.values()]
        return sum(encoding_times) / len(encoding_times)

    @property
    def encoding_time_std_deviation(self) -> float:
        encoding_times = [metrics.encoding_time for metrics in self.run_metrics.values()]
        if len(encoding_times) > 1:
            return statistics.stdev(encoding_times)
        return 0.0

    @property
    def psnr_avg(self) -> float:
        psnr_avgs = [metrics.psnr_avg for metrics in self.run_metrics.values()]
        return sum(psnr_avgs) / len(psnr_avgs)

    @property
    def ssim_avg(self) -> float:
        ssim_avgs = [metrics.ssim_avg for metrics in self.run_metrics.values()]
        return sum(ssim_avgs) / len(ssim_avgs)

    def get_speedup(self,
                    anchor: SubTestMetrics) -> float:
        return anchor.encoding_time_avg / self.encoding_time_avg


class TestMetrics:

    def __init__(self,
                 parent: Test):

        self.parent: Test = parent
        # Key: SubTest, value: SubTestMetrics
        # Populated dynamically in __getitem__
        self.subtest_metrics: dict = {}

    def __getitem__(self,
                    item: SubTest) -> SubTestMetrics:
        if not item in self.subtest_metrics.keys():
            self.subtest_metrics[item] = SubTestMetrics(self, item)
        return self.subtest_metrics[item]

    def get_bdbr_psnr(self,
                      anchor: TestMetrics) -> float:

        if self is anchor:
            return 0

        psnr_list = []
        anchor_psnr_list = []

        for subtest_metrics in self.subtest_metrics.values():
            psnr_list.append((
                subtest_metrics.bitrate_avg,
                subtest_metrics.psnr_avg
            ))

        for anchor_subtest_metrics in anchor.subtest_metrics.values():
            anchor_psnr_list.append((
                anchor_subtest_metrics.bitrate_avg,
                anchor_subtest_metrics.psnr_avg
            ))

        return TestMetrics._compute_bdbr(psnr_list, anchor_psnr_list)

    def get_bdbr_ssim(self,
                      anchor: TestMetrics) -> float:

        if self is anchor:
            return 0

        ssim_list = []
        anchor_ssim_list = []

        for subtest_metrics in self.subtest_metrics.values():
            ssim_list.append((
                subtest_metrics.bitrate_avg,
                subtest_metrics.ssim_avg
            ))

        for anchor_subtest_metrics in anchor.subtest_metrics.values():
            anchor_ssim_list.append((
                anchor_subtest_metrics.bitrate_avg,
                anchor_subtest_metrics.ssim_avg
            ))

        return TestMetrics._compute_bdbr(ssim_list, anchor_ssim_list)

    @staticmethod
    def _compute_bdbr(bitrate_metric_tuple_list: list,
                      anchor_bitrate_metric_tuple_list: list) -> float:

        def bitrate_metric_tuple_list_asc_sort_by_bitrate(a, b):
            return -1 if a[0] < b[0] else 1

        sort_key = functools.cmp_to_key(bitrate_metric_tuple_list_asc_sort_by_bitrate)

        bitrate_metric_tuple_list = sorted(bitrate_metric_tuple_list, key=sort_key)
        anchor_bitrate_metric_tuple_list = sorted(anchor_bitrate_metric_tuple_list, key=sort_key)

        try:
            bdbr = BDrateCalculator().CalcBDRate(
                bitrate_metric_tuple_list,
                anchor_bitrate_metric_tuple_list)
        except AssertionError:
            bdbr = float("NaN")

        return bdbr
