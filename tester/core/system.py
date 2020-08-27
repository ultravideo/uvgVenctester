"""This module defines functionality related to the system the tester is running on."""

from tester.core.cfg import Cfg
from tester.core.log import console_log


def system_validate_config():

    if not Cfg().system_os_name in ["Linux", "Windows"]:
        console_log.error(f"System: Invalid OS '{Cfg().system_os_name}' "
                          f"(only Linux and Windows are supported)")
        raise RuntimeError

    if Cfg().system_cpu_arch != "x64":
        console_log.error(f"System: Invalid architecture '{Cfg().system_cpu_arch}' "
                          f"(only x64 is supported)")
        raise RuntimeError
