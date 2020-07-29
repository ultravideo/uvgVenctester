"""This module defines functionality related to video files."""

from __future__ import annotations

from tester.encoders.base import *
from tester.core.log import *

from pathlib import *
import re


class VideoFileBase:
    """Base class for video files."""

    def __init__(self,
                 filepath: Path,
                 width: int,
                 height: int,
                 framerate: int,
                 framecount: int,
                 duration_seconds: float):

        assert width
        assert height
        assert framerate
        assert framecount
        assert duration_seconds

        self._filepath: Path = filepath
        self._width: int = width
        self._height: int = height
        self._framerate: int = framerate
        self._framecount: int = framecount

    def __hash__(self):
        return hash(str(self._filepath))

    def __eq__(self,
               other: VideoFileBase):
        return self._filepath == other._filepath

    def get_total_size_bytes(self) -> int:
        return self._filepath.stat().st_size

    def get_total_size_bits(self) -> int:
        return self.get_total_size_bytes() * 8

    def get_filepath(self) -> Path:
        return self._filepath

    def get_width(self) -> int:
        return self._width

    def get_height(self) -> int:
        return self._height

    def get_framerate(self) -> int:
        return self._framerate

    def get_framecount(self) -> int:
        return self._framecount

    def get_duration_seconds(self) -> float:
        return self._framecount / self._framerate

    def get_bitrate(self) -> float:
        file_size_bits = self._filepath.stat().st_size * 8
        return file_size_bits / self.get_duration_seconds()


class RawVideoSequence(VideoFileBase):
    """Represents a YUV file (or part of it, in case seek and frames are not 0)."""

    def __init__(self,
                 filepath: Path,
                 width: int = None,
                 height: int = None,
                 framerate: int = 25,
                 chroma: int = 420,
                 bits_per_pixel: int = 8,
                 seek: int = 0,
                 frames: int = 0):

        assert filepath.exists()
        assert (not width and not height) or (width and height)
        assert chroma in (400, 420)
        assert bits_per_pixel in (8, 10)

        if not width and not height:
            (width, height) = RawVideoSequence.guess_resolution_from_filepath(filepath)

        self._total_framecount = RawVideoSequence.guess_total_framecount_from_filename(filepath)
        if not self._total_framecount:
            self._total_framecount = RawVideoSequence.guess_total_framecount_from_filesize(
                filepath,
                width,
                height,
                chroma,
                bits_per_pixel
            )

        assert self._total_framecount > seek
        assert self._total_framecount - seek >= frames
        if not frames:
            frames = self._total_framecount

        duration_seconds = frames / framerate

        super().__init__(
            filepath,
            width,
            height,
            framerate,
            frames,
            duration_seconds
        )

        self._seek = seek
        self._chroma = chroma
        self._bits_per_pixel = bits_per_pixel

        self._sequence_class = RawVideoSequence.guess_sequence_class_from_filepath(filepath)

        console_log.debug(f"{type(self).__name__}: Initialized object:")
        for attribute_name in sorted(self.__dict__):
            console_log.debug(f"{type(self).__name__}: "
                                 f"{attribute_name} = {getattr(self, attribute_name)}")

    def get_effective_size_bytes(self) -> int:
        if self._framecount == self._total_framecount:
            return self.get_total_size_bytes()
        else:
            percentage_of_total_size = self._framecount / self._total_framecount
            return int(percentage_of_total_size * self.get_total_size_bytes())

    def get_effective_size_bits(self) -> int:
        return self.get_effective_size_bytes() * 8

    def get_seek(self) -> int:
        return self._seek

    def get_chroma(self) -> int:
        return self._chroma

    def get_bits_per_pixel(self) -> int:
        return self._bits_per_pixel

    def get_pixel_format(self) -> str:
        PIXEL_FORMATS: dict = {
            # (chroma, bits per pixel) : pixel format (ffmpeg)
            (400,  8): "gray",
            (400, 10): "gray16le",
            (420,  8): "yuv420p",
            (420, 10): "yuv420p10le",
        }
        return PIXEL_FORMATS[(self._chroma, self._bits_per_pixel)]

    def get_sequence_class(self) -> str:
        return self._sequence_class

    @staticmethod
    def guess_sequence_class_from_filepath(filepath: Path) -> str:
        for letter in "A", "B", "C", "D", "E", "F":
            sequence_class = f"hevc-{letter}"
            if sequence_class.lower() in str(filepath).lower():
                return sequence_class
        console_log.debug(f"Could not guess the sequence class from '{filepath}'")
        return "-"

    @staticmethod
    def guess_resolution_from_filepath(filepath: Path) -> (int, int):
        filename = filepath.name
        resolution_pattern = re.compile(r"_([0-9]+)x([0-9]+)")
        match = resolution_pattern.search(filename)
        if match:
            width = int(match.group(1))
            height = int(match.group(2))
            return width, height
        else:
            console_log.error(f"Could not guess the resolution from '{filename}'")
            raise RuntimeError

    @staticmethod
    def guess_total_framecount_from_filename(filepath: Path) -> int:

        console_log.debug(f"Trying to guess the total framecount from "
                          f"'{filepath.name}'")

        framecount_pattern = re.compile("_[0-9]+x[0-9]+_[0-9]+_([0-9]+)")
        match = framecount_pattern.search(filepath.name)
        if match:
            return int(match.group(1))
        else:
            console_log.debug(f"Could not guess the total framecount from "
                              f"'{filepath.name}'")
            return 0

    @staticmethod
    def guess_total_framecount_from_filesize(filepath: Path,
                                             width: int,
                                             height: int,
                                             chroma: int,
                                             bits_per_pixel: int) -> int:

        console_log.debug(f"Guessing the total framecount from the size of file "
                          f"'{filepath.name}'")

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
            console_log.debug(f"Could not guess the framerate from '{filename}'")
            raise RuntimeError


class HevcVideoFile(VideoFileBase):
    """Represents a HEVC file encoded by an encoder."""

    def __init__(self,
                 filepath: Path,
                 width: int,
                 height: int,
                 framerate: int,
                 framecount: int,
                 duration_seconds: float):

        assert filepath.suffix == ".hevc"

        super().__init__(
            filepath,
            width,
            height,
            framerate,
            framecount,
            duration_seconds
        )
