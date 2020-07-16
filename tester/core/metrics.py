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
import os
from vmaf.tools.bd_rate_calculator import BDrateCalculator

class MetricsFile:
    def __init__(self,
                 encoder_instance: EncoderInstanceBase,
                 encoding_param_set: EncodingParamSetBase,
                 input_sequence: VideoSequence):
        self.encoder_instance = encoder_instance
        self.encoding_param_set = encoding_param_set
        self.input_sequence = input_sequence

        self.directory_path = os.path.join(
            Cfg().encoding_output_dir_path,
            os.path.basename(encoder_instance.get_exe_path()).strip(".exe"),
            encoding_param_set.to_cmdline_str(include_quality_param=False)
        )

        base_filename: str = f"{input_sequence.get_input_filename(include_extension=False)}"
        qp_name: str = encoding_param_set.get_quality_param_name()
        qp_value: int = encoding_param_set.get_quality_param_value()
        ext_filename = f"{base_filename}_{qp_name.lower()}{qp_value}_metrics.json"
        self.filepath = os.path.join(
            self.directory_path,
            ext_filename
        )

        self.data: dict = {}
        if os.path.exists(self.filepath):
            self.data = self._read_in()

    def __hash__(self):
        return hashlib.md5(self.filepath)

    def exists(self) -> bool:
        return os.path.exists(self.filepath)

    def get_encoder(self) -> EncoderInstanceBase:
        return self.encoder_instance

    def get_param_set(self) -> EncodingParamSetBase:
        return self.encoding_param_set

    def get_sequence(self) -> VideoSequence:
        return self.input_sequence

    def get_filepath(self) -> str:
        return self.filepath

    def get_directory(self) -> str:
        return self.directory_path

    def get_encoder_name(self) -> str:
        if self.exists():
            self._read_in()
        return self.data["ENCODER_NAME"]

    def set_encoder_name(self, encoder_name: str):
        if self.exists():
            self._read_in()
        self.data["ENCODER_NAME"] = encoder_name
        self._write_out()

    def get_encoder_revision(self) -> str:
        if self.exists():
            self._read_in()
        return self.data["ENCODER_REVISION"]

    def set_encoder_revision(self, encoder_revision: str):
        if self.exists():
            self._read_in()
        self.data["ENCODER_REVISION"] = encoder_revision
        self._write_out()

    def get_encoder_defines(self) -> list:
        if self.exists():
            self._read_in()
        return self.data["ENCODER_DEFINES"]

    def set_encoder_defines(self, encoder_defines: list):
        if self.exists():
            self._read_in()
        self.data["ENCODER_DEFINES"] = encoder_defines
        self._write_out()

    def get_encoder_cmdline(self) -> str:
        if self.exists():
            self._read_in()
        return self.data["ENCODER_CMDLINE"]

    def set_encoder_cmdline(self, encoder_cmdline: str):
        if self.exists():
            self._read_in()
        self.data["ENCODER_CMDLINE"] = encoder_cmdline
        self._write_out()

    def get_encoding_input(self) -> str:
        if self.exists():
            self._read_in()
        return self.data["ENCODING_INPUT"]

    def set_encoding_input(self, encoding_input: str):
        if self.exists():
            self._read_in()
        self.data["ENCODING_INPUT"] = encoding_input
        self._write_out()

    def get_encoding_output(self) -> str:
        if self.exists():
            self._read_in()
        return self.data["ENCODING_OUTPUT"]

    def set_encoding_output(self, encoding_output: str):
        if self.exists():
            self._read_in()
        self.data["ENCODING_OUTPUT"] = encoding_output
        self._write_out()

    def get_encoding_resolution(self) -> str:
        if self.exists():
            self._read_in()
        return self.data["ENCODING_RESOLUTION"]

    def set_encoding_resolution(self, encoding_resolution: str):
        if self.exists():
            self._read_in()
        self.data["ENCODING_RESOLUTION"] = encoding_resolution
        self._write_out()

    def get_encoding_time(self) -> float:
        if self.exists():
            self._read_in()
        return self.data["ENCODING_TIME_SECONDS"]

    def set_encoding_time(self, time_as_seconds: float):
        if self.exists():
            self._read_in()
        self.data["ENCODING_TIME_SECONDS"] = time_as_seconds
        self._write_out()

    def get_speedup_relative_to(self, anchor) -> float:
        own_time = self.get_encoding_time()
        anchor_time = anchor.get_encoding_time()
        return anchor_time / own_time

    def get_psnr_avg(self) -> float:
        if self.exists():
            self._read_in()
        return self.data["PSNR_AVG"]

    def set_psnr_avg(self, psnr_avg: float):
        if self.exists():
            self._read_in()
        self.data["PSNR_AVG"] = psnr_avg
        self._write_out()

    def get_ssim_avg(self) -> float:
        if self.exists():
            self._read_in()
        return self.data["SSIM_AVG"]

    def set_ssim_avg(self, ssim_avg: float):
        if self.exists():
            self._read_in()
        self.data["SSIM_AVG"] = ssim_avg
        self._write_out()

    def _write_out(self):
        if not os.path.exists(self.directory_path):
            os.makedirs(self.directory_path)
        try:
            with open(self.filepath, "w") as file:
                json.dump(self.data, file)
        except:
            console_logger.error(f"Couldn't write metrics to file '{self.filepath}'")
            raise

    def _read_in(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r") as file:
                    self.data = json.load(file)
            except:
                console_logger.error(f"Couldn't read metrics from file '{self.filepath}'")
                raise


class Metrics:
    def __init__(self,
                 encoder_instance: EncoderInstanceBase,
                 param_sets: list,
                 sequence: VideoSequence):
        self.encoder: EncoderInstanceBase = encoder_instance
        self.param_sets: list = param_sets
        self.sequence: VideoSequence = sequence

    def __eq__(self, other):
        for i in range(len(self.param_sets)):
            if self.param_sets[i] != other.get_param_sets()[i]:
                return False
        return self.encoder == other.get_encoder() \
               and self.sequence == other.sequence

    def get_encoder(self) -> EncoderInstanceBase:
        return self.encoder

    def get_param_sets(self) -> list:
        return self.param_sets

    def get_sequence(self) -> VideoSequence:
        return self.sequence

    def get_metrics_file(self, param_set: EncodingParamSetBase) -> MetricsFile:
        return MetricsFile(self.encoder, param_set, self.sequence)

    def get_bdbr_psnr(self, anchor: Metrics) -> float:

        if self is anchor:
            return 0

        psnr_list = []
        anchor_psnr_list = []

        # The code duplication here is ugly, but it's simple and it works, so it will stay,
        # at least for now.

        metrics_files = [self.get_metrics_file(param_set) for param_set in self.param_sets]
        for metrics_file in metrics_files:
            sequence = metrics_file.get_sequence()
            output_filepath = sequence.get_output_filepath(
                self.encoder,
                metrics_file.get_param_set()
            )
            bitrate = (os.path.getsize(output_filepath) * 8)\
                      / sequence.get_duration_seconds()
            psnr = metrics_file.get_psnr_avg()
            psnr_list.append((bitrate, psnr))

        anchor_metrics_files = [anchor.get_metrics_file(param_set) for param_set in anchor.param_sets]
        for anchor_metrics_file in anchor_metrics_files:
            sequence = anchor_metrics_file.get_sequence()
            output_filepath = sequence.get_output_filepath(
                anchor_metrics_file.get_encoder(),
                anchor_metrics_file.get_param_set()
            )
            bitrate = (os.path.getsize(output_filepath) * 8)\
                      / sequence.get_duration_seconds()
            psnr = anchor_metrics_file.get_psnr_avg()
            anchor_psnr_list.append((bitrate, psnr))

        return self._compute_bdbr(psnr_list, anchor_psnr_list)

    def get_bdbr_ssim(self, anchor: Metrics) -> float:

        if self is anchor:
            return 0

        ssim_list = []
        anchor_ssim_list = []

        # The code duplication here is ugly, but it's simple and it works, so it will stay,
        # at least for now.

        metrics_files = [self.get_metrics_file(param_set) for param_set in self.param_sets]
        for metrics_file in metrics_files:
            sequence = metrics_file.get_sequence()
            output_filepath = sequence.get_output_filepath(
                self.encoder,
                metrics_file.get_param_set()
            )
            bitrate = (os.path.getsize(output_filepath) * 8)\
                      / sequence.get_duration_seconds()
            ssim = metrics_file.get_ssim_avg()
            ssim_list.append((bitrate, ssim))

        anchor_metrics_files = [anchor.get_metrics_file(param_set) for param_set in anchor.param_sets]
        for anchor_metrics_file in anchor_metrics_files:
            sequence = anchor_metrics_file.get_sequence()
            output_filepath = sequence.get_output_filepath(
                anchor_metrics_file.get_encoder(),
                anchor_metrics_file.get_param_set()
            )
            bitrate = (os.path.getsize(output_filepath) * 8)\
                      / sequence.get_duration_seconds()
            ssim = anchor_metrics_file.get_ssim_avg()
            anchor_ssim_list.append((bitrate, ssim))

        return self._compute_bdbr(ssim_list, anchor_ssim_list)

    def _compute_bdbr(self, bitrate_metric_tuple_list: list, anchor_bitrate_metric_tuple_list: list):

        def bitrate_metric_tuple_list_asc_sort_by_bitrate(a, b):
            return -1 if a[0] < b[0] else 1
        sort_key = functools.cmp_to_key(bitrate_metric_tuple_list_asc_sort_by_bitrate)

        bitrate_metric_tuple_list = sorted(bitrate_metric_tuple_list, key=sort_key)
        anchor_bitrate_metric_tuple_list = sorted(anchor_bitrate_metric_tuple_list, key=sort_key)

        bdbr = BDrateCalculator().CalcBDRate(
            bitrate_metric_tuple_list,
            anchor_bitrate_metric_tuple_list)
        return bdbr
