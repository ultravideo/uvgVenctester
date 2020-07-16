from tester.encoders.base import *
from tester.core.log import *

import hashlib
import re
import os

class VideoSequence:

    PIXEL_FORMATS: dict = {
        # (chroma, bits per pixel) : pixel format
        (400, 8): "gray",
        (400, 10): "gray16le",
        (420, 8): "yuv420p",
        (420, 10): "yuv420p10le",
    }

    def __init__(self,
                 filepath: str,
                 width: int = None,
                 height: int = None,
                 framerate: int = 25,
                 framecount: int = None,
                 chroma: int = 420,
                 bits_per_pixel: int = 8):

        assert (not width and not height) or (width and height)
        assert os.path.exists(filepath)
        assert chroma in (400, 420)
        assert bits_per_pixel in (8, 10)

        self.input_filepath = filepath
        self.input_filename = os.path.basename(self.input_filepath)
        self.base_filename = os.path.splitext(self.input_filename)[0]
        self.sequence_class = VideoSequence.guess_sequence_class(self.input_filepath)
        self.width = width
        self.height = height
        self.framerate = framerate
        self.framecount = framecount
        self.chroma = chroma
        self.bits_per_pixel = bits_per_pixel
        self.pixel_format = VideoSequence.PIXEL_FORMATS[(self.chroma, self.bits_per_pixel)]

        if not self.width and not self.height:
            self.width, self.height = VideoSequence.guess_resolution(self.input_filepath)

        if not self.framecount:
            self.framecount = VideoSequence.guess_framecount(
                self.input_filepath,
                self.width,
                self.height,
                self.chroma,
                self.bits_per_pixel
            )

        if not self.framerate:
            self.framerate = VideoSequence.guess_framerate(self.input_filepath)

        self.duration_seconds = self.framecount // self.framerate

        console_logger.debug(f"{type(self).__name__}: Initialized object:")
        for attribute_name in sorted(self.__dict__):
            console_logger.debug(f"{type(self).__name__}: {attribute_name} = {getattr(self, attribute_name)}")

    def __hash__(self):
        return int(hashlib.md5(self.input_filepath.encode()).hexdigest(), 16)

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
        quality_param_name = param_set.get_quality_param_name().lower()
        quality_param_value = param_set.get_quality_param_value()
        return f"{self.get_base_filename()}_{quality_param_name}{quality_param_value}.hevc"

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

    def get_chroma(self) -> int:
        return self.chroma

    def get_bits_per_pixel(self) -> int:
        return self.bits_per_pixel

    def get_framecount(self) -> int:
        return self.framecount

    def get_framerate(self) -> int:
        return self.framerate

    def get_sequence_class(self) -> str:
        return self.sequence_class

    def get_pixel_format(self):
        return self.pixel_format

    def get_duration_seconds(self):
        return self.duration_seconds

    @staticmethod
    def guess_sequence_class(filepath: str) -> str:
        for letter in "A", "B", "C", "D", "E", "F":
            sequence_class = f"hevc-{letter}"
            if sequence_class.lower() in filepath.lower():
                return sequence_class
        console_logger.warning(f"VideoSequence: Could not guess the sequence class from '{filepath}'")
        return "-"

    @staticmethod
    def guess_resolution(filepath: str) -> (int, int):
        filename = os.path.basename(filepath)
        resolution_pattern = re.compile(r"_([0-9]+)x([0-9]+)")
        match = resolution_pattern.search(filename)
        if match:
            width = int(match.group(1))
            height = int(match.group(2))
            return width, height
        else:
            console_logger.error(f"VideoSequence: Could not guess the resolution from '{filename}'")
            raise RuntimeError

    @staticmethod
    def guess_framecount(filepath: str,
                         width: int,
                         height: int,
                         chroma: int,
                         bits_per_pixel: int) -> int:

        filename = os.path.basename(filepath)
        console_logger.debug(f"VideoSequence: Trying to guess the framecount from '{filename}'")

        frame_count_pattern = re.compile("_[0-9]+x[0-9]+_[0-9]+_([0-9]+)")
        match = frame_count_pattern.search(filename)
        if match:
            return int(match.group(1))

        console_logger.debug(f"VideoSequence: Could not guess the framecount from '{filename}'")
        console_logger.debug(f"VideoSequence: Guessing the framecount from the size of file '{filename}'")

        file_size_bytes = os.path.getsize(filepath)
        bytes_per_pixel = 1 if bits_per_pixel == 8 else 2
        pixels_per_frame = width * height if chroma == 400 else int(width * height * 1.5)

        return file_size_bytes // (pixels_per_frame * bytes_per_pixel)

    @staticmethod
    def guess_framerate(filepath: str) -> int:
        filename = os.path.basename(filepath)
        framerate_pattern = re.compile("_[0-9]+x[0-9]+_([0-9]+)")
        match = framerate_pattern.search(filename)
        if match:
            return int(match.group(1))
        else:
            console_logger.error(f"VideoSequence: Could not guess the framerate from '{filename}'")
            raise RuntimeError
