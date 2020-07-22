from tester.encoders.base import *
from tester.core.log import *

import hashlib
from pathlib import *
import re

class VideoSequence:

    PIXEL_FORMATS: dict = {
        # (chroma, bits per pixel) : pixel format
        (400, 8): "gray",
        (400, 10): "gray16le",
        (420, 8): "yuv420p",
        (420, 10): "yuv420p10le",
    }

    def __init__(self,
                 filepath: Path,
                 width: int = None,
                 height: int = None,
                 framerate: int = 25,
                 total_framecount: int = None,
                 chroma: int = 420,
                 bits_per_pixel: int = 8,
                 seek: int = 0,
                 frames: int = 0):

        assert (not width and not height) or (width and height)
        assert filepath.exists()
        assert chroma in (400, 420)
        assert bits_per_pixel in (8, 10)

        self._filepath: Path = filepath
        self._sequence_class: str = VideoSequence.guess_sequence_class(self._filepath)
        self._seek: int = seek
        self._chroma: int = chroma
        self._bits_per_pixel: int = bits_per_pixel
        self._pixel_format: str = VideoSequence.PIXEL_FORMATS[(self._chroma, self._bits_per_pixel)]
        (self._width, self._height) = (width, height) if (width and height)\
            else VideoSequence.guess_resolution(self._filepath)
        self._total_framecount: int = total_framecount if total_framecount\
            else VideoSequence.guess_total_framecount(
                self._filepath,
                self._width,
                self._height,
                self._chroma,
                self._bits_per_pixel
            )
        self._framecount: int = frames if frames else self._total_framecount - seek
        self._framerate: int = framerate if framerate else VideoSequence.guess_framerate(self._filepath)
        self._total_duration_seconds: float = self._total_framecount / self._framerate
        self._duration_seconds: float = self._framecount / self._framerate
        self._bitrate: float = VideoSequence.guess_bitrate(filepath, self._total_duration_seconds)

        console_logger.debug(f"{type(self).__name__}: Initialized object:")
        for attribute_name in sorted(self.__dict__):
            console_logger.debug(f"{type(self).__name__}: {attribute_name} = {getattr(self, attribute_name)}")

    def __hash__(self) -> int:
        return hashlib.md5(str(self._filepath).encode())

    def get_base_filename(self) -> str:
        return Path(self._filepath).stem

    def get_input_filepath(self) -> Path:
        return self._filepath

    def get_input_filename(self,
                           include_extension=True) -> str:
        if include_extension:
            return self._filepath.name
        else:
            return str(self._filepath.with_suffix("").name)

    def get_output_filename(self,
                            encoder_instance: EncoderBase,
                            param_set: ParamSetBase) -> str:
        quality_param_name = param_set.get_quality_param_name().lower()
        quality_param_value = param_set.get_quality_param_value()
        return f"{self.get_base_filename()}_{quality_param_name}{quality_param_value}.hevc"

    def get_output_filepath(self,
                            encoder_instance: EncoderBase,
                            param_set: ParamSetBase) -> Path:
        return encoder_instance.get_output_subdir(param_set) \
               / self.get_output_filename(encoder_instance, param_set)

    def get_psnr_log_filename(self,
                              encoder_instance: EncoderBase,
                              param_set: ParamSetBase) -> str:
        return self.get_output_filename(encoder_instance, param_set).replace(".hevc", "_psnr_log.txt")

    def get_ssim_log_filename(self,
                              encoder_instance: EncoderBase,
                              param_set: ParamSetBase) -> str:
        return self.get_output_filename(encoder_instance, param_set).replace(".hevc", "_ssim_log.txt")

    def get_psnr_log_filepath(self,
                              encoder_instance: EncoderBase,
                              param_set: ParamSetBase) -> Path:
        return encoder_instance.get_output_subdir(param_set) \
               / self.get_psnr_log_filename(encoder_instance, param_set)

    def get_ssim_log_filepath(self,
                              encoder_instance: EncoderBase,
                              param_set: ParamSetBase) -> Path:
        return encoder_instance.get_output_subdir(param_set) \
               / self.get_ssim_log_filename(encoder_instance, param_set)

    def get_width(self) -> int:
        return self._width

    def get_height(self) -> int:
        return self._height

    def get_chroma(self) -> int:
        return self._chroma

    def get_bits_per_pixel(self) -> int:
        return self._bits_per_pixel

    def get_total_framecount(self) -> int:
        return self._total_framecount

    def get_framecount(self) -> int:
        return self._framecount

    def get_framerate(self) -> int:
        return self._framerate

    def get_sequence_class(self) -> str:
        return self._sequence_class

    def get_pixel_format(self):
        return self._pixel_format

    def get_total_duration_seconds(self):
        return self._total_duration_seconds

    def get_duration_seconds(self):
        return self._duration_seconds

    def get_bitrate(self):
        return self._bitrate

    @staticmethod
    def guess_bitrate(filepath: Path,
                      total_duration_seconds: float) -> float:
        total_bits = filepath.stat().st_size * 8
        return total_bits / total_duration_seconds

    @staticmethod
    def guess_sequence_class(filepath: Path) -> str:
        for letter in "A", "B", "C", "D", "E", "F":
            sequence_class = f"hevc-{letter}"
            if sequence_class.lower() in str(filepath).lower():
                return sequence_class
        console_logger.warning(f"VideoSequence: Could not guess the sequence class from '{filepath}'")
        return "-"

    @staticmethod
    def guess_resolution(filepath: Path) -> (int, int):
        filename = filepath.name
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
    def guess_total_framecount(filepath: Path,
                               width: int,
                               height: int,
                               chroma: int,
                               bits_per_pixel: int) -> int:

        filename = filepath.name
        console_logger.debug(f"VideoSequence: Trying to guess the total framecount from '{filename}'")

        frame_count_pattern = re.compile("_[0-9]+x[0-9]+_[0-9]+_([0-9]+)")
        match = frame_count_pattern.search(filename)
        if match:
            return int(match.group(1))

        console_logger.debug(f"VideoSequence: Could not guess the total framecount from '{filename}'")
        console_logger.debug(f"VideoSequence: Guessing the total framecount from the size of file '{filename}'")

        file_size_bytes = filepath.stat().st_size
        bytes_per_pixel = 1 if bits_per_pixel == 8 else 2
        pixels_per_frame = width * height if chroma == 400 else int(width * height * 1.5)

        return file_size_bytes // (pixels_per_frame * bytes_per_pixel)

    @staticmethod
    def guess_framerate(filepath: Path) -> int:
        filename = filepath.name
        framerate_pattern = re.compile("_[0-9]+x[0-9]+_([0-9]+)")
        match = framerate_pattern.search(filename)
        if match:
            return int(match.group(1))
        else:
            console_logger.error(f"VideoSequence: Could not guess the framerate from '{filename}'")
            raise RuntimeError
