"""This module defines functionality related to GCC (and closely related tools)."""

import subprocess

from tester.core.cfg import Cfg
from tester.core.log import console_log


def gcc_validate_config():
    if Cfg().system_os_name != "Linux":
        return

    try:
        subprocess.check_output(["gcc", "--version"])
    except FileNotFoundError:
        console_log.error("GCC: Executable 'gcc' was not found")
        raise RuntimeError

    try:
        subprocess.check_output(["make", "--version"])
    except FileNotFoundError:
        console_log.error("Make: Executable 'make' was not found")
        raise RuntimeError
