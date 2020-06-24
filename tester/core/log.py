#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module defines functionality related to logging.
"""

import logging
import sys

import colorama
colorama.init()

# Custom formatter
class ColoredFormatter(logging.Formatter):
    """A formatter that adds color to log messages based on the logging level.
    Meant to be used with the console logger so the user can more easily
    filter information based on the color."""
    def __init__(self, format):
        super().__init__(fmt=format, datefmt=None, style='%')
        self.debug_format = f"{colorama.Fore.LIGHTBLACK_EX}{format}{colorama.Fore.RESET}"
        self.info_format = f"{colorama.Fore.GREEN}{format}{colorama.Fore.RESET}"
        self.warning_format = f"{colorama.Fore.LIGHTYELLOW_EX}{format}{colorama.Fore.RESET}"
        self.error_format = f"{colorama.Fore.RED}{format}{colorama.Fore.RESET}"

    def format(self, record):
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

# Set up global console logger.
formatter = ColoredFormatter("--%(levelname)s: %(message)s")
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(formatter)
console_logger = logging.getLogger("console")
console_logger.addHandler(handler)
console_logger.setLevel(logging.DEBUG)


def setup_build_logger(log_filename: str) -> logging.Logger:
    """Initializes and returns a Logger object with the given filename.
    The returned object is intended to be used for build logging.
    NOTE: Make sure this function is always called with a different log_filename
    because it also identifies the logger object!"""
    formatter = logging.Formatter("%(message)s")
    handler = logging.FileHandler(log_filename, "w")
    handler.setFormatter(formatter)
    build_logger = logging.getLogger(log_filename)
    build_logger.addHandler(handler)
    build_logger.setLevel(logging.DEBUG)
    return build_logger
