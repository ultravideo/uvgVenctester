#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""This module defines functionality related to computing video quality metrics."""

from .cfg import *
from .log import *
from .encoderinstancebase import *
from .encodingparamsetbase import *
from .videosequence import *

import functools
import hashlib
import json
import os
from vmaf.tools.bd_rate_calculator import BDrateCalculator

class SubMetrics:
    """Represents the quality metrics of a given sequence encoded with a given subtest configuration.
    The metrics are stored in a file automatically stored in a file."""
    def __init__(self,
                 encoder_instance: EncoderInstanceBase,
                 encoding_param_set: EncodingParamSetBase,
                 input_sequence: VideoSequence):
        """@param encoder_instance The encoder used in the subtest.
        @param encoding_param_set The parameter set used in the subtest.
        @param input_sequence The video sequence encoded with the given encoder and parameter set."""
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

    def file_exists(self) -> bool:
        """Returns True if the file in which the metrics are stored exists."""
        return os.path.exists(self.filepath)

    def get_encoder(self) -> EncoderInstanceBase:
        """Returns the encoder instance tied to the object."""
        return self.encoder_instance

    def get_param_set(self) -> EncodingParamSetBase:
        """Returns the parameter set tied to the object."""
        return self.encoding_param_set

    def get_sequence(self) -> VideoSequence:
        """Returns the input video sequence tied to the object."""
        return self.input_sequence

    def get_filepath(self) -> str:
        """Returns the absolute path of the file in which the metrics are stored."""
        return self.filepath

    def get_directory(self) -> str:
        """Returns the absolute path of the directory in which the metrics are stored."""
        return self.directory_path

    def get_encoder_name(self) -> str:
        """Returns the name of the encoder used in the subtest."""
        if self.file_exists():
            self._read_in()
        return self.data["ENCODER_NAME"]

    def set_encoder_name(self, encoder_name: str):
        """Sets the name of the encoder used in the subtest."""
        if self.file_exists():
            self._read_in()
        self.data["ENCODER_NAME"] = encoder_name
        self._write_out()

    def get_encoder_revision(self) -> str:
        """Returns the revision of the encoder used in the subtest."""
        if self.file_exists():
            self._read_in()
        return self.data["ENCODER_REVISION"]

    def set_encoder_revision(self, encoder_revision: str):
        """Sets the revision of the encoder used in the subtest."""
        if self.file_exists():
            self._read_in()
        self.data["ENCODER_REVISION"] = encoder_revision
        self._write_out()

    def get_encoder_defines(self) -> list:
        """Returns the predefined preprocessor symbols used when the encoder executable was built."""
        if self.file_exists():
            self._read_in()
        return self.data["ENCODER_DEFINES"]

    def set_encoder_defines(self, encoder_defines: list):
        """Sets the predefined preprocessor symbols used when the encoder executable was built."""
        if self.file_exists():
            self._read_in()
        self.data["ENCODER_DEFINES"] = encoder_defines
        self._write_out()

    def get_encoder_cmdline(self) -> str:
        """Returns the command executed on the command line when the encoding
        was performed."""
        if self.file_exists():
            self._read_in()
        return self.data["ENCODER_CMDLINE"]

    def set_encoder_cmdline(self, encoder_cmdline: str):
        """Sets the command executed on the command line when the encoding
        was performed."""
        if self.file_exists():
            self._read_in()
        self.data["ENCODER_CMDLINE"] = encoder_cmdline
        self._write_out()

    def get_encoding_input(self) -> str:
        """Returns the name of the input sequence that was encoded."""
        if self.file_exists():
            self._read_in()
        return self.data["ENCODING_INPUT"]

    def set_encoding_input(self, encoding_input: str):
        """Sets the name of the input sequence that was encoded."""
        if self.file_exists():
            self._read_in()
        self.data["ENCODING_INPUT"] = encoding_input
        self._write_out()

    def get_encoding_output(self) -> str:
        """Returns the name of the encoded output file."""
        if self.file_exists():
            self._read_in()
        return self.data["ENCODING_OUTPUT"]

    def set_encoding_output(self, encoding_output: str):
        """Sets the name of the encoded output file."""
        if self.file_exists():
            self._read_in()
        self.data["ENCODING_OUTPUT"] = encoding_output
        self._write_out()

    def get_encoding_resolution(self) -> str:
        """Returns the resolution of the input/output sequences."""
        if self.file_exists():
            self._read_in()
        return self.data["ENCODING_RESOLUTION"]

    def set_encoding_resolution(self, encoding_resolution: str):
        """Sets the resolution of the input/output sequences."""
        if self.file_exists():
            self._read_in()
        self.data["ENCODING_RESOLUTION"] = encoding_resolution
        self._write_out()

    def get_encoding_time(self) -> float:
        """Returns the encoding time in seconds."""
        if self.file_exists():
            self._read_in()
        return self.data["ENCODING_TIME_SECONDS"]

    def set_encoding_time(self, time_as_seconds: float):
        """Sets the encoding time in seconds."""
        if self.file_exists():
            self._read_in()
        self.data["ENCODING_TIME_SECONDS"] = time_as_seconds
        self._write_out()

    def get_speedup_relative_to(self, anchor) -> float:
        """Returns the speedup relative to the anchor.
        @param anchor The metrics object to compare to."""
        own_time = self.get_encoding_time()
        anchor_time = anchor.get_encoding_time()
        return anchor_time / own_time

    def get_psnr_avg(self) -> float:
        """Returns the average PNSR."""
        if self.file_exists():
            self._read_in()
        return self.data["PSNR_AVG"]

    def set_psnr_avg(self, psnr_avg: float):
        """Sets the average PNSR."""
        if self.file_exists():
            self._read_in()
        self.data["PSNR_AVG"] = psnr_avg
        self._write_out()

    def get_ssim_avg(self) -> float:
        """Returns the average SSIM."""
        if self.file_exists():
            self._read_in()
        return self.data["SSIM_AVG"]

    def set_ssim_avg(self, ssim_avg: float):
        """Sets the average SSIM."""
        if self.file_exists():
            self._read_in()
        self.data["SSIM_AVG"] = ssim_avg
        self._write_out()

    def _write_out(self):
        """Writes the data tied to the object into the file as JSON."""
        if not os.path.exists(self.directory_path):
            os.makedirs(self.directory_path)
        try:
            with open(self.filepath, "w") as file:
                json.dump(self.data, file)
        except:
            console_logger.error(f"Couldn't write metrics to file '{self.filepath}'")
            raise

    def _read_in(self):
        """Reads the data tied to the object into the file."""
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r") as file:
                    self.data = json.load(file)
            except:
                console_logger.error(f"Couldn't read metrics from file '{self.filepath}'")
                raise



