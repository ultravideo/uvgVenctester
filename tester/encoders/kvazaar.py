"""This module defines all functionality specific to Kvazaar."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

import tester
import tester.core.git as git
import tester.core.test as test
from tester.core import vs
from tester.core.log import console_log
from . import ParamSetBase, EncoderBase


def kvazaar_validate_config():
    if not git.git_remote_exists(tester.Cfg().kvazaar_remote_url):
        console_log.error(f"Kvazaar: Remote '{tester.Cfg().kvazaar_remote_url}' is unavailable")
        raise RuntimeError


class KvazaarParamSet(ParamSetBase):
    """Represents the command line parameters passed to Kvazaar when encoding."""

    # These have to be the first two arguments on the command line.
    POSITIONAL_ARGS = ("--preset", "--gop")

    def __init__(self,
                 quality_param_type: tester.QualityParam,
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

        # This checks the integrity of the parameters.
        self.to_cmdline_tuple(include_quality_param=False)

    def _to_unordered_args_list(self,
                                include_quality_param: bool = True,
                                include_seek: bool = True,
                                include_frames: bool = True,
                                inode_safe=False) -> list:

        args = self._cl_args

        if include_quality_param:
            if self._quality_param_type == tester.QualityParam.QP:
                args += f" --qp {self._quality_param_value}"
            elif self._quality_param_type == tester.QualityParam.BITRATE:
                args += f" --bitrate {self._quality_param_value}"
            elif self.get_quality_param_type() == tester.QualityParam.BPP:
                args += f" --bitrate {self._quality_param_value}"
            elif self.get_quality_param_type() == tester.QualityParam.RES_SCALED_BITRATE:
                args += f" --bitrate {self._quality_param_value}"
            elif self.get_quality_param_type() == tester.QualityParam.RES_ROOT_SCALED_BITRATE:
                args += f" --bitrate {self._quality_param_value}"
            else:
                raise ValueError(f"{self.get_quality_param_type().pretty_name} not available for encoder {str(self)}")
        if include_seek and self._seek:
            args += f" --seek {self._seek}"
        if include_frames and self._frames:
            args += f" --frames {self._frames}"

        if inode_safe:
            args = args.replace("/", "-").replace("\\", "-").replace(":", "-")

        split_args: list = []

        # Split the arguments such that each option and its value, if any, are separated.
        for item in args.split():
            if ParamSetBase._is_short_option(item):
                # A short option is of the form -<short form><value> or -<short form> <value>,
                # so split after the second character.
                option_name: str = item[:2]
                option_value: str = item[2:].strip()
                split_args.append(option_name)
                if option_value:
                    split_args.append(option_value)
            else:
                for item in item.split("="):
                    split_args.append(item)

        return split_args

    @staticmethod
    def _get_arg_order() -> list:
        return ["--preset", "--gop"]


class Kvazaar(EncoderBase):
    """Represents a Kvazaar executable."""

    def __init__(self,
                 user_given_revision: str,
                 defines: Iterable,
                 use_prebuilt: bool):
        super().__init__(
            id=tester.Encoder.KVAZAAR,
            user_given_revision=user_given_revision,
            defines=defines,
            git_local_path=tester.Cfg().tester_sources_dir_path / "kvazaar",
            git_remote_url=tester.Cfg().kvazaar_remote_url,
            use_prebuilt=use_prebuilt,
        )

        self._exe_src_path: Path = None
        if tester.Cfg().system_os_name == "Windows":
            self._exe_src_path = self._git_local_path / "bin" / "x64-Release" / "kvazaar.exe"
        elif tester.Cfg().system_os_name == "Linux":
            self._exe_src_path = self._git_local_path / "src" / "kvazaar"

    def build(self) -> None:

        if not self.build_start():
            return

        build_cmd = ()

        if tester.Cfg().system_os_name == "Windows":

            # Add defines to msbuild arguments.
            msbuild_args = vs.get_msbuild_args(add_defines=self._defines)

            # Run VsDevCmd.bat, then msbuild.
            build_cmd = (
                "call", str(vs.get_vsdevcmd_bat_path()),
                "&&", "msbuild", str(self._git_local_path / "build" / "kvazaar_VS2015.sln")
            ) + tuple(msbuild_args)

        elif tester.Cfg().system_os_name == "Linux":

            # Add defines to configure arguments.
            cflags_str = f"CFLAGS={''.join([f'-D{define} ' for define in self._defines])}"
            kvz_configure_args = ["--disable-shared", "--enable-static",]
            kvz_configure_args.append(cflags_str.strip())

            # Run autogen.sh, then configure, then make.
            build_cmd = (
                "cd", str(self._git_local_path),
                "&&", "autogen.sh",
                "&&", "configure",) + tuple(kvz_configure_args) + (
                "&&", "make",
            )

        self.build_finish(build_cmd)

    def clean(self) -> None:

        self.clean_start()

        clean_cmd = ()

        if tester.Cfg().system_os_name == "Linux":
            clean_cmd = (
                "cd", str(self._git_local_path),
                "&&", "make", "clean",
            )

        self.clean_finish(clean_cmd)

    def dummy_run(self,
                  param_set: KvazaarParamSet) -> bool:

        self.dummy_run_start(param_set)

        RESOLUTION_PLACEHOLDER = "2x2"

        dummy_cmd = (
            str(self._exe_path),
            "-i", os.devnull,
            "--input-res", RESOLUTION_PLACEHOLDER,
            "-o", os.devnull,
        ) + param_set.to_cmdline_tuple()

        return self.dummy_run_finish(dummy_cmd, param_set)

    def encode(self,
               encoding_run: test.EncodingRun) -> None:

        if not self.encode_start(encoding_run):
            return

        if encoding_run.qp_name == tester.QualityParam.QP:
            quality = ("--qp", str(encoding_run.qp_value))
        elif encoding_run.qp_name in (tester.QualityParam.BITRATE,
                                      tester.QualityParam.RES_SCALED_BITRATE,
                                      tester.QualityParam.BPP,
                                      tester.QualityParam.RES_ROOT_SCALED_BITRATE):
            quality = ("--bitrate", str(encoding_run.qp_value))
        else:
            assert 0, "Invalid quality parameter"

        encode_cmd = (
            str(self._exe_path),
            "-i", str(encoding_run.input_sequence.get_filepath()),
            "--input-res", f"{encoding_run.input_sequence.get_width()}x{encoding_run.input_sequence.get_height()}",
            "--input-fps", str(encoding_run.input_sequence.get_framerate()),
            "-o", str(encoding_run.output_file.get_filepath()),
            "--frames", str(encoding_run.frames),
        ) + encoding_run.param_set.to_cmdline_tuple(include_quality_param=False, include_frames=False) + quality

        self.encode_finish(encode_cmd, encoding_run)
