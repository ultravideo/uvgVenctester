#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""This module defines functionality related to computing video quality metrics."""

from __future__ import annotations

from tester.core.cfg import *
from tester.core.videosequence import *
from tester.encoders.base import *

import functools
import hashlib
import json
from pathlib import Path
from vmaf.tools.bd_rate_calculator import BDrateCalculator

class MetricsFile:
    def __init__(self,
                 encoder_instance: EncoderBase,
                 encoding_param_set: ParamSetBase,
                 input_sequence: VideoSequence):
        self.encoder_instance = encoder_instance
        self.encoding_param_set = encoding_param_set
        self.input_sequence = input_sequence

        self.filepath: Path = encoder_instance.get_output_subdir(encoding_param_set) \
            / f"{input_sequence.get_input_filename(include_extension=False)}_" \
              f"{encoding_param_set.get_quality_param_name()}" \
              f"{encoding_param_set.get_quality_param_value()}"

        self.data: dict = {}
        if self.filepath.exists():
            self.data = self._read_in()

    def __hash__(self) -> int:
        return hashlib.md5(self.filepath)

    def exists(self) -> bool:
        return self.filepath.exists()

    def get_encoder(self) -> EncoderBase:
        return self.encoder_instance

    def get_param_set(self) -> ParamSetBase:
        return self.encoding_param_set

    def get_sequence(self) -> VideoSequence:
        return self.input_sequence

    def get_filepath(self) -> Path:
        return self.filepath

    def get_directory(self) -> Path:
        return Path(self.filepath.parent)

    def get_encoder_name(self) -> str:
        if self.exists():
            self._read_in()
        return self.data["ENCODER_NAME"]

    def set_encoder_name(self,
                         encoder_name: str) -> None:
        if self.exists():
            self._read_in()
        self.data["ENCODER_NAME"] = encoder_name
        self._write_out()

    def get_encoder_revision(self) -> str:
        if self.exists():
            self._read_in()
        return self.data["ENCODER_REVISION"]

    def set_encoder_revision(self,
                             encoder_revision: str) -> None:
        if self.exists():
            self._read_in()
        self.data["ENCODER_REVISION"] = encoder_revision
        self._write_out()

    def get_encoder_defines(self) -> list:
        if self.exists():
            self._read_in()
        return self.data["ENCODER_DEFINES"]

    def set_encoder_defines(self,
                            encoder_defines: list) -> None:
        if self.exists():
            self._read_in()
        self.data["ENCODER_DEFINES"] = encoder_defines
        self._write_out()

    def get_encoder_cmdline(self) -> str:
        if self.exists():
            self._read_in()
        return self.data["ENCODER_CMDLINE"]

    def set_encoder_cmdline(self,
                            encoder_cmdline: str) -> None:
        if self.exists():
            self._read_in()
        self.data["ENCODER_CMDLINE"] = encoder_cmdline
        self._write_out()

    def get_encoding_input(self) -> str:
        if self.exists():
            self._read_in()
        return self.data["ENCODING_INPUT"]

    def set_encoding_input(self,
                           encoding_input: str) -> None:
        if self.exists():
            self._read_in()
        self.data["ENCODING_INPUT"] = encoding_input
        self._write_out()

    def get_encoding_output(self) -> str:
        if self.exists():
            self._read_in()
        return self.data["ENCODING_OUTPUT"]

    def set_encoding_output(self,
                            encoding_output: str) -> None:
        if self.exists():
            self._read_in()
        self.data["ENCODING_OUTPUT"] = encoding_output
        self._write_out()

    def get_encoding_resolution(self) -> str:
        if self.exists():
            self._read_in()
        return self.data["ENCODING_RESOLUTION"]

    def set_encoding_resolution(self,
                                encoding_resolution: str) -> None:
        if self.exists():
            self._read_in()
        self.data["ENCODING_RESOLUTION"] = encoding_resolution
        self._write_out()

    def get_encoding_time(self) -> float:
        if self.exists():
            self._read_in()
        return self.data["ENCODING_TIME_SECONDS"]

    def set_encoding_time(self,
                          time_as_seconds: float) -> None:
        if self.exists():
            self._read_in()
        self.data["ENCODING_TIME_SECONDS"] = time_as_seconds
        self._write_out()

    def get_speedup_relative_to(self,
                                anchor) -> float:
        own_time = self.get_encoding_time()
        anchor_time = anchor.get_encoding_time()
        return anchor_time / own_time

    def get_psnr_avg(self) -> float:
        if self.exists():
            self._read_in()
        return self.data["PSNR_AVG"]

    def set_psnr_avg(self,
                     psnr_avg: float) -> None:
        if self.exists():
            self._read_in()
        self.data["PSNR_AVG"] = psnr_avg
        self._write_out()

    def get_ssim_avg(self) -> float:
        if self.exists():
            self._read_in()
        return self.data["SSIM_AVG"]

    def set_ssim_avg(self,
                     ssim_avg: float) -> None:
        if self.exists():
            self._read_in()
        self.data["SSIM_AVG"] = ssim_avg
        self._write_out()

    def _write_out(self) -> None:
        if not Path(self.filepath.parent).exists():
            Path(self.filepath.parent).mkdir(parents=True)
        try:
            with self.filepath.open("w") as file:
                json.dump(self.data, file)
        except:
            console_logger.error(f"Couldn't write metrics to file '{self.filepath}'")
            raise

    def _read_in(self) -> None:
        if self.filepath.exists():
            try:
                with self.filepath.open("r") as file:
                    self.data = json.load(file)
            except:
                console_logger.error(f"Couldn't read metrics from file '{self.filepath}'")
                raise


class Metrics:
    def __init__(self,
                 encoder_instance: EncoderBase,
                 param_sets: list,
                 sequence: VideoSequence):
        self.encoder: EncoderBase = encoder_instance
        self.param_sets: list = param_sets
        self.sequence: VideoSequence = sequence

    def __eq__(self, other):
        for i in range(len(self.param_sets)):
            if self.param_sets[i] != other.get_param_sets()[i]:
                return False
        return self.encoder == other.get_encoder() \
               and self.sequence == other.sequence

    def get_encoder(self) -> EncoderBase:
        return self.encoder

    def get_param_sets(self) -> list:
        return self.param_sets

    def get_sequence(self) -> VideoSequence:
        return self.sequence

    def get_metrics_file(self,
                         param_set: ParamSetBase) -> MetricsFile:
        return MetricsFile(self.encoder, param_set, self.sequence)

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
                metrics_file.get_sequence().get_bitrate(),
                metrics_file.get_psnr_avg()
            ))

        anchor_metrics_files = [anchor.get_metrics_file(param_set) for param_set in anchor.param_sets]
        for anchor_metrics_file in anchor_metrics_files:
            anchor_psnr_list.append((
                anchor_metrics_file.get_sequence().get_bitrate(),
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
                metrics_file.get_sequence().get_bitrate(),
                metrics_file.get_ssim_avg()
            ))

        anchor_metrics_files = [anchor.get_metrics_file(param_set) for param_set in anchor.param_sets]
        for anchor_metrics_file in anchor_metrics_files:
            anchor_ssim_list.append((
                anchor_metrics_file.get_sequence().get_bitrate(),
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
