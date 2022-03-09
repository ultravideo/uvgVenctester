"""This module defines functionality related to the system the tester is running on."""

import tester.core.cfg as cfg
from tester.core.log import console_log

import os
from contextlib import contextmanager


@contextmanager
def pushd(path):
    old_wd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old_wd)


def system_validate_config():
    if not cfg.Cfg().system_os_name in ["Linux", "Windows"]:
        console_log.error(f"System: Invalid OS '{cfg.Cfg().system_os_name}' "
                          f"(only Linux and Windows are supported)")
        raise RuntimeError

    if cfg.Cfg().system_cpu_arch != "x64":
        console_log.error(f"System: Invalid architecture '{cfg.Cfg().system_cpu_arch}' "
                          f"(only x64 is supported)")
        raise RuntimeError
