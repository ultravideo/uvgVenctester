#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""This module defines functionality related to computing video quality metrics."""

from __future__ import annotations

from tester.core.cfg import *
from tester.core.video import *
from tester.encoders.base import *

import functools
import hashlib
import json
from pathlib import Path
from vmaf.tools.bd_rate_calculator import BDrateCalculator

class MetricsFile:

    def __init__(self,
                 input_sequence: RawVideoSequence,
                 output_sequence: HevcVideoFile):

        self._input_sequence: RawVideoSequence = input_sequence
        self._output_sequence: HevcVideoFile = output_sequence
        self._filepath: Path = output_sequence.get_metrics_json_path()
        self._data: dict = {}
        if self._filepath.exists():
            self._data = self._read_in()

    def __hash__(self) -> int:
        return hashlib.md5(self._filepath)

    def exists(self) -> bool:
        return self._filepath.exists()

    def get_input_sequence(self) -> RawVideoSequence:
        return self._input_sequence

    def get_output_sequence(self) -> HevcVideoFile:
        return self._output_sequence

    def get_filepath(self) -> Path:
        return self._filepath

    def get_directory(self) -> Path:
        return Path(self._filepath.parent)

    def get_encoder_name(self) -> str:
        if self.exists():
            self._read_in()
        return self._data["ENCODER_NAME"]

    def set_encoder_name(self,
                         encoder_name: str) -> None:
        if self.exists():
            self._read_in()
        self._data["ENCODER_NAME"] = encoder_name
        self._write_out()

    def get_encoder_revision(self) -> str:
        if self.exists():
            self._read_in()
        return self._data["ENCODER_REVISION"]

    def set_encoder_revision(self,
                             encoder_revision: str) -> None:
        if self.exists():
            self._read_in()
        self._data["ENCODER_REVISION"] = encoder_revision
        self._write_out()

    def get_encoder_defines(self) -> list:
        if self.exists():
            self._read_in()
        return self._data["ENCODER_DEFINES"]

    def set_encoder_defines(self,
                            encoder_defines: list) -> None:
        if self.exists():
            self._read_in()
        self._data["ENCODER_DEFINES"] = encoder_defines
        self._write_out()

    def get_encoder_cmdline(self) -> str:
        if self.exists():
            self._read_in()
        return self._data["ENCODER_CMDLINE"]

    def set_encoder_cmdline(self,
                            encoder_cmdline: str) -> None:
        if self.exists():
            self._read_in()
        self._data["ENCODER_CMDLINE"] = encoder_cmdline
        self._write_out()

    def get_encoding_input(self) -> str:
        if self.exists():
            self._read_in()
        return self._data["ENCODING_INPUT"]

    def set_encoding_input(self,
                           encoding_input: str) -> None:
        if self.exists():
            self._read_in()
        self._data["ENCODING_INPUT"] = encoding_input
        self._write_out()

    def get_encoding_output(self) -> str:
        if self.exists():
            self._read_in()
        return self._data["ENCODING_OUTPUT"]

    def set_encoding_output(self,
                            encoding_output: str) -> None:
        if self.exists():
            self._read_in()
        self._data["ENCODING_OUTPUT"] = encoding_output
        self._write_out()

    def get_encoding_resolution(self) -> str:
        if self.exists():
            self._read_in()
        return self._data["ENCODING_RESOLUTION"]

    def set_encoding_resolution(self,
                                encoding_resolution: str) -> None:
        if self.exists():
            self._read_in()
        self._data["ENCODING_RESOLUTION"] = encoding_resolution
        self._write_out()

    def get_encoding_time(self) -> float:
        if self.exists():
            self._read_in()
        return self._data["ENCODING_TIME_SECONDS"]

    def set_encoding_time(self,
                          time_as_seconds: float) -> None:
        if self.exists():
            self._read_in()
        self._data["ENCODING_TIME_SECONDS"] = time_as_seconds
        self._write_out()

    def get_speedup_relative_to(self,
                                anchor) -> float:
        own_time = self.get_encoding_time()
        anchor_time = anchor.get_encoding_time()
        return anchor_time / own_time

    def get_psnr_avg(self) -> float:
        if self.exists():
            self._read_in()
        return self._data["PSNR_AVG"]

    def set_psnr_avg(self,
                     psnr_avg: float) -> None:
        if self.exists():
            self._read_in()
        self._data["PSNR_AVG"] = psnr_avg
        self._write_out()

    def get_ssim_avg(self) -> float:
        if self.exists():
            self._read_in()
        return self._data["SSIM_AVG"]

    def set_ssim_avg(self,
                     ssim_avg: float) -> None:
        if self.exists():
            self._read_in()
        self._data["SSIM_AVG"] = ssim_avg
        self._write_out()

    def _write_out(self) -> None:
        if not Path(self._filepath.parent).exists():
            Path(self._filepath.parent).mkdir(parents=True)
        try:
            with self._filepath.open("w") as file:
                json.dump(self._data, file)
        except:
            console_logger.error(f"Couldn't write metrics to file '{self._filepath}'")
            raise

    def _read_in(self) -> None:
        if self._filepath.exists():
            try:
                with self._filepath.open("r") as file:
                    self._data = json.load(file)
            except:
                console_logger.error(f"Couldn't read metrics from file '{self._filepath}'")
                raise


