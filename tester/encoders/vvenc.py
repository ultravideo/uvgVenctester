"""This module defines all functionality specific to Kvazaar."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Iterable

import tester
import tester.core.git as git
import tester.core.cfg as cfg
import tester.core.test as test
from tester.core import vs, cmake
from tester.core.log import console_log
from . import EncoderBase


class Vvenc(EncoderBase):
    file_suffix = "vvc"

    class ParamSet(EncoderBase.ParamSet):

        def _to_unordered_args_list(self,
                                    include_quality_param: bool = True,
                                    include_seek: bool = True,
                                    include_frames: bool = True,
                                    include_directory_data: bool = False) -> list:
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
                    raise ValueError(
                        f"{self.get_quality_param_type().pretty_name} not available for encoder {str(self)}")
            if include_seek and self._seek:
                raise AssertionError("vvenc does not support seeking")
                args += f" -fs {self._seek}"
            if include_frames and self._frames:
                raise AssertionError("vvenc does not support setting frame_count")
                args += f" -f {self._frames}"

            if include_directory_data:
                if tester.Cfg().frame_step_size != 1:
                    args += f" --TemporalSubsampleRatio={tester.Cfg().frame_step_size}"
                args = args.replace("/", "-").replace("\\", "-").replace(":", "-")

            return args.split()

        @staticmethod
        def _get_arg_order() -> list:
            return []

    def __init__(self,
                 user_given_revision: str,
                 defines: Iterable,
                 use_prebuilt: bool):
        super().__init__(
            name="vvenc",
            user_given_revision=user_given_revision,
            defines=defines,
            git_local_path=tester.Cfg().tester_sources_dir_path / "vvenc",
            git_remote_url=tester.Cfg().vvenc_remote_url,
            use_prebuilt=use_prebuilt,
        )
        if tester.Cfg().system_os_name == "Windows":
            self._exe_src_path = self._git_local_path / "bin" / "release-static" / "vvencapp.exe"
        elif tester.Cfg().system_os_name == "Linux":
            raise NotImplementedError
            self._exe_src_path = self._git_local_path / "src" / "kvazaar"

        self._decoder_exe_path: Path = cfg.Cfg().tester_binaries_dir_path / f"DecoderApp.exe"

    def build(self) -> None:
        if not self.build_start():
            return

        if not (self._git_local_path / "build").exists():
            (self._git_local_path / "build").mkdir()

        if tester.Cfg().system_os_name == "Windows":
            msbuild_args = vs.get_msbuild_args(add_defines=self._defines)

            build_cmd = (
                            "cd", str(self._git_local_path),
                            "&&", "cd", "build",
                            "&&", "cmake", "..",
                            "-G", cmake.get_cmake_build_system_generator(),
                            "-A", cmake.get_cmake_architecture(),
                            "&&", "call", vs.get_vsdevcmd_bat_path(),
                            "&&", "msbuild", "vvenc.sln",
                        ) + tuple(msbuild_args)

        elif tester.Cfg().system_os_name == "Linux":
            cflags_str = f"CFLAGS={''.join([f'-D{define} ' for define in self._defines])}".strip()

            build_cmd = (
                "cd", str(self._git_local_path),
                "&&", "make", cflags_str
            )

        else:
            raise RuntimeError("Invalid operating system")

        self.build_finish(build_cmd)

    def clean(self) -> None:

        self.clean_start()

        clean_cmd = ()

        if tester.Cfg().system_os_name == "Linux":
            clean_cmd = (
                "cd", str(self._git_local_path),
                "&&", "make", "clean"
            )

        self.clean_finish(clean_cmd)

    def dummy_run(self,
                  param_set: EncoderBase.ParamSet) -> bool:
        self.dummy_run_start(param_set)

        RESOLUTION_PLACEHOLDER = "128x128"

        dummy_cmd = \
            (
                str(self._exe_path),
                "-i", os.devnull,
                "-s", RESOLUTION_PLACEHOLDER,
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

        encode_cmd = \
            (
                str(self._exe_path),
                "-i",
                str(encoding_run.input_sequence.get_filepath()) if tester.Cfg().frame_step_size == 1 else "-",
                "-s",
                f"{encoding_run.input_sequence.get_width()}x{encoding_run.input_sequence.get_height()}",
                "-r", str(encoding_run.input_sequence.get_framerate()),
                "-o", str(encoding_run.output_file.get_filepath()),
                "--frames", str(encoding_run.frames),
            ) + encoding_run.param_set.to_cmdline_tuple(include_quality_param=False,
                                                        include_frames=False) + quality
        self.encode_finish(encode_cmd, encoding_run)

    def _decode(self,
                encoding_run: test.EncodingRun):

        decode_cmd = (
            str(self._decoder_exe_path),
            "-b", str(encoding_run.output_file.get_filepath()),
            "-o", str(encoding_run.decoded_output_file_path),
            "-d", str(encoding_run.input_sequence.get_bit_depth())
        )

        try:
            subprocess.check_output(
                subprocess.list2cmdline(decode_cmd),
                shell=True,
                stderr=subprocess.STDOUT
            )
        except:
            console_log.error(f"{type(self.__name__)}: Failed to decode file "
                              f"'{encoding_run.output_file.get_filepath()}'")
            raise
