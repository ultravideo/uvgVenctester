from core.log import console_logger

import re
import os

class VideoSequence:
    def __init__(self, filepath: str, width: int = None, height: int = None):
        assert (not width and not height) or (width and height)
        assert os.path.exists(filepath)
        self.filepath = filepath
        self.width = width
        self.height = height

        if not self.width and not self.height:
            self.width, self.height = self.guess_resolution()

    def get_filepath(self) -> str:
        return self.filepath

    def get_width(self) -> int:
        return self.width

    def get_height(self) -> int:
        return self.height

    def guess_resolution(self) -> (int, int):
        # The following pattern is equal to "<width>x<height> preceded by non-integers".
        resolution_pattern: re.Pattern = re.compile(r"^[^0-9]+([0-9]+)x([0-9]+).*$")
        match: re.Match = resolution_pattern.fullmatch(self.filepath)
        if match:
            return int(match.groups()[0]), int(match.groups()[1])
        else:
            console_logger.error(f"The name of the file '{self.filepath}' doesn't include the video "
                                 f"resolution (expected format: <width>x<height>)")
            raise RuntimeError
