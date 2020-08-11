"""This module defines all functionality specific to VTM."""

from __future__ import annotations

from .base import *
from tester.core.cfg import *
from tester.core.test import *
from tester.core import cmake

from pathlib import Path
import os


def vtm_validate_config():

    if not git_remote_exists(Cfg().hm_remote_url):
        console_log.error(f"VTM: Remote '{Cfg().hm_remote_url}' is not available")
        raise RuntimeError


class VtmParamSet(ParamSetBase):
    """Represents the command line parameters passed to VTM when encoding."""

    def __init__(self,
                 quality_param_type: QualityParam,
                 quality_param_value: int,
                 seek: int,
                 frames: int,
                 cl_args: str):

        super().__init__(
            quality_param_type,
            quality_param_value,
            seek,
            frames,
            cl_args
        )

    @staticmethod
    def _get_arg_order() -> list:
        return []

    def _to_unordered_args_list(self,
                                include_quality_param: bool = True,
                                include_seek: bool = True,
                                include_frames: bool = True) -> list:
        return ["--asd", "5"]


class Vtm(EncoderBase):
    """Represents a VTM executable."""

    def __init__(self,
                 user_given_revision: str,
                 defines: list):

        super().__init__(
            id=Encoder.VTM,
            user_given_revision=user_given_revision,
            defines = defines,
            git_local_path=Cfg().tester_sources_dir_path / "vtm",
            git_remote_url=Cfg().vtm_remote_url
        )

        self._exe_src_path: Path = None
        if Cfg().system_os_name == "Windows":
            self._exe_src_path =\
                self._git_local_path \
                / "bin" \
                / f"vs{Cfg().vs_major_version}" \
                / f"msvc-{Cfg().vs_msvc_version}" \
                / "x86_64" \
                / "release" \
                / "EncoderApp.exe"
        elif Cfg().system_os_name == "Linux":
            self._exe_src_path = self._git_local_path / "bin" / "EncoderAppStatic"

    def build(self) -> None:

        if not super().build_start():
            return

        build_cmd = ()

        if Cfg().system_os_name == "Windows":

            # Add defines to msbuild arguments.
            msbuild_args = vs.get_msbuild_args(add_defines=self._defines)

            # Configure CMake, run VsDevCmd.bat, then MSBuild.
            build_cmd = (
                "cd", str(self._git_local_path),
                "&&", "mkdir", "build",
                "&&", "cd", "build",
                "&&", "cmake", "..",
                      "-G", cmake.get_cmake_build_system_generator(),
                      "-A", cmake.get_cmake_architecture(),
                "&&", "call", vs.get_vsdevcmd_bat_path(),
                "&&", "msbuild", "NextSoftware.sln", r"/t:App\EncoderApp",
            ) + tuple(msbuild_args)

        elif Cfg().system_os_name == "Linux":
            
            # Add defines to make arguments.
            cflags_str = f"CFLAGS={''.join([f'-D{define} ' for define in self._defines])}".strip()

            build_cmd = (
                "cd", str(self._git_local_path),
                "&&", "make", "EncoderApp-r", cflags_str
            )

        super().build_finish(build_cmd)

    def clean(self) -> None:

        super().clean_start()

        clean_cmd = ()

        if Cfg().system_os_name == "Windows":

            clean_cmd = (
                "call", str(vs.get_vsdevcmd_bat_path()),
                "&&", "cd", str(self._git_local_path),
                "&&", "cd", "build",
                "&&", "msbuild", "NextSoftware.sln", r"/t:App\EncoderApp:clean"
            )

        elif Cfg().system_os_name == "Linux":
            
            clean_cmd = (
                "cd", str(self._git_local_path),
                "&&", "make", "clean", "EncoderApp-r"
            )

        super().clean_finish(clean_cmd)