class Metrics:
    def __init__(self,
                 encoder_instance: EncoderBase,
                 param_sets: list,
                 sequence: RawVideoSequence):
        self.encoder: EncoderBase = encoder_instance
        self.param_sets: list = param_sets
        self.input_sequence: RawVideoSequence = sequence

    def __eq__(self, other):
        for i in range(len(self.param_sets)):
            if self.param_sets[i] != other.get_param_sets()[i]:
                return False
        return self.encoder == other.get_encoder() \
               and self.input_sequence == other.sequence

    def get_encoder(self) -> EncoderBase:
        return self.encoder

    def get_param_sets(self) -> list:
        return self.param_sets

    def get_sequence(self) -> RawVideoSequence:
        return self.input_sequence

    def get_metrics_file(self,
                         param_set: ParamSetBase) -> MetricsFile:
        return MetricsFile(
            self.input_sequence,
            self.encoder.get_output_file(self.input_sequence, param_set)
        )

    def get_bdbr_psnr(self,
                      anchor: Metrics) -> float:

        if self is anchor:
            return 0

        psnr_list = []
        anchor_psnr_list = []

        # The code duplication here is ugly, but it's simple and it works, so it will stay,
        # at least for now.

        metrics_files = [self.get_metrics_file(param_set) for param_set in self.param_sets]
        for metrics_file in metrics_files:
            psnr_list.append((
                metrics_file.get_input_sequence().get_bitrate(),
                metrics_file.get_psnr_avg()
            ))

        anchor_metrics_files = [anchor.get_metrics_file(param_set) for param_set in anchor.param_sets]
        for anchor_metrics_file in anchor_metrics_files:
            anchor_psnr_list.append((
                anchor_metrics_file.get_input_sequence().get_bitrate(),
                anchor_metrics_file.get_psnr_avg()
            ))

        return self._compute_bdbr(psnr_list, anchor_psnr_list)

    def get_bdbr_ssim(self,
                      anchor: Metrics) -> float:

        if self is anchor:
            return 0

        ssim_list = []
        anchor_ssim_list = []

        # The code duplication here is ugly, but it's simple and it works, so it will stay,
        # at least for now.

        metrics_files = [self.get_metrics_file(param_set) for param_set in self.param_sets]
        for metrics_file in metrics_files:
            ssim_list.append((
                metrics_file.get_input_sequence().get_bitrate(),
                metrics_file.get_ssim_avg()
            ))

        anchor_metrics_files = [anchor.get_metrics_file(param_set) for param_set in anchor.param_sets]
        for anchor_metrics_file in anchor_metrics_files:
            anchor_ssim_list.append((
                anchor_metrics_file.get_input_sequence().get_bitrate(),
                anchor_metrics_file.get_ssim_avg()
            ))

        return self._compute_bdbr(ssim_list, anchor_ssim_list)

    def _compute_bdbr(self,
                      bitrate_metric_tuple_list: list,
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
