"""This module defines functionality related logging."""

import logging
import sys
import traceback
from pathlib import Path

# For printing colored text.
from typing import Any

import colorama

colorama.init()


class ColoredFormatter(logging.Formatter):
    """A formatter that adds color to log messages based on the logging level.
    Meant to be used with the console logger so the user can more easily
    filter information based on the color."""

    def __init__(self,
                 format):
        super().__init__(
            fmt=format,
            datefmt=None,
            style='%'
        )
        self.debug_format: str = f"{colorama.Fore.LIGHTBLACK_EX}{format}{colorama.Fore.RESET}"
        self.info_format: str = f"{colorama.Fore.GREEN}{format}{colorama.Fore.RESET}"
        self.warning_format: str = f"{colorama.Fore.LIGHTYELLOW_EX}{format}{colorama.Fore.RESET}"
        self.error_format: str = f"{colorama.Fore.RED}{format}{colorama.Fore.RESET}"

    def format(self,
               record) -> str:
        original_format = self._style._fmt
        if record.levelno == logging.DEBUG:
            self._style._fmt = self.debug_format
        elif record.levelno == logging.INFO:
            self._style._fmt = self.info_format
        elif record.levelno == logging.WARNING:
            self._style._fmt = self.warning_format
        elif record.levelno == logging.ERROR:
            self._style._fmt = self.error_format
        result = logging.Formatter.format(self, record)
        self._style._fmt = original_format
        return result


class MyLogger(logging.Logger):
    def __init__(self, *args, **kwargs):
        super(MyLogger, self).__init__(*args, **kwargs)
        self._call_counts = {"error": 0, "warning": 0, "info": 0, "debug": 0}
        self._warnings = []

    def error(self, msg: Any, *args: Any, **kwargs: Any) -> None:
        self._call_counts["error"] += 1
        super(MyLogger, self).error(msg=msg, *args, **kwargs)

    def info(self, msg: Any, *args: Any, **kwargs: Any) -> None:
        self._call_counts["info"] += 1
        super(MyLogger, self).info(msg=msg, *args, **kwargs)

    def warning(self, msg: Any, *args: Any, **kwargs: Any) -> None:
        self._call_counts["warning"] += 1
        self._warnings.append(msg)
        super(MyLogger, self).warning(msg=msg, *args, **kwargs)

    def debug(self, *args: Any, **kwargs: Any) -> None:
        self._call_counts["debug"] += 1
        super(MyLogger, self).debug(*args, **kwargs)

    def __del__(self):
        if not self._warnings:
            return
        temp = '\n'.join(self._warnings)
        print(f"Caught {self._call_counts['warning']} warnings:\n{temp}")


logging.setLoggerClass(MyLogger)
# Set up the global console logger.
formatter = ColoredFormatter("--%(levelname)s: %(message)s")
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(formatter)
console_log = logging.getLogger("console")
console_log.addHandler(handler)


def log_exception(exception: Exception) -> None:
    console_log.error(f"Tester: An exception of "
                      f"type '{type(exception).__name__}' "
                      f"was caught: "
                      f"{str(exception)}")
    console_log.error(f"Tester: {traceback.format_exc().strip()}")


UNAVAILABLE_LOG_FILENAMES = []


def setup_build_log(log_filepath: Path) -> logging.Logger:
    """Initializes and returns a Logger object with the given filename.
    The returned object is intended to be used for build logging.
    NOTE: Make sure this function is always called with a different log_filepath
    because it also identifies the logger object!"""

    assert log_filepath not in UNAVAILABLE_LOG_FILENAMES
    UNAVAILABLE_LOG_FILENAMES.append(log_filepath)

    formatter = logging.Formatter("%(message)s")
    handler = logging.FileHandler(str(log_filepath), "w")
    handler.setFormatter(formatter)
    build_log = logging.getLogger(str(log_filepath))
    build_log.addHandler(handler)
    build_log.setLevel(logging.DEBUG)
    return build_log
