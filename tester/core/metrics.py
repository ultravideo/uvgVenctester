from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Iterable, Union

import numpy as np
from vmaf.tools.bd_rate_calculator import BDrateCalculator

import tester.core.test as test
from tester.core.log import console_log
from tester.core.video import VideoFileBase, RawVideoSequence
from tester.encoders.base import QualityParam, EncoderBase


def bd_distortion(rate1, distortion1, rate2, distortion2):
    """Get Bjøntegaard Delta -distortion for two RD-curves.

    args:
        - rateN: list of bitrates for line N.
        - psnrN: list of psnr values for line N.

    returns: Average distortion difference (BD-distortion).

    """
    # Sort inputs according to rate.
    values1 = sorted(zip(rate1, distortion1))
    rate1, distortion1 = zip(*values1)
    values2 = sorted(zip(rate2, distortion2))
    rate2, distortion2 = zip(*values2)

    # Change inputs into numpy arrays for bdrint.
    distortion1 = np.array(distortion1)
    rate1 = np.array(rate1)
    distortion2 = np.array(distortion2)
    rate2 = np.array(rate2)

    # Select integration limits such that bots curves are defined.
    min_rate = np.log10(max(np.min(rate1), np.min(rate2)))
    max_rate = np.log10(min(np.max(rate1), np.max(rate2)))

    area1 = bdrint(distortion1, np.log10(rate1), min_rate, max_rate)
    area2 = bdrint(distortion2, np.log10(rate2), min_rate, max_rate)

    avg = (area2 - area1) / (max_rate - min_rate)

    return avg


def bdrint(y, x, low_x, high_x):
    """Integrate a curve defined by rate and distortion between points low and high.

    args:
        y: numpy.array of 4 y coordinates.
        x: numpy.array of 4 x coordinates.
        low_x: start limit for interpolation
        high_x: end limit for interpolation
    """
    def pchipend(tangent, d1, d2):
        if tangent * d1 < 0:
            # If tangent is different sign than the adjacent slope.
            tangent = 0
        elif d1 * d2 < 0 and abs(tangent) > abs(3 * d1):
            # If the adjacent point is a peak.
            tangent = 3 * d1
        return tangent

    def end_tangent(h1, h2, d1, d2):
        return ((2*h1 + h2) * d1 - h1 * d2) / (h1 + h2)

    def mid_tangent(h1, h2, d1, d2):
        # Divides by zero if h2 == h1 and d1 == -d2, but thats not likely
        # to happen in real RD curves. Happened in my tests though.
        return (3*h1 + 3*h2) / ( (2*h2 + h1) / d1 + (h2 + 2*h1) / d2)

    h = x[1:] - x[:-1]
    delta = (y[1:] - y[:-1]) / h

    # I don't know where these equations are from, but it seems they are
    # supposed to provide for a smooth piecewise monotonic curve.
    t = np.zeros(4)
    t[0] = end_tangent(h[0], h[1], delta[0], delta[1])
    t[1] = mid_tangent(h[0], h[1], delta[0], delta[1])
    t[2] = mid_tangent(h[1], h[2], delta[1], delta[2])
    t[3] = end_tangent(h[2], h[1], delta[2], delta[1])

    # Modify end points to ensure the interpolated curve doesn't overshoot the
    # second data point.
    t[0] = pchipend(t[0], delta[0], delta[1])
    t[3] = pchipend(t[3], delta[2], delta[1])

    result = np.float64(0)

    c = (3*delta - 2*t[:-1] - t[1:]) / h
    b = (t[:-1] - 2*delta + t[1:]) / (h * h)
    for i in range(3):
        # Constrain the integration between low_x and high_x.
        s0 = min(high_x, max(low_x, x[i])) - x[i]
        s1 = min(high_x, max(low_x, x[i+1])) - x[i]

        assert(s0 <= s1)
        result += (s1 -  s0) * y[i]
        result += (s1**2 - s0**2) * t[i] / 2
        result += (s1**3 - s0**3) * c[i] / 3
        result += (s1**4 - s0**4) * b[i] / 4

    return result


class EncodingRunMetrics:
    """
    Represents the data for a single encoding run
    This is essentially stateless itself, since it always reads and writes from file
    """

    def __init__(self,
                 file_path: Path):
        self.filepath: Path = file_path

        self._data = {}

        if self.filepath.exists():
            self._read_in()

    def __getitem__(self, item):
        self._read_in()
        return self._data[item]

    def __setitem__(self, key, value):
        self._read_in()
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
        self._read_in()
        return item in self._data

    @property
    def has_calculated_metrics(self):
        """
        Used to determine if the metric object has any calculated metrics such as PSNR, SSIM, or VMAF
        The two non-calculated and always existing metrics are bitrate and encoding speed
        """
        return len(self._data) >= 3

    def clear(self):
        self._data = {}
        self._write_out()


