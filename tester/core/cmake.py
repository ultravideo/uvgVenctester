"""This module defines functionality related to CMake."""
import subprocess

import tester.core.cfg as cfg
from tester.core.log import console_log

CMAKE_ARCHITECTURE: str = "x64"


def cmake_validate_config():
    try:
        subprocess.check_output(f"cmake --version", shell=True)
    except FileNotFoundError:
        console_log.error(f"CMake: Executable 'cmake' was not found")
        raise RuntimeError


def get_cmake_architecture() -> str:
    return CMAKE_ARCHITECTURE


def get_cmake_build_system_generator() -> str:
    return f"Visual Studio {cfg.Cfg().vs_major_version} {cfg.Cfg().vs_year_version}"
