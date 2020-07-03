from core.log import console_logger

import hashlib
import re
import os

class VideoSequence:
    def __init__(self, filepath: str, width: int = None, height: int = None):
        assert (not width and not height) or (width and height)
        assert os.path.exists(filepath)
        self.input_filepath = filepath
        self.input_filename = os.path.basename(self.input_filepath)
        self.output_filename = self.input_filename + ".hevc"
        self.width = width
        self.height = height

        if not self.width and not self.height:
            self.width, self.height = self.guess_resolution()

        hash = hashlib.md5()
        hash.update(self.input_filepath.encode())
        hash.update(self.output_filename.encode())
        self.hash = int(hash.hexdigest(), 16)

    def __hash__(self):
        return self.hash

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
