"""This module defines functionality related to GCC (and closely related tools)."""

from tester.core.cfg import *
from tester.core.log import *

import subprocess


def gcc_validate_config():

    if Cfg().system_os_name != "Linux":
        return

    try:
        subprocess.check_output("gcc --version", shell=True)
    except FileNotFoundError:
        console_log.error("GCC: Executable 'gcc' was not found")
        raise RuntimeError

    try:
        subprocess.check_output("make --version", shell=True)
    except FileNotFoundError:
        console_log.error("Make: Executable 'make' was not found")
        raise RuntimeError
