"""This module defines all functionality specific to HM."""

from __future__ import annotations

from .base import *
from tester.core.cfg import *
from tester.core.test import *
from tester.core import cmake
from tester.core import vs

from pathlib import Path
import os


def hm_validate_config():
    # Using the public property raises an exception, so access the private attribute instead.
    if Cfg()._hm_cfg_file_path is None:
        console_log.error(f"HM: Configuration file path has not been set")
        raise RuntimeError

    elif not Cfg().hm_cfg_file_path.exists():
        console_log.error(f"HM: Configuration file '{Cfg().hm_cfg_file_path}' does not exist")
        raise RuntimeError

    elif not git_remote_exists(Cfg().hm_remote_url):
        console_log.error(f"HM: Remote '{Cfg().hm_remote_url}' is not available")
        raise RuntimeError


def hm_get_temporal_subsample_ratio() -> int:

    hm_validate_config()

    pattern = re.compile(r"TemporalSubsampleRatio.*: ([0-9]+)", re.DOTALL)
    lines = Cfg().hm_cfg_file_path.open("r").readlines()
    for line in lines:
        match = pattern.match(line)
        if match:
            return int(match[1])

    return 0


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
            git_local_path=Cfg().tester_sources_dir_path / "hm",
            git_remote_url=Cfg().hm_remote_url
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
                / "TAppEncoder.exe"
        elif Cfg().system_os_name == "Linux":
            self._exe_src_path = self._git_local_path / "bin" / "TAppEncoderStatic"

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
                "&&", "msbuild", "HM.sln", f"/t:App\\TAppEncoder",
            ) + tuple(msbuild_args)

        elif Cfg().system_os_name == "Linux":

            # Add defines to make arguments.
            cflags_str = f"CFLAGS={''.join([f'-D{define} ' for define in self._defines])}".strip()

            build_cmd = (
                "cd", str(self._git_local_path),
                "&&", "make", "TAppEncoder-r", cflags_str
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
                "&&", "msbuild", "HM.sln", f"/t:App\\TAppEncoder:clean"
            )

        elif Cfg().system_os_name == "Linux":

            # TODO: This is SUPER slow (the binary seems to be recompiled for whatever reason).
            # TODO: Eliminate?
            clean_cmd = (
                "cd", str(self._git_local_path),
                "&&", "make", "clean", "TAppEncoder-r"
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
            "-c", str(Cfg().hm_cfg_file_path),
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
            "-c", str(Cfg().hm_cfg_file_path),
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
