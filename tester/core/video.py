"""This module defines functionality related to video files."""

from __future__ import annotations

from tester.encoders.base import *
from tester.core.log import *

from pathlib import *
import math
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
        path = str(self._filepath).lower() if Cfg().system_os_name == "Windows" else str(self._filepath)
        return hash(path)

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

    def get_suffixless_name(self):
        return self._filepath.parts[-1].replace(self._filepath.suffix, "")

    def __str__(self):
        return f"{self._filepath.parts[-1]}"


class RawVideoSequence:
    """Represents a YUV file (or part of it if seek, framecount and/or step have been defined)."""

    def __init__(self,
                 filepath: Path,
                 width: int = None,
                 height: int = None,
                 framerate: int = None,
                 chroma: int = None,
                 bit_depth: int = None,
                 seek: int = None,
                 frames: int = None,
                 step: int = None):

        if width is None and height is None:
            width, height = RawVideoSequence.guess_resolution(filepath)
        assert width and height

        filename_framerate = RawVideoSequence.guess_framerate(filepath)
        if framerate is None:
            if filename_framerate:
                framerate = filename_framerate
            else:
                DEFAULT_FRAMERATE = 25
                console_log.info(f"{type(self).__name__}: Assuming framerate of '{filepath.name}' to be {DEFAULT_FRAMERATE}")
                framerate = DEFAULT_FRAMERATE
        else:
            if filename_framerate and filename_framerate != framerate:
                console_log.error(f"{type(self).__name__}: Given framerate '{framerate}' doesn't match name '{filepath.name}'")
                raise RuntimeError
        assert framerate

        filename_chroma = RawVideoSequence.guess_chroma(filepath)
        if chroma is None:
            if filename_chroma:
                chroma = filename_chroma
            else:
                DEFAULT_CHROMA = 420
                console_log.info(f"{type(self).__name__}: Assuming chroma of '{filepath.name}' to be {DEFAULT_CHROMA}")
                chroma = DEFAULT_CHROMA
        else:
            if filename_chroma and filename_chroma != chroma:
                console_log.error(f"{type(self).__name__}: Given chroma '{framerate}' doesn't match name '{filepath.name}'")
                raise RuntimeError
        assert chroma in (400, 420)

        filename_bitdepth = RawVideoSequence.guess_bit_depth(filepath)
        if bit_depth is None:
            if filename_bitdepth:
                bit_depth = filename_bitdepth
            else:
                DEFAULT_BITDEPTH = 8
                console_log.info(f"{type(self).__name__}: Assuming bit depth of '{filepath.name}' to be {DEFAULT_BITDEPTH}")
                bit_depth = DEFAULT_BITDEPTH
        else:
            if filename_bitdepth and filename_bitdepth != chroma:
                console_log.error(f"{type(self).__name__}: Given bit depth '{framerate}' doesn't match name '{filepath.name}'")
                raise RuntimeError
        assert bit_depth in (8, 10)

        if seek is None:
            seek = 0

        if step is None:
            step = 1

        file_total_framecount = RawVideoSequence.guess_total_framecount(
            filepath,
            width,
            height,
            chroma,
            bit_depth
        )
        assert file_total_framecount
        assert file_total_framecount > seek

        if frames is None:
            frames = file_total_framecount - seek
        assert frames

        # Only ever <step>th frame is encoded.
        framecount = math.ceil(frames / step)
        assert framecount
        assert framecount <= file_total_framecount - seek

        if not framerate:
            framerate = RawVideoSequence.guess_framerate(filepath)

        if not chroma:
            chroma = RawVideoSequence.guess_chroma(filepath)

        filename_bitdepth = RawVideoSequence.guess_bit_depth(filepath)
        if bit_depth and filename_bitdepth:
            assert filename_bitdepth == bit_depth
        if not bit_depth:
            bit_depth = filename_bitdepth

        sequence_class = RawVideoSequence.guess_sequence_class(filepath)

        self._filepath = filepath
        self._width = width
        self._height = height
        self._framerate = framerate
        # This doesn't take step into account:
        self._frames = frames
        # This takes step into account:
        self._framecount = framecount
        self._duration_seconds: float = framecount / framerate
        self._seek: int = seek
        self._chroma: int = chroma
        self._bit_depth: int = bit_depth
        self._step: int = step
        self._sequence_class: str = sequence_class

        # For bitrate calculation.
        self._bytes_per_pixel: int = 1 if bit_depth == 8 else 2
        self._pixels_per_frame: int = width * height if chroma == 400 else int(width * height * 1.5)
        self._bitrate: int = int(self._framerate * self._pixels_per_frame * self._bytes_per_pixel * 8)

        console_log.debug(f"{type(self).__name__}: Initialized object:")
        for attribute_name in sorted(self.__dict__):
            console_log.debug(f"{type(self).__name__}: "
                              f"{attribute_name} = {getattr(self, attribute_name)}")

    def __hash__(self):
        path = str(self._filepath).lower() if Cfg().system_os_name == "Windows" else str(self._filepath)
        return hash(path)

    def __eq__(self,
               other: VideoFileBase):
        return self._filepath == other._filepath

    def get_size_bytes(self):
        return self._framecount * self._pixels_per_frame * self._bytes_per_pixel

    def get_size_bits(self):
        return self.get_size_bytes() * 8

    def get_seek(self) -> int:
        return self._seek

    def get_chroma(self) -> int:
        return self._chroma

    def get_bit_depth(self) -> int:
        return self._bit_depth

    def get_pixel_format(self) -> str:
        PIXEL_FORMATS: dict = {
            # (chroma, bit depth) : pixel format (ffmpeg)
            (400,  8): "gray",
            (400, 10): "gray16le",
            (420,  8): "yuv420p",
            (420, 10): "yuv420p10le",
        }
        return PIXEL_FORMATS[(self._chroma, self._bit_depth)]

    def get_sequence_class(self) -> str:
        return self._sequence_class

    def get_step(self) -> int:
        return self._step

    def get_filepath(self) -> Path:
        return self._filepath

    def get_width(self) -> int:
        return self._width

    def get_height(self) -> int:
        return self._height

    def get_framerate(self) -> int:
        return self._framerate

    def get_frames(self) -> int:
        return self._frames

    def get_framecount(self) -> int:
        return self._framecount

    def get_duration_seconds(self) -> float:
        return self._duration_seconds

    def get_bitrate(self) -> float:
        return self._bitrate

    def get_suffixless_name(self):
        return self._filepath.parts[-1].replace(self._filepath.suffix, "")

    @staticmethod
    def guess_sequence_class(filepath: Path) -> str:
        regex_pattern = re.compile("hevc-([a-z])]", re.IGNORECASE)
        match = regex_pattern.search(str(filepath))
        if match:
            return match[1]
        else:
            return None

    @staticmethod
    def guess_resolution(filepath: Path) -> (int, int):
        resolution_pattern = re.compile("([0-9]+)x([0-9]+)")
        match = resolution_pattern.search(filepath.name)
        if match:
            return int(match[1]), int(match[2])
        else:
            return None, None

    @staticmethod
    def guess_framerate(filepath: Path) -> int:
        framerate_pattern = re.compile("[0-9]+x[0-9]+_([0-9]+)fps")
        match = framerate_pattern.search(filepath.name)
        if match:
            return int(match[1])
        else:
            return None

    @staticmethod
    def guess_total_framecount(filepath: Path,
                               width: int,
                               height: int,
                               chroma: int,
                               bit_depth: int) -> int:
        # There is no reason to have the frame count in the file name because it can be computed.
        """
        framecount_pattern = re.compile("[0-9]+x[0-9]+_[0-9]+fps_([0-9]+)")
        match = framecount_pattern.search(filepath.name)
        if match:
            return int(match[1])
        else:
        """
        assert filepath.exists()
        file_size_bytes = filepath.stat().st_size
        bytes_per_pixel = 1 if bit_depth == 8 else 2
        pixels_per_frame = width * height if chroma == 400 else int(width * height * 1.5)
        return file_size_bytes // (pixels_per_frame * bytes_per_pixel)

    @staticmethod
    def guess_bit_depth(filepath: Path) -> int:
        bitdepth_pattern = re.compile("[0-9]+x[0-9]+_[0-9]+fps_([0-9]+)bit")
        match = bitdepth_pattern.search(filepath.name)
        if match:
            return int(match[1])
        else:
            return None

    @staticmethod
    def guess_chroma(filepath: Path) -> int:
        chroma_pattern = re.compile("[0-9]+x[0-9]+_[0-9]+fps_[0-9]+bit_([0-9]+)")
        match = chroma_pattern.search(filepath.name)
        if match:
            return int(match[1])
        else:
            return None


class EncodedVideoFile(VideoFileBase):
    """Represents an encoded video file (HEVC/VVC)."""

    def __init__(self,
                 filepath: Path,
                 width: int,
                 height: int,
                 framerate: int,
                 frames: int,
                 duration_seconds: float):

        assert filepath.suffix in (".hevc", ".vvc")

        super().__init__(
            filepath,
            width,
            height,
            framerate,
            frames,
            duration_seconds
        )
