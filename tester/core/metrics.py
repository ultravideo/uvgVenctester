from .cfg import *
from .log import *
from .encoderinstancebase import *
from .encodingparamsetbase import *
from .testconfiguration import *
from .videosequence import *

import functools
import hashlib
import json
import os
from vmaf.tools.bd_rate_calculator import BDrateCalculator

class Metrics:
    def __init__(self,
                 encoder_instance: EncoderInstanceBase,
                 encoding_param_set: EncodingParamSetBase,
                 input_sequence: VideoSequence):
        self.encoder_instance = encoder_instance
        self.encoding_param_set = encoding_param_set
        self.input_sequence = input_sequence

        self.directory = os.path.join(
            Cfg().encoding_output_dir_path,
            os.path.basename(encoder_instance.get_exe_path()).strip(".exe"),
            encoding_param_set.to_cmdline_str(include_quality_param=False)
        )

        base_filename: str = f"{input_sequence.get_input_filename(include_extension=False)}"
        qp_name: str = encoding_param_set.get_quality_param_name()
        qp_value: str = encoding_param_set.get_quality_param_value()
        ext_filename = f"{base_filename}_{qp_name.lower()}{qp_value}_metrics.json"
        self.filepath = os.path.join(
            self.directory,
            ext_filename
        )

        self.data: dict = {}
        if os.path.exists(self.filepath):
            self.data = self.read_in()

    def __hash__(self):
        return hashlib.md5(self.filepath)

    def get_data(self) -> dict:
        return self.data

    def file_exists(self) -> bool:
        return os.path.exists(self.filepath)

    def get_filepath(self) -> str:
        return self.filepath

    def get_directory(self) -> str:
        return self.directory

    def get_encoder_name(self) -> str:
        if self.file_exists():
            self.read_in()
        return self.data["ENCODER_NAME"]

    def set_encoder_name(self, encoder_name: str):
        if self.file_exists():
            self.read_in()
        self.data["ENCODER_NAME"] = encoder_name
        self.write_out()

    def get_encoder_revision(self) -> str:
        if self.file_exists():
            self.read_in()
        return self.data["ENCODER_REVISION"]

    def set_encoder_revision(self, encoder_revision: str):
        if self.file_exists():
            self.read_in()
        self.data["ENCODER_REVISION"] = encoder_revision
        self.write_out()

    def get_encoder_defines(self) -> list:
        if self.file_exists():
            self.read_in()
        return self.data["ENCODER_DEFINES"]

    def set_encoder_defines(self, encoder_defines: list):
        if self.file_exists():
            self.read_in()
        self.data["ENCODER_DEFINES"] = encoder_defines
        self.write_out()

    def get_encoder_cmdline(self) -> str:
        if self.file_exists():
            self.read_in()
        return self.data["ENCODER_CMDLINE"]

    def set_encoder_cmdline(self, encoder_cmdline: str):
        if self.file_exists():
            self.read_in()
        self.data["ENCODER_CMDLINE"] = encoder_cmdline
        self.write_out()

    def get_encoding_input(self) -> str:
        if self.file_exists():
            self.read_in()
        return self.data["ENCODING_INPUT"]

    def set_encoding_input(self, encoding_input: str):
        if self.file_exists():
            self.read_in()
        self.data["ENCODING_INPUT"] = encoding_input
        self.write_out()

    def get_encoding_output(self) -> str:
        if self.file_exists():
            self.read_in()
        return self.data["ENCODING_OUTPUT"]

    def set_encoding_output(self, encoding_output: str):
        if self.file_exists():
            self.read_in()
        self.data["ENCODING_OUTPUT"] = encoding_output
        self.write_out()

    def get_encoding_resolution(self) -> str:
        if self.file_exists():
            self.read_in()
        return self.data["ENCODING_RESOLUTION"]

    def set_encoding_resolution(self, encoding_resolution: str):
        if self.file_exists():
            self.read_in()
        self.data["ENCODING_RESOLUTION"] = encoding_resolution
        self.write_out()

    def get_encoding_time(self) -> float:
        if self.file_exists():
            self.read_in()
        return self.data["ENCODING_TIME_SECONDS"]

    def set_encoding_time(self, time_as_seconds: float):
        if self.file_exists():
            self.read_in()
        self.data["ENCODING_TIME_SECONDS"] = time_as_seconds
        self.write_out()

    def get_speedup_relative_to(self, anchor):
        own_time = self.get_encoding_time()
        anchor_time = anchor.get_encoding_time()
        return anchor_time / own_time

    def set_psnr_avg(self, psnr_avg: float):
        if self.file_exists():
            self.read_in()
        self.data["PSNR_AVG"] = psnr_avg
        self.write_out()

    def get_psnr_avg(self):
        if self.file_exists():
            self.read_in()
        return self.data["PSNR_AVG"]

    def set_ssim_avg(self, ssim_avg: float):
        if self.file_exists():
            self.read_in()
        self.data["SSIM_AVG"] = ssim_avg
        self.write_out()

    def get_ssim_avg(self):
        if self.file_exists():
            self.read_in()
        return self.data["SSIM_AVG"]

    def get_psnr_bdbr(self, parent_config: TestConfiguration, anchor_config: TestConfiguration, sequence: VideoSequence):

        if parent_config is anchor_config:
            return 0

        parent_bitrate_ssim_list = []
        anchor_bitrate_ssim_list = []

        parent_encoder_instance = parent_config.get_encoder_instance()
        for parent_param_set in parent_config.get_encoding_param_sets():
            parent_param_set_metrics = Metrics(parent_encoder_instance, parent_param_set, sequence)
            ssim = parent_param_set_metrics.get_ssim_avg()
            output_filepath = sequence.get_output_filepath(parent_encoder_instance, parent_param_set)
            bitrate = (os.path.getsize(output_filepath) * 8) // sequence.get_duration_seconds()
            parent_bitrate_ssim_list.append((bitrate, ssim))

        anchor_encoder_instance = anchor_config.get_encoder_instance()
        for anchor_param_set in anchor_config.get_encoding_param_sets():
            anchor_param_set_metrics = Metrics(anchor_encoder_instance, anchor_param_set, sequence)
            ssim = anchor_param_set_metrics.get_ssim_avg()
            output_filepath = sequence.get_output_filepath(anchor_encoder_instance, anchor_param_set)
            bitrate = (os.path.getsize(output_filepath) * 8) // sequence.get_duration_seconds()
            anchor_bitrate_ssim_list.append((bitrate, ssim))

        def bitrate_asc_sort(x, y):
            return -1 if x[0] < y[0] else 1

        sort_key = functools.cmp_to_key(bitrate_asc_sort)

        bd_rate_calc = BDrateCalculator()
        return bd_rate_calc.CalcBDRate(
            sorted(parent_bitrate_ssim_list, key=sort_key),
            sorted(anchor_bitrate_ssim_list, key=sort_key)
        )

    def get_ssim_bdbr(self, parent_config: TestConfiguration, anchor_config: TestConfiguration,
                          sequence: VideoSequence):

        if parent_config is anchor_config:
            return 0

        parent_bitrate_psnr_list = []
        anchor_bitrate_psnr_list = []

        parent_encoder_instance = parent_config.get_encoder_instance()
        for parent_param_set in parent_config.get_encoding_param_sets():
            parent_param_set_metrics = Metrics(parent_encoder_instance, parent_param_set, sequence)
            psnr = parent_param_set_metrics.get_psnr_avg()
            output_filepath = sequence.get_output_filepath(parent_encoder_instance, parent_param_set)
            bitrate = (os.path.getsize(output_filepath) * 8) // sequence.get_duration_seconds()
            parent_bitrate_psnr_list.append((bitrate, psnr))

        anchor_encoder_instance = anchor_config.get_encoder_instance()
        for anchor_param_set in anchor_config.get_encoding_param_sets():
            anchor_param_set_metrics = Metrics(anchor_encoder_instance, anchor_param_set, sequence)
            psnr = anchor_param_set_metrics.get_psnr_avg()
            output_filepath = sequence.get_output_filepath(anchor_encoder_instance, anchor_param_set)
            bitrate = (os.path.getsize(output_filepath) * 8) // sequence.get_duration_seconds()
            anchor_bitrate_psnr_list.append((bitrate, psnr))

        def bitrate_asc_sort(x, y):
            return -1 if x[0] < y[0] else 1

        sort_key = functools.cmp_to_key(bitrate_asc_sort)

        bd_rate_calc = BDrateCalculator()
        return bd_rate_calc.CalcBDRate(
            sorted(parent_bitrate_psnr_list, key=sort_key),
            sorted(anchor_bitrate_psnr_list, key=sort_key)
        )

    def write_out(self):
        if not os.path.exists(self.directory):
            os.makedirs(self.directory)
        try:
            with open(self.filepath, "w") as file:
                json.dump(self.data, file)
        except:
            console_logger.error(f"Couldn't write metrics to file '{self.filepath}'")
            raise

    def read_in(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r") as file:
                    self.data = json.load(file)
            except:
                console_logger.error(f"Couldn't read metrics from file '{self.filepath}'")
                raise
