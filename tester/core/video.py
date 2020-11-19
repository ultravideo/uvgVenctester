"""This module defines functionality related to video files."""

from __future__ import annotations

import math
import re
from pathlib import Path

import tester.core.cfg as cfg
from tester.core.log import console_log


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
        path = str(self._filepath).lower() if cfg.Cfg().system_os_name == "Windows" else str(self._filepath)
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
                 framerate: int = 25,
                 chroma: int = 420,
                 bit_depth: int = 8):

        self._width: [int, None] = None
        self._height: [int, None] = None
        self._fps: [int, None] = None
        self._chroma: [int, None] = None
        self._bit_depth: [int, None] = None
        self._total_frames: [int, None] = None

        stats = {
            "width": width,
            "height": height,
            "fps": framerate,
            "chroma": chroma,
            "bit_depth": bit_depth,
            "total_frames": self._total_frames,
        }

        stats.update(self.guess_values(filepath))

        if stats["total_frames"] is None:
            stats["total_frames"] = self.guess_total_framecount(filepath, **stats)

        for key, value in stats.items():
            setattr(self, "_" + key, value)

        assert self._width and self._height
        assert self._fps
        assert self._chroma in (400, 420)
        assert self._bit_depth in (8, 10)
        assert self._total_frames

        self._frames = self._total_frames
        assert self._total_frames


        sequence_class = RawVideoSequence.guess_sequence_class(filepath)

        self._filepath = filepath
        self._sequence_class: str = sequence_class

        # For bitrate calculation.
        self._bytes_per_pixel: int = 1 if self._bit_depth == 8 else 2
        self._pixels_per_frame: int = self._width * self._height \
            if self._chroma == 400 \
            else int(self._width * self._height * 1.5)
        self._bitrate: int = int(self._fps * self._pixels_per_frame * self._bytes_per_pixel * 8)

        console_log.debug(f"{type(self).__name__}: Initialized object:")
        for attribute_name in sorted(self.__dict__):
            console_log.debug(f"{type(self).__name__}: "
                              f"{attribute_name} = {getattr(self, attribute_name)}")

    def __hash__(self):
        path = str(self._filepath).lower() if cfg.Cfg().system_os_name == "Windows" else str(self._filepath)
        return hash(path)

    def __eq__(self,
               other: VideoFileBase):
        return self._filepath == other._filepath

    def get_size_bytes(self):
        return self.get_framecount() * self._pixels_per_frame * self._bytes_per_pixel

    def get_size_bits(self):
        return self.get_size_bytes() * 8

    def get_chroma(self) -> int:
        return self._chroma

    def get_bit_depth(self) -> int:
        return self._bit_depth

    def get_pixel_format(self) -> str:
        PIXEL_FORMATS: dict = {
            # (chroma, bit depth) : pixel format (ffmpeg)
            (400, 8): "gray",
            (400, 10): "gray16le",
            (420, 8): "yuv420p",
            (420, 10): "yuv420p10le",
        }
        return PIXEL_FORMATS[(self._chroma, self._bit_depth)]

    def get_sequence_class(self) -> str:
        return self._sequence_class

    def get_filepath(self) -> Path:
        return self._filepath

    def get_width(self) -> int:
        return self._width

    def get_height(self) -> int:
        return self._height

    def get_framerate(self) -> int:
        return self._fps

    def get_frames(self, seek=0) -> int:
        return self._frames - seek

    def get_framecount(self, seek=0) -> int:
        return (self._frames - seek + cfg.Cfg().frame_step_size - 1) // cfg.Cfg().frame_step_size

    def get_duration_seconds(self) -> float:
        return self.get_framecount() / self._fps

    def get_bitrate(self) -> float:
        return self._bitrate

    def get_suffixless_name(self):
        return self._filepath.parts[-1].replace(self._filepath.suffix, "")

    @staticmethod
    def guess_values(filepath: Path):
        file = filepath.parts[-1]
        first_pattern = re.compile(".+_(\d+)x(\d+)_(\d+)_?(\d+)?.yuv")
        second_pattern = re.compile(".+_(\d+)x(\d+)_(\d+)fps_(\d+)bit_(\d+).yuv")

        match = first_pattern.match(file)
        if match:
            result = {
                "width": int(match[1]),
                "height": int(match[2]),
                "fps": int(match[3]),
            }
            if match.lastindex == 4:
                result["total_frames"] = int(match[4])

            return result
        match = second_pattern.match(file)
        if match:
            return {
                "width": int(match[1]),
                "height": int(match[2]),
                "fps": int(match[3]),
                "bit_depth": int(match[4]),
                "chroma": int(match[5])
            }

    @staticmethod
    def guess_sequence_class(filepath: Path) -> str:
        regex_pattern = re.compile("(hevc-[a-z])", re.IGNORECASE)
        match = regex_pattern.search(str(filepath))
        if match:
            return match[1]
        else:
            return "Unknown"

    @staticmethod
    def guess_total_framecount(filepath: Path,
                               width: int,
                               height: int,
                               chroma: int,
                               bit_depth: int, **kwargs) -> int:
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