class Metrics:
    """Represents the quality metrics of a given set of video sequences encoded with a given
    test configuration. """
    def __init__(self,
                 encoder_instance: EncoderInstanceBase,
                 param_sets: list,
                 sequence: VideoSequence):
        self.encoder: EncoderInstanceBase = encoder_instance
        self.param_sets: list = param_sets
        self.sequence: VideoSequence = sequence
        self.submetrics: dict = {
            param_set: SubMetrics(self.encoder, param_set, self.sequence) for param_set in param_sets
        }

    def __eq__(self, other):
        for i in range(len(self.param_sets)):
            if self.param_sets[i] != other.get_param_sets()[i]:
                return False
        return self.encoder == other.get_encoder() \
               and self.sequence == other.sequence

    def get_encoder(self) -> EncoderInstanceBase:
        """Returns the encoder instance tied to the object."""
        return self.encoder

    def get_param_sets(self) -> list:
        """Returns the parameter sets tied to the object."""
        return self.param_sets

    def get_sequence(self) -> VideoSequence:
        """Returns the video sequence tied to the object."""
        return self.sequence

    def get_submetrics_list(self) -> list:
        """Returns the list of submetrics tied to the object."""
        return [value for key, value in self.submetrics.items()]

    def get_submetrics_of(self, param_set: EncodingParamSetBase) -> SubMetrics:
        """Returns a single set of submetrics corresponding with the given parameter set.
        @param param_set The parameter set to which the returned submetrics are tied."""
        return self.submetrics[param_set]

    def get_bdbr_psnr_relative_to(self, anchor_metrics) -> float:
        """Returns BD-BR based on PSNR values in relation to the anchor metrics.
        @param anchor_metrics The anchor set of metrics with relation to which the comparison
        is made."""

        if self is anchor_metrics:
            return 0

        psnr_list = []
        anchor_psnr_list = []

        # The code duplication here is ugly, but it's simple and it works, so it will stay,
        # at least for now.

        for submetrics in self.submetrics.values():
            sequence = submetrics.get_sequence()
            output_filepath = sequence.get_output_filepath(
                self.encoder,
                submetrics.get_param_set()
            )
            bitrate = (os.path.getsize(output_filepath) * 8)\
                      / sequence.get_duration_seconds()
            psnr = submetrics.get_psnr_avg()
            psnr_list.append((bitrate, psnr))

        for anchor_submetrics in anchor_metrics.get_submetrics_list():
            sequence = anchor_submetrics.get_sequence()
            output_filepath = sequence.get_output_filepath(
                anchor_submetrics.get_encoder(),
                anchor_submetrics.get_param_set()
            )
            bitrate = (os.path.getsize(output_filepath) * 8)\
                      / sequence.get_duration_seconds()
            psnr = anchor_submetrics.get_psnr_avg()
            anchor_psnr_list.append((bitrate, psnr))

        return self._compute_bdbr(psnr_list, anchor_psnr_list)

    def get_bdbr_ssim_relative_to(self, anchor_metrics) -> float:
        """Returns BD-BR based on SSIM values in relation to the anchor metrics.
        @param anchor_metrics The anchor set of metrics with relation to which the comparison
        is made."""

        if self == anchor_metrics:
            return 0

        ssim_list = []
        anchor_ssim_list = []

        for submetrics in self.get_submetrics_list():
            sequence = submetrics.get_sequence()
            output_filepath = sequence.get_output_filepath(
                self.encoder,
                submetrics.get_param_set()
            )
            bitrate = (os.path.getsize(output_filepath) * 8)\
                      / sequence.get_duration_seconds()
            ssim = submetrics.get_ssim_avg()
            ssim_list.append((bitrate, ssim))

        for anchor_submetrics in anchor_metrics.get_submetrics_list():
            sequence = anchor_submetrics.get_sequence()
            output_filepath = sequence.get_output_filepath(
                anchor_submetrics.get_encoder(),
                anchor_submetrics.get_param_set()
            )
            bitrate = (os.path.getsize(output_filepath) * 8)\
                      / sequence.get_duration_seconds()
            ssim = anchor_submetrics.get_ssim_avg()
            anchor_ssim_list.append((bitrate, ssim))

        return self._compute_bdbr(ssim_list, anchor_ssim_list)

    def _compute_bdbr(self, metrics_list: list, anchor_metrics_list: list):
        """Just a helper function to reduce the amount of duplicate code."""

        def metrics_list_bitrate_asc_sort(a, b):
            """Orders a metrics list such that they are in ascending order in terms of bitrate."""
            return -1 if a[0] < b[0] else 1
        sort_key = functools.cmp_to_key(metrics_list_bitrate_asc_sort)

        metrics_list = sorted(metrics_list, key=sort_key)
        anchor_metrics_list = sorted(anchor_metrics_list, key=sort_key)

        bdbr = BDrateCalculator().CalcBDRate(metrics_list, anchor_metrics_list)
        return bdbr
