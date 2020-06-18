#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module defines functionality related to logging.
"""

import logging
import sys

# Set up global console logger.
formatter = logging.Formatter("--%(levelname)s: %(message)s")
handler = logging.StreamHandler(sys.stdout)
console_logger = logging.getLogger("console")
handler.setFormatter(formatter)
console_logger.addHandler(handler)
console_logger.setLevel(logging.DEBUG)

def setup_build_logger(log_name: str, log_filename: str) -> logging.Logger:
    """Initializes and returns a Logger object with the given name and filename.
    The returned object is intended to be used for build logging.
    NOTE: Make sure this function is always called with a different log_name!"""
    formatter = logging.Formatter("%(message)s")
    handler = logging.FileHandler(log_filename, "w")
    handler.setFormatter(formatter)
    build_logger = logging.getLogger(log_name)
    build_logger.addHandler(handler)
    build_logger.setLevel(logging.DEBUG)
    return build_logger