class EncodingQualityRunMetrics:
    """
    Has all of the data for a single quality metric
    """

    def __init__(self, rounds: int, base_path: Path):
        self._rounds = [EncodingRunMetrics(Path(str(base_path).format(x + 1))) for x in range(rounds)]

    def __getitem__(self, item: Union[str, int]):
        if isinstance(item, str):
            # Calculates either the avg or stdev of selected metric
            assert (item.endswith("_avg") or item.endswith("_stdev"))

            value, type_ = self.__split_suffix(item, ["_avg", "_stdev"])

            all_ = [x[value] for x in self._rounds]

            if type_ == "avg":
                return sum(all_) / len(all_)

            elif type_ == "stdev":
                return statistics.stdev(all_) if len(all_) > 1 else 0.0

        elif isinstance(item, int):
            return self._rounds[item - 1]

    def __contains__(self, item):
        if isinstance(item, str):
            assert (item.endswith("_avg") or item.endswith("_stdev"))

            value, _ = self.__split_suffix(item, ["_avg", "_stdev"])
            return all(value in x for x in self._rounds)

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
                         f"{sequence.get_constructed_name()}_{quality_type.short_name}{x}_{{}}_metrics.json"
                      for x in quality_values}
        self.__sequence = sequence
        self.__qp_type = quality_type
        self._prefix = path_prefix.name

        self._data = {x: EncodingQualityRunMetrics(rounds, base_paths[x]) for x in quality_values}

    def get_quality_with_bitrates(self, quality_metric: str):
        return [(item["bitrate_avg"], item[f"{quality_metric}_avg"]) for item in self._data.values()]

    def _compute_bdbr_to_anchor(self, anchor: SequenceMetrics, quality_metric: str):
        return self._compute_bdbr(anchor.get_quality_with_bitrates(quality_metric),
                                  self.get_quality_with_bitrates(quality_metric))

    def _compute_bd_distortion_to_anchor(self, anchor: SequenceMetrics, quality_metric: str):
        anchor_data = sorted(anchor.get_quality_with_bitrates(quality_metric), key=lambda x:x[0])
        own_data = sorted(self.get_quality_with_bitrates(quality_metric), key=lambda x:x[0])
        return bd_distortion([x[0] for x in anchor_data], [x[1] for x in anchor_data],
                             [x[0] for x in own_data], [x[1] for x in own_data], )

    def compare_to_anchor(self, anchor: SequenceMetrics, quality_metric: str):
        if quality_metric == "encoding_time":
            return self._average_speedup(anchor)
        elif quality_metric.endswith("-bddistortion"):
            return self._compute_bd_distortion_to_anchor(anchor, quality_metric[:-13])
        return self._compute_bdbr_to_anchor(anchor, quality_metric)

    def _average_speedup(self, anchor: SequenceMetrics):
        temp = [item["encoding_time_avg"] for item in self._data.values()]
        own_average_time = sum(temp) / len(temp)
        temp = [item["encoding_time_avg"] for item in anchor._data.values()]
        other_average_time = sum(temp) / len(temp)
        return other_average_time / own_average_time

    def metric_overlap(self, anchor: SequenceMetrics, metric: str):
        if anchor == self:
            return 1
        if not metric.endswith("_avg"):
            metric = metric + "_avg"
        rates = [item[metric] for item in self._data.values()]
        anchor_rates = [item[metric] for item in anchor._data.values()]
        start = max(min(rates), min(anchor_rates))
        stop = min(max(rates), max(anchor_rates))
        return (stop - start) / (max(anchor_rates) - min(anchor_rates))

    def rd_curve_crossings(self, anchor: SequenceMetrics, quality_metric: str):
        def linear_equ(first, second):
            slope = (second[1] - first[1]) / (second[0] - first[0])
            b = first[1] - slope * first[0]
            return lambda x: slope * x + b

        if self == anchor:
            return 0

        own = self.get_quality_with_bitrates(quality_metric)
        other = anchor.get_quality_with_bitrates(quality_metric)

        first_index = 0
        second_index = 0

        crossings = 0
        while True:
            if first_index == len(own) - 1 or second_index == len(other) - 1:
                break
            if own[first_index + 1][0] < other[second_index][0]:
                first_index += 1
                continue
            if own[first_index][0] > other[second_index + 1][0]:
                second_index += 1
                continue
            equ1 = linear_equ(own[first_index], own[first_index + 1])
            equ2 = linear_equ(other[second_index], other[second_index + 1])

            if own[first_index][0] < other[second_index][0]:
                start = equ1(other[second_index][0]) - other[second_index][1]
            else:
                start = own[first_index][1] - equ2(own[first_index][0])

            if own[first_index + 1][0] > other[second_index + 1][0]:
                stop = equ1(other[second_index + 1][0]) - other[second_index + 1][1]
            else:
                stop = own[first_index + 1][1] - equ2(own[first_index + 1][0])

            if not start or not stop:
                console_log.warning(f"Potential overlap between {self} and {anchor} that may or may not be recorded.")

            if start * stop < 0:
                crossings += 1

            if own[first_index + 1][0] < other[second_index + 1][0]:
                first_index += 1
            else:
                second_index += 1
        return crossings

    @staticmethod
    def _compute_bdbr(anchor_values, compared_values):
        try:
            bdbr = BDrateCalculator.CalcBDRate(
                sorted(anchor_values, key=lambda x: x[0]),
                sorted(compared_values, key=lambda x: x[0]),
            )
            # no overlap
            if bdbr == -10000:
                bdbr = float("NaN")
        except AssertionError:
            bdbr = float("NaN")

        return bdbr

    def __getitem__(self, item):
        return self._data[item]

    def __repr__(self):
        return f"{self._prefix}/{self.__sequence}/{self.__qp_type.pretty_name}"


class TestMetrics:
    def __init__(self, test_instance: "Test", sequences):
        encoder: EncoderBase = test_instance.encoder
        base_path = encoder.get_output_dir(test_instance.subtests[0].param_set, test_instance.env)

        self.seq_data = {
            seq: SequenceMetrics(base_path,
                                 seq,
                                 test_instance.quality_param_type,
                                 test_instance.quality_param_list,
                                 test_instance.rounds)
            for seq
            in sequences
        }

    def __getitem__(self, item):
        if isinstance(item, RawVideoSequence):
            return self.seq_data[item]
        elif isinstance(item, test.EncodingRun):
            return self.seq_data[item.input_sequence][item.param_set.get_quality_param_value()][item.round_number]
