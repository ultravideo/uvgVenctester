"""This module defines functionality related to generating the CSV output file."""

from tester.core.log import *
from tester.core import cfg

import math
from pathlib import Path
from enum import *


def csv_validate_config():
    for field in cfg.Cfg().csv_enabled_fields:
        if not field in cfg.Cfg().csv_field_names.keys():
            console_log.error(f"CSV: Field '{field}' is enabled but does not have a name")
            raise RuntimeError


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
    TIME_SECONDS: int = 12
    TIME_STDEV: int = 13
    SPEEDUP: int = 14
    BITRATE: int = 15
    BITRATE_STDEV: int = 16
    PSNR_AVG: int = 17
    PSNR_STDEV: int = 18
    SSIM_AVG: int = 19
    SSIM_STDEV: int = 20
    VMAF_AVG: int = 21
    VMAF_STDEV: int = 22
    BDBR_PSNR: int = 23
    BDBR_SSIM: int = 24


class CsvFile():
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

    def add_entry(self,
                  values_by_field: dict) -> None:

        config_name = values_by_field[CsvField.CONFIG_NAME]
        anchor_name = values_by_field[CsvField.ANCHOR_NAME]

        new_row = ""
        for field_id in cfg.Cfg().csv_enabled_fields:
            value = values_by_field[field_id]

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
            if field_id == CsvField.ANCHOR_NAME and anchor_name == config_name:
                value = "-"
            elif field_id == CsvField.SPEEDUP and anchor_name == config_name:
                value = "-"

            new_row += f"{value}{cfg.Cfg().csv_field_delimiter}"

        with self._filepath.open("a") as file:
            file.write(new_row + "\n")
