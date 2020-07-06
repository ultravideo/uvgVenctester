import test
from core.cfg import *
from core.log import *

import hashlib
import json
import os

class Metrics:
    def __init__(self,
                 encoder_instance: test.EncoderInstanceBase,
                 encoding_param_set: test.EncodingParamSetBase,
                 input_sequence: test.VideoSequence):
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
