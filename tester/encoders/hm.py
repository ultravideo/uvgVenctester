"""This module defines all functionality specific to HM."""

from __future__ import annotations

from .base import *
from tester.core.test import *

import os


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

    @staticmethod
    def _get_arg_order() -> list:
        return []

    def _to_unordered_args_list(self,
                                include_quality_param: bool = True,
                                include_seek: bool = True,
                                include_frames: bool = True) -> list:

        args = self._cl_args

        if include_quality_param:
            if self._quality_param_type == QualityParam.QP:
                args += f" --QP={self._quality_param_value}"
            elif self._quality_param_type == QualityParam.BITRATE:
                args += f" --TargetBitrate={self._quality_param_value}"
        if include_seek and self._seek:
            args += f" -fs {self._seek}"
        if include_frames and self._frames:
            args += f" -f {self._frames}"
        # TODO: Figure out why this is needed or if it's needed.
        if not "--SEIDecodedPictureHash" in args:
            args += " --SEIDecodedPictureHash=3"
        if not "--ConformanceWindowMode" in args:
            args += " --ConformanceWindowMode=1"

        return args.split()


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

    def dummy_run(self,
                  param_set: ParamSetBase) -> bool:

        super().dummy_run_start(param_set)

        FRAMERATE_PLACEHOLDER = "1"
        WIDTH_PLACEHOLDER = "16"
        HEIGHT_PLACEHOLDER = "16"
        FRAMECOUNT_PLACEHOLDER = "1"

        dummy_cmd = (
            str(self._exe_path),
            "-c", str(Cfg().hm_cfg_path),
            "-i", os.devnull,
            "-fr", FRAMERATE_PLACEHOLDER,
            "-wdt", WIDTH_PLACEHOLDER,
            "-hgt", HEIGHT_PLACEHOLDER,
            # Just in case the parameter set doesn't contain the number of frames parameter.
            "-f", FRAMECOUNT_PLACEHOLDER,
            "-b", os.devnull,
            "-o", os.devnull,
        ) + param_set.to_cmdline_tuple(include_frames=False)

        return super().dummy_run_finish(dummy_cmd, param_set)

    def encode(self,
               encoding_run: EncodingRun) -> None:

        if not super().encode_start(encoding_run):
            return

        # HM is stupid.
        framecount = encoding_run.param_set.get_frames()

        encode_cmd = (
            str(self._exe_path),
            "-c", str(Cfg().hm_cfg_path),
            "-i", str(encoding_run.input_sequence.get_filepath()),
            "-fr", str(encoding_run.input_sequence.get_framerate()),
            "-wdt", str(encoding_run.input_sequence.get_width()),
            "-hgt", str(encoding_run.input_sequence.get_height()),
            "-b", str(encoding_run.output_file.get_filepath()),
            "-o", os.devnull,
        ) + encoding_run.param_set.to_cmdline_tuple(include_quality_param=bool(framecount))

        if not framecount:
            encode_cmd += ("-f", str(encoding_run.input_sequence.get_framecount()))

        super().encode_finish(encode_cmd, encoding_run)
