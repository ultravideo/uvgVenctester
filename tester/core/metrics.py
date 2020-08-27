from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Iterable, Union

from vmaf.tools.bd_rate_calculator import BDrateCalculator

import tester.core.test as test
from tester.core.cfg import Cfg
from tester.core.video import VideoFileBase, RawVideoSequence
from tester.encoders.base import QualityParam


class EncodingRunMetrics:

    def __init__(self,
                 file_path: Path):
        self.filepath: Path = file_path

        self._data = {}

        if self.filepath.exists():
            self._read_in()

    def __getitem__(self, item):
        return self._data[item]

    def __setitem__(self, key, value):
        self._data[key] = value
        self._write_out()

    def _write_out(self) -> None:
        with self.filepath.open("w") as file:
            json.dump(self._data, file)

    def _read_in(self) -> None:
        try:
            with self.filepath.open("r") as file:
                self._data = json.load(file)
        except FileNotFoundError:
            pass

    def __contains__(self, item):
        return item in self._data


class EncodingQualityRunMetrics:

    def __init__(self, rounds: int, base_path: Path):
        self._rounds = [EncodingRunMetrics(Path(str(base_path).format(x + 1))) for x in range(rounds)]

    def __getitem__(self, item: Union[str, int]):
        if isinstance(item, str):
            assert (item.endswith("_avg") or item.endswith("_stdev"))

            value, type_ = self.__split_suffix(item, ["_avg", "_stdev"])

            all_ = [x[value] for x in self._rounds]

            if type_ == "avg":
                return sum(all_) / len(all_)

            elif type_ == "stdev":
                return statistics.stdev(all_) if len(all_) > 1 else 0.0

        elif isinstance(item, int):
            return self._rounds[item - 1]

    @staticmethod
    def __split_suffix(item: str, suffixes):
        for suffix in suffixes:
            if item.endswith(suffix):
                return item.replace(suffix, ""), suffix[1:]

    def speedup(self, anchor: EncodingQualityRunMetrics):
        return anchor["encoding_time_avg"] / self["encoding_time_avg"]


class SequenceMetrics:
    def __init__(self,
                 path_prefix: Path,
                 sequence: VideoFileBase,
                 quality_type: QualityParam,
                 quality_values: Iterable,
                 rounds: int):
        base_paths = {x: path_prefix /
                         f"{sequence.get_suffixless_name()}_{quality_type.short_name}{x}_{{}}_metrics.json" for x in
                      quality_values}

        self._data = {x: EncodingQualityRunMetrics(rounds, base_paths[x]) for x in quality_values}

    def get_quality_with_bitrates(self, quality_metric: str):
        return [(item["bitrate_avg"], item[f"{quality_metric}_avg"]) for item in self._data.values()]

    def compute_bdbr_to_anchor(self, anchor: SequenceMetrics, quality_metric: str):
        return self._compute_bdbr(anchor.get_quality_with_bitrates(quality_metric),
                                  self.get_quality_with_bitrates(quality_metric))

    @staticmethod
    def _compute_bdbr(anchor_values, compared_values):
        try:
            bdbr = BDrateCalculator.CalcBDRate(
                sorted(anchor_values, key=lambda x: x[0]),
                sorted(compared_values, key=lambda x: x[0]),
            )
        except AssertionError:
            bdbr = float("NaN")

        return bdbr

    def __getitem__(self, item):
        return self._data[item]


class TestMetrics:
    def __init__(self, test: "Test"):
        base_path = Cfg().tester_output_dir_path /\
                    f"{test.encoder.get_name()}" \
                    f"_{test.encoder.get_short_revision()}" \
                    f"_{test.encoder.get_short_define_hash()}" / \
                    test.subtests[0].param_set.to_cmdline_str(False)
        self.seq_data = {
            seq: SequenceMetrics(base_path, seq, test.quality_param_type, test.quality_param_list, test.rounds)
            for seq
            in test.sequences
        }

    def __getitem__(self, item):
        if isinstance(item, RawVideoSequence):
            return self.seq_data[item]
        elif isinstance(item, test.EncodingRun):
            return self.seq_data[item.input_sequence][item.param_set.get_quality_param_value()][item.round_number]
