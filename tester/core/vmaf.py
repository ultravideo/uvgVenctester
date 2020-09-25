"""This module defines functionality related to the VMAF library."""

from tester.core.cfg import Cfg
from tester.core.log import console_log


def vmaf_validate_config():

    # Access the private attribute instead of the public property because the latter will raise
    # an exception.
    if Cfg()._vmaf_repo_path is None:
        console_log.error(f"VMAF: VMAF repository path has not been set")
        raise RuntimeError

    if not Cfg().vmaf_repo_path.exists():
        console_log.error(f"VMAF: VMAF repository path '{Cfg().vmaf_repo_path}' does not exist")
