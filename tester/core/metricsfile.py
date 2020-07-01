import test
from core.cfg import *
from core.log import *

import json
import os
import pathlib

class MetricsFile:
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
            encoding_param_set.to_cmdline_str(include_quality_param=False))

        base_filename: str = f"{input_sequence.get_input_filename(include_extension=False)}"
        qp_name: str = encoding_param_set.get_quality_param_name()
        qp_value: str = encoding_param_set.get_quality_param_value()
        ext_filename = f"{base_filename}_{qp_name.lower()}{qp_value}_metrics.json"
        self.filepath = os.path.join(
            self.directory,
            ext_filename
        )

        self.results: dict = {}
        self.results["ENCODER_NAME"] = encoder_instance.get_encoder_name()
        self.results["ENCODER_REVISION"] = encoder_instance.get_revision()
        self.results["ENCODER_DEFINES"] = encoder_instance.get_defines()
        self.results["ENCODER_CMDLINE"] = encoding_param_set.to_cmdline_str()
        self.results["ENCODING_INPUT"] = input_sequence.input_filename
        self.results["ENCODING_OUTPUT"] = f"{input_sequence.get_input_filename(include_extension=False)}.hevc"
        self.results["ENCODING_RESOLUTION"] = f"{input_sequence.width}x{input_sequence.height}"
        self.write_out()

    def set_encoding_time(self, time_as_seconds: float):
        self.results["ENCODING_TIME_SECONDS"] = time_as_seconds
        self.write_out()

    def write_out(self):
        if not os.path.exists(self.directory):
            os.makedirs(self.directory)
        try:
            with open(self.filepath, "w") as file:
                json.dump(self.results, file)
        except:
            console_logger.error(f"Couldn't write metrics to file '{self.filepath}'")
            raise

    def read_in(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r") as file:
                    self.results = json.load(file)
            except:
                console_logger.error(f"Couldn't read metrics from file '{self.filepath}'")
