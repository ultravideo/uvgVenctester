from __future__ import annotations

from .base import *
from tester.core.test import *


class HmParamSet(ParamSetBase):
    """Represents the command line parameters passed to HM when encoding."""

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

    def to_cmdline_tuple(self,
                         include_quality_param: bool = True) -> tuple:
        return ("",)


class Hm(EncoderBase):
    """Represents a HM executable."""

    def __init__(self,
                 user_given_revision: str,
                 defines: list):

        super().__init__(
            id=Encoder.HM,
            user_given_revision=user_given_revision,
            defines = defines,
            git_local_path=Cfg().hm_git_repo_path,
            git_remote_url=Cfg().hm_git_repo_https_url
        )

        self._exe_src_path: Path = Cfg().hm_exe_src_path_windows if Cfg().os_name == "Windows"\
                              else Cfg().hm_exe_src_path_linux

    def build(self) -> None:

        if not super().build_start():
            return

        build_cmd = ()

        if Cfg().os_name == "Windows":

            # Add defines to msbuild arguments.
            # Semicolons cannot be used as literals, so use %3B instead. Read these for reference:
            # https://docs.microsoft.com/en-us/visualstudio/msbuild/how-to-escape-special-characters-in-msbuild
            # https://docs.microsoft.com/en-us/visualstudio/msbuild/msbuild-special-characters
            MSBUILD_SEMICOLON_ESCAPE = "%3B"
            msbuild_args = Cfg().msbuild_args
            msbuild_args.append(f"/p:DefineConstants={MSBUILD_SEMICOLON_ESCAPE.join(self._defines)}")

            # Configure CMake, run VsDevCmd.bat, then msbuild.
            build_cmd = (
                "cd", str(Cfg().hm_git_repo_path),
                "&&", "mkdir", "build",
                "&&", "cd", "build",
                "&&", "cmake", "..",
                      "-G", Cfg().cmake_build_system_generator,
                      "-A", Cfg().cmake_architecture,
                "&&", "call", str(Cfg().vs_vsdevcmd_bat_path),
                "&&", "msbuild", str(Cfg().hm_vs_solution_path),
                      f"/t:{Cfg().hm_vs_project_name}",
            ) + tuple(msbuild_args)

        elif Cfg().os_name == "Linux":

            # Add defines to make arguments.
            cflags_str = f"CFLAGS={''.join([f'-D{define} ' for define in self._defines])}".strip()

            build_cmd = (
                "cd", str(Cfg().hm_git_repo_path),
                "&&", "make", Cfg().hm_make_target_name, cflags_str
            )

        super().build_finish(build_cmd)

    def clean(self) -> None:

        super().clean_start()

        clean_cmd = ()

        if Cfg().os_name == "Windows":

            clean_cmd = (
                "call", str(Cfg().vs_vsdevcmd_bat_path),
                "&&", "msbuild", str(Cfg().hm_vs_solution_path), f"/t:{Cfg().hm_vs_project_name}:clean"
            )

        elif Cfg().os_name == "Linux":

            # TODO: This is SUPER slow (the binary seems to be recompiled for whatever reason).
            # TODO: Eliminate?
            clean_cmd = (
                "cd", str(Cfg().hm_git_repo_path),
                "&&", "make", "clean", Cfg().hm_make_target_name
            )

        super().clean_finish(clean_cmd)
