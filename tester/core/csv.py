#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""This module defines functionality related to creating the tester output CSV file."""

from tester.core import cfg

import os

from enum import *

class CsvFieldId(Enum):
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
    SPEEDUP: int = 13
    PSNR_AVG: int = 14
    SSIM_AVG: int = 15
    BDBR_PSNR: int = 16
    BDBR_SSIM: int = 17


class CsvFile():
    """Represents the tester output CSV file."""

    def __init__(self,
                 filepath: str):
        self.directory = os.path.dirname(filepath)
        self.filepath = filepath

        # Create the new CSV file.
        if self.directory and not os.path.exists(self.directory):
            os.makedirs(self.directory)

        # Create the header.
        header_row = ""
        for field_id in cfg.Cfg().csv_enabled_fields:
            header_row += cfg.Cfg().csv_field_names[field_id]
            header_row += cfg.Cfg().csv_field_separator

        with open(self.filepath, "w") as file:
            file.write(header_row + "\n")

    def add_entry(self,
                  values_by_field: dict) -> None:

        config_name = values_by_field[CsvFieldId.CONFIG_NAME]
        anchor_name = values_by_field[CsvFieldId.ANCHOR_NAME]

        new_row = ""
        for field_id in cfg.Cfg().csv_enabled_fields:
            value = values_by_field[field_id]

            if isinstance(value, float):
                # Round floats, use the configured decimal point character.
                value = round(value, cfg.Cfg().csv_float_rounding_accuracy)
                value = str(value).replace(".", cfg.Cfg().csv_decimal_point)
            else:
                value = str(value)

            # If the config has no anchor, i.e. the anchor name is the same as the config name,
            # give special treatment to certain fields.
            # TODO: Make values user-configurable?
            if field_id == CsvFieldId.ANCHOR_NAME and anchor_name == config_name:
                value = "None"
            elif field_id == CsvFieldId.SPEEDUP and anchor_name == config_name:
                value = "0"

            new_row += f"{value}{cfg.Cfg().csv_field_separator}"

        with open(self.filepath, "a") as file:
            file.write(new_row + "\n")
