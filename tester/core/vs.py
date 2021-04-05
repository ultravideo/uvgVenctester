"""This module defines functionality related to Visual Studio (and closely related tools)."""
import subprocess
from pathlib import Path
from typing import Iterable

import tester
from tester.core.log import console_log


def vs_validate_config():
    if tester.Cfg().system_os_name != "Windows":
        return

    if tester.Cfg().vs_year_version is None:
        console_log.error(f"Visual Studio: Year version has not been set")
        raise RuntimeError

    if tester.Cfg().vs_edition is None:
        console_log.error(f"Visual Studio: Edition has not been set")
        raise RuntimeError

    if tester.Cfg().vs_major_version is None:
        console_log.error(f"Visual Studio: Major version has not been set")
        raise RuntimeError

    if tester.Cfg().vs_msbuild_platformtoolset is None:
        console_log.error(f"Visual Studio: MSBuild platform toolset has not been set")
        raise RuntimeError

    if tester.Cfg().vs_msvc_version is None:
        console_log.error(f"Visual Studio: MSVC version has not been set")
        raise RuntimeError

    if tester.Cfg().vs_msbuild_windowstargetplatformversion is None:
        console_log.error(f"Visual Studio: MSBuild target platform version has not been set")
        raise RuntimeError

    VALID_EDITIONS = ["Community", "Professional", "Enterprise"]
    if tester.Cfg().vs_edition not in VALID_EDITIONS:
        console_log.error(f"Visual Studio: Edition '{tester.Cfg().vs_edition}' is not valid "
                          f"(expected one of: {VALID_EDITIONS})")
        raise RuntimeError

    if "." not in tester.Cfg().vs_msvc_version:
        console_log.error(f"Visual Studio: MSVC version '{tester.Cfg().vs_msvc_version}' is not "
                          f"sufficiently accurate (expected '<major version>.<minor version>)'")
        raise RuntimeError

    if not tester.Cfg().vs_install_path.exists():
        console_log.error(f"Visual Studio: Installation path '{tester.Cfg().vs_install_path}' does not exist")
        raise RuntimeError

    if not get_vsdevcmd_bat_path().exists():
        console_log.error(f"Visual Studio: VsDevCmd.bat does not exist in '{get_vsdevcmd_bat_path()}'")
        raise RuntimeError

    try:
        subprocess.check_output(
            subprocess.list2cmdline(
                ("call", str(get_vsdevcmd_bat_path()),
                 "&&", "msbuild", "/version")
            ),
            shell=True
        )
    except FileNotFoundError:
        console_log.error(f"Visual Studio: Executable 'msbuild' was not found")
        raise RuntimeError


def get_vsdevcmd_bat_path() -> Path:
    return tester.Cfg().vs_install_path \
           / tester.Cfg().vs_year_version \
           / tester.Cfg().vs_edition \
           / "Common7" \
           / "Tools" \
           / "VsDevCmd.bat"


def get_msbuild_args(add_defines: Iterable = None, target=None) -> list:
    base_args = [
        f"/p:Configuration=Release",
        f"/p:Platform=x64",
        f"/p:PlatformToolset={tester.Cfg().vs_msbuild_platformtoolset}",
        f"/p:WindowsTargetPlatformVersion={tester.Cfg().vs_msbuild_windowstargetplatformversion}",
    ]

    if add_defines:
        # Semicolons cannot be used as literals, so use %3B instead. Read these for reference:
        # https://docs.microsoft.com/en-us/visualstudio/msbuild/how-to-escape-special-characters-in-msbuild
        # https://docs.microsoft.com/en-us/visualstudio/msbuild/msbuild-special-characters
        base_args.append(f"/p:DefineConstants={'%3B'.join(add_defines)}")

    if target:
        base_args.append(f"-t:{target}")

    return base_args
