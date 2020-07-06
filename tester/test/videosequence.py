from core.log import console_logger
from .encoderinstancebase import *
from .encodingparamsetbase import *

import hashlib
import re
import os

class VideoSequence:
    def __init__(self, filepath: str, width: int = None, height: int = None):
        assert (not width and not height) or (width and height)
        assert os.path.exists(filepath)
        self.input_filepath = filepath
        self.input_filename = os.path.basename(self.input_filepath)
        self.base_filename = self.input_filename.strip(".yuv")
        self.width = width
        self.height = height

        if not self.width and not self.height:
            self.width, self.height = self.guess_resolution()

        hash = hashlib.md5()
        hash.update(self.input_filepath.encode())
        self.hash = int(hash.hexdigest(), 16)

    def __hash__(self):
        return self.hash

    def get_base_filename(self) -> str:
        return self.base_filename

    def get_input_filepath(self) -> str:
        return self.input_filepath

    def get_input_filename(self, include_extension=True) -> str:
        if include_extension:
            return self.input_filename
        else:
            if "." in self.input_filename:
                split_parts: list = self.input_filename.split(".")
                return ".".join(split_parts[:len(split_parts) - 1])
            else:
                return self.input_filename

    def get_output_filename(self, encoder_instance: EncoderInstanceBase, param_set: EncodingParamSetBase) -> str:
        return f"{self.get_base_filename()}_{param_set.get_quality_param_name().lower()}{param_set.get_quality_param_value()}.hevc"

    def get_output_filepath(self, encoder_instance: EncoderInstanceBase, param_set: EncodingParamSetBase) -> str:
        return os.path.join(
            encoder_instance.get_output_subdir(param_set),
            self.get_output_filename(encoder_instance, param_set)
        )

    def get_psnr_log_filename(self, encoder_instance: EncoderInstanceBase, param_set: EncodingParamSetBase) -> str:
        return self.get_output_filename(encoder_instance, param_set).replace(".hevc", "_psnr_log.txt")

    def get_ssim_log_filename(self, encoder_instance: EncoderInstanceBase, param_set: EncodingParamSetBase) -> str:
        return self.get_output_filename(encoder_instance, param_set).replace(".hevc", "_ssim_log.txt")

    def get_psnr_log_filepath(self, encoder_instance: EncoderInstanceBase, param_set: EncodingParamSetBase) -> str:
        return os.path.join(
            encoder_instance.get_output_subdir(param_set),
            self.get_psnr_log_filename(encoder_instance, param_set)
        )

    def get_ssim_log_filepath(self, encoder_instance: EncoderInstanceBase, param_set: EncodingParamSetBase) -> str:
        return os.path.join(
            encoder_instance.get_output_subdir(param_set),
            self.get_ssim_log_filename(encoder_instance, param_set)
        )

    def get_width(self) -> int:
        return self.width

    def get_height(self) -> int:
        return self.height

    def get_class(self) -> str:
        for letter in "A", "B", "C", "D", "E", "F":
            sequence_class: str = f"hevc-{letter}"
            if sequence_class in self.input_filepath:
                return sequence_class
        return "-"

    def guess_resolution(self) -> (int, int):
        # The following pattern is equal to "<width>x<height> preceded by non-integers".
        resolution_pattern: re.Pattern = re.compile(r"^[^0-9]+([0-9]+)x([0-9]+).*$")
        match: re.Match = resolution_pattern.fullmatch(self.input_filepath)
        if match:
            return int(match.groups()[0]), int(match.groups()[1])
        else:
            console_logger.error(f"The name of the file '{self.input_filepath}' doesn't include the video "
                                 f"resolution (expected format: <width>x<height>)")
            raise RuntimeError
