"""This module defines functionality related to generating the CSV output file."""

import math
from enum import Enum
from pathlib import Path
from typing import Union

from tester.core import cfg
from tester.core.log import console_log
from tester.core.metrics import SequenceMetrics


def csv_validate_config():
    for field in cfg.Cfg().csv_enabled_fields:
        if not field in cfg.Cfg().csv_field_names.keys():
            console_log.error(f"CSV: Field '{field}' is enabled but does not have a name")
            raise RuntimeError


class CsvFieldBaseType(Enum):
    BITS = 1 << 10
    PSNR = 1 << 11
    SSIM = 1 << 12
    VMAF = 1 << 13
    TIME = 1 << 14

    def __or__(self, other: Union[Enum, int]):
        if type(other) is int:
            return self.value | other
        return self.value | other.value

    def __str__(self):
        names = {
            CsvFieldBaseType.BITS: "bitrate",
            CsvFieldBaseType.PSNR: "psnr",
            CsvFieldBaseType.SSIM: "ssim",
            CsvFieldBaseType.VMAF: "vmaf",
            CsvFieldBaseType.TIME: "encoding_time"
        }
        return names[self]


class CsvFieldValueType(Enum):
    VALUE = 1
    STDEV = 2
    COMPARISON = 3
    CROSSINGS = 4
    OVERLAP = 5
    COMPARISON2 = 6

    def __or__(self, other: Union[Enum, int]):
        if type(other) is int:
            return self.value | other
        return self.value | other.value


class CsvField(Enum):
    """An enumeration to identify the different CSV fields."""
    NONE: int = 0
    SEQUENCE_NAME: int = 1
    SEQUENCE_CLASS: int = 2
    SEQUENCE_FRAMECOUNT: int = 3
    ENCODER_NAME: int = 4
    ENCODER_REVISION: int = 5
    ENCODER_DEFINES: int = 6
    ENCODER_CMDLINE: int = 7
    QUALITY_PARAM_NAME: int = 8
    QUALITY_PARAM_VALUE: int = 9
    CONFIG_NAME: int = 10
    ANCHOR_NAME: int = 11

    TIME_SECONDS: int = CsvFieldBaseType.TIME | CsvFieldValueType.VALUE
    TIME_STDEV: int = CsvFieldBaseType.TIME | CsvFieldValueType.STDEV
    SPEEDUP: int = CsvFieldBaseType.TIME | CsvFieldValueType.COMPARISON
    ITEM_WISE_SPEEDUP: int = CsvFieldBaseType.TIME | CsvFieldValueType.COMPARISON2
    # Crossings
    # Overlap

    BITRATE: int = CsvFieldBaseType.BITS | CsvFieldValueType.VALUE
    BITRATE_STDEV: int = CsvFieldBaseType.BITS | CsvFieldValueType.STDEV
    # Comparison
    # Crossings
    RATE_OVERLAP: int = CsvFieldBaseType.BITS | CsvFieldValueType.OVERLAP
    BITRATE_ERROR: int = CsvFieldBaseType.BITS | 6

    PSNR_AVG: int = CsvFieldBaseType.PSNR | CsvFieldValueType.VALUE
    PSNR_STDEV: int = CsvFieldBaseType.PSNR | CsvFieldValueType.STDEV
    BDBR_PSNR: int = CsvFieldBaseType.PSNR | CsvFieldValueType.COMPARISON
    PSNR_CURVE_CROSSINGS: int = CsvFieldBaseType.PSNR | CsvFieldValueType.CROSSINGS
    PSNR_OVERLAP: int = CsvFieldBaseType.PSNR | CsvFieldValueType.OVERLAP
    BD_PSNR: int = CsvFieldBaseType.PSNR | CsvFieldValueType.COMPARISON2

    SSIM_AVG: int = CsvFieldBaseType.SSIM | CsvFieldValueType.VALUE
    SSIM_STDEV: int = CsvFieldBaseType.SSIM | CsvFieldValueType.STDEV
    BDBR_SSIM: int = CsvFieldBaseType.SSIM | CsvFieldValueType.COMPARISON
    SSIM_CURVE_CROSSINGS: int = CsvFieldBaseType.SSIM | CsvFieldValueType.CROSSINGS
    SSIM_OVERLAP: int = CsvFieldBaseType.SSIM | CsvFieldValueType.OVERLAP
    BD_SSIM: int = CsvFieldBaseType.SSIM | CsvFieldValueType.COMPARISON2

    VMAF_AVG: int = CsvFieldBaseType.VMAF | CsvFieldValueType.VALUE
    VMAF_STDEV: int = CsvFieldBaseType.VMAF | CsvFieldValueType.STDEV
    BDBR_VMAF: int = CsvFieldBaseType.VMAF | CsvFieldValueType.COMPARISON
    VMAF_CURVE_CROSSINGS: int = CsvFieldBaseType.VMAF | CsvFieldValueType.CROSSINGS
    VMAF_OVERLAP: int = CsvFieldBaseType.VMAF | CsvFieldValueType.OVERLAP
    BD_VMAF: int = CsvFieldBaseType.VMAF | CsvFieldValueType.COMPARISON2

    CONFORMANCE: int = 12

    @classmethod
    def has_value(cls, value):
        return value in cls._value2member_map_


class CsvFile:
    """Represents the tester output CSV file."""

    def __init__(self,
                 filepath: Path):
        self._filepath: Path = filepath

        # Create the new CSV file.
        if not Path(self._filepath.parent).exists():
            Path(self._filepath.parent).mkdir(parents=True, exist_ok=True)
        with self._filepath.open("w") as file:
            # Create the header.
            header_row = ""
            for field_id in cfg.Cfg().csv_enabled_fields:
                header_row += cfg.Cfg().csv_field_names[field_id]
                header_row += cfg.Cfg().csv_field_delimiter
            file.write(header_row + "\n")

    def add_entry(self, metrics, test, subtest, anchor, anchor_subtest, sequence) -> None:

        metric = metrics[test.name][sequence][subtest.param_set.get_quality_param_value()]
        anchor_metric = metrics[anchor.name][sequence][anchor_subtest.param_set.get_quality_param_value()]
        sequence_metric: SequenceMetrics = metrics[test.name][sequence]
        anchor_seq: SequenceMetrics = metrics[anchor.name][sequence]

        values_by_field = {
            CsvField.SEQUENCE_NAME: lambda: sequence.get_filepath().name,
            CsvField.SEQUENCE_CLASS: lambda: sequence.get_sequence_class(),
            CsvField.SEQUENCE_FRAMECOUNT: lambda: sequence.get_framecount(),
            CsvField.ENCODER_NAME: lambda: test.encoder.get_pretty_name(),
            CsvField.ENCODER_REVISION: lambda: test.encoder.get_short_revision(),
            CsvField.ENCODER_DEFINES: lambda: test.encoder.get_defines(),
            CsvField.ENCODER_CMDLINE: lambda: subtest.param_set.to_cmdline_str(),
            CsvField.QUALITY_PARAM_NAME: lambda: subtest.param_set.get_quality_param_type().pretty_name,
            CsvField.QUALITY_PARAM_VALUE: lambda: subtest.param_set.get_quality_param_value()
            if "target_bitrate_avg" not in metric
            else metric["target_bitrate_avg"],
            CsvField.CONFIG_NAME: lambda: test.name,
            CsvField.ANCHOR_NAME: lambda: anchor.name,

            CsvField.BITRATE_ERROR: lambda: -1 + metric["bitrate_avg"] / metric[
                "target_bitrate_avg"] if "target_bitrate_avg" in metric else "-",

            CsvField.CONFORMANCE: lambda: metric["conforms_avg"],
        }

        # TODO: Find a way to make this cleaner
        for base_type in CsvFieldBaseType:
            try:
                values_by_field[CsvField(base_type | CsvFieldValueType.VALUE)] = \
                    lambda base_type=base_type: metric[str(base_type) + "_avg"]
            except ValueError:
                pass

            try:
                values_by_field[CsvField(base_type | CsvFieldValueType.STDEV)] = \
                    lambda base_type=base_type: metric[str(base_type) + "_stdev"]
            except ValueError:
                pass

            try:
                values_by_field[CsvField(base_type | CsvFieldValueType.COMPARISON)] = \
                    lambda base_type=base_type: sequence_metric.compare_to_anchor(anchor_seq, str(base_type))
            except ValueError:
                pass

            try:
                values_by_field[CsvField(base_type | CsvFieldValueType.CROSSINGS)] = \
                    lambda base_type=base_type: sequence_metric.rd_curve_crossings(anchor_seq, str(base_type))
            except ValueError:
                pass

            try:
                values_by_field[CsvField(base_type | CsvFieldValueType.OVERLAP)] = \
                    lambda base_type=base_type: sequence_metric.metric_overlap(anchor_seq, str(base_type))
            except ValueError:
                pass
            try:
                values_by_field[CsvField(base_type | CsvFieldValueType.COMPARISON2)] = \
                    lambda base_type=base_type: sequence_metric.compare_to_anchor(anchor_seq, str(base_type)+"-bddistortion")
            except ValueError:
                pass

        values_by_field[CsvField.ITEM_WISE_SPEEDUP] = \
            lambda: anchor_metric["encoding_time_avg"] / metric["encoding_time_avg"]

        new_row = []
        for field_id in cfg.Cfg().csv_enabled_fields:
            value = values_by_field[field_id]()

            if isinstance(value, float):
                if math.isnan(value):
                    value = "-"
                else:
                    # Round floats, use the configured decimal point character.
                    value = round(value, cfg.Cfg().csv_float_rounding_accuracy)
                    value = str(value).replace(".", cfg.Cfg().csv_decimal_point)
            else:
                value = str(value)

            # If the config has no anchor, i.e. the anchor name is the same as the config name,
            # give special treatment to certain fields.
            # TODO: Make values user-configurable?
            if field_id == CsvField.ANCHOR_NAME and anchor == test:
                value = "-"

            new_row.append(value)

        with self._filepath.open("a") as file:
            file.write(cfg.Cfg().csv_field_delimiter.join(new_row) + "\n")
