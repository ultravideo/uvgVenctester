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

            self._quality_formats[tester.QualityParam.QP] = "-qp "
            for t in range(tester.QualityParam.BITRATE.value, len(tester.QualityParam) + 1):
                self._quality_formats[tester.QualityParam(t)] = "--bitrate"

        def _to_unordered_args_list(self,
                                    include_quality_param: bool = True,
                                    include_seek: bool = True,
                                    include_frames: bool = True,
                                    include_directory_data: bool = False) -> list:
            args = self._cl_args

            if include_quality_param:
                args += " " + " ".join(self.get_quality_value(self.get_quality_param_value()))

            if self._seek:
                raise AssertionError("vvenc does not support seeking")
            if self._frames:
                raise AssertionError("vvenc does not support setting frame_count")

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
            self._exe_src_path = self._git_local_path / "bin" / "release-static" / "vvencapp"

        self._decoder_exe_path: Path = cfg.Cfg().vvc_reference_decoder

    def build(self) -> bool:
        if not self.build_start():
            return False

        env = None
        if not (self._git_local_path / "build").exists():
            (self._git_local_path / "build").mkdir()

        if tester.Cfg().system_os_name == "Windows":
            if self.get_defines():
                env = os.environ
                temp = " ".join([f"/D{x}".replace("=", "#") for x in self.get_defines()])
                env["CL"] = temp
            msbuild_args = vs.get_msbuild_args()

            build_cmd = (
                            "cd", str(self._git_local_path),
                            "&&", "cd", "build",
                            "&&", "cmake", "..",
                            "-G", cmake.get_cmake_build_system_generator(),
                            "-A", cmake.get_cmake_architecture(),
                            "&&", "call", str(vs.get_vsdevcmd_bat_path()),
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

        return self.build_finish(build_cmd, env)

    def clean(self) -> None:

        self.clean_start()

        clean_cmd = ()

        if tester.Cfg().system_os_name == "Linux":
            clean_cmd = (
                "cd", str(self._git_local_path),
                "&&", "make", "clean"
            )

        elif tester.Cfg().system_os_name == "Windows":
            msbuild_args = vs.get_msbuild_args(target="Clean")
            clean_cmd = (
                            "call", str(vs.get_vsdevcmd_bat_path()),
                            "&&", "msbuild", str(self._git_local_path / "build" / "vvenc.sln")
                        ) + tuple(msbuild_args)

        self.clean_finish(clean_cmd)

    def dummy_run(self,
                  param_set: EncoderBase.ParamSet, env) -> bool:
        self.dummy_run_start(param_set)

        RESOLUTION_PLACEHOLDER = "128x128"

        dummy_cmd = \
            (
                str(self._exe_path),
                "-i", os.devnull,
                "-s", RESOLUTION_PLACEHOLDER,
                "--FrameRate=30",
                "-o", os.devnull,
            ) + param_set.to_cmdline_tuple()

        return self.dummy_run_finish(dummy_cmd, param_set, env)

    @staticmethod
    def validate_config(test_config: test.Test):
        # Using the public property raises an exception, so access the private attribute instead.
        if not test_config.use_prebuilt and not git.git_remote_exists(tester.Cfg().vvenc_remote_url):
            console_log.error(f"VVenC: Remote '{tester.Cfg().vvenc_remote_url}' is not available")
            raise RuntimeError

        try:
            subprocess.call((cfg.Cfg().vvc_reference_decoder, ), )
        except FileNotFoundError:
            raise RuntimeError("VVenC: VVC reference decoder is needed for decoding VVC currently")

    def encode(self,
               encoding_run: test.EncodingRun) -> None:
        if not self.encode_start(encoding_run):
            return

        quality = encoding_run.param_set.get_quality_value(encoding_run.qp_value)

        encode_cmd = \
            (
                str(self._exe_path),
                "-i", str(encoding_run.input_sequence.get_filepath()),
                "-s", f"{encoding_run.input_sequence.get_width()}x{encoding_run.input_sequence.get_height()}",
                f"--FrameRate={encoding_run.input_sequence.get_framerate()}",
                f"--InputBitDepth={encoding_run.input_sequence.get_bit_depth()}",
                f"--InputChromaFormat={encoding_run.input_sequence.get_chroma()}",
                "-o", str(encoding_run.output_file.get_filepath()),
                "--frames", str(encoding_run.frames * tester.Cfg().frame_step_size),
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
            console_log.error(f"VVenc: Failed to decode file "
                              f"'{encoding_run.output_file.get_filepath()}'")
            raise


class Vvencff(Vvenc):
    def __init__(self,
                 user_given_revision: str,
                 defines: Iterable,
                 use_prebuilt: bool):
        super(Vvenc, self).__init__(
            name="vvencff",
            user_given_revision=user_given_revision,
            defines=defines,
            git_local_path=tester.Cfg().tester_sources_dir_path / "vvenc",
            git_remote_url=tester.Cfg().vvenc_remote_url,
            use_prebuilt=use_prebuilt,
        )
        if tester.Cfg().system_os_name == "Windows":
            self._exe_src_path = self._git_local_path / "bin" / "release-static" / "vvencFFapp.exe"
        elif tester.Cfg().system_os_name == "Linux":
            self._exe_src_path = self._git_local_path / "bin" / "release-static" / "vvencFFapp"

        self._decoder_exe_path: Path = cfg.Cfg().vvc_reference_decoder

    def encode(self,
               encoding_run: test.EncodingRun) -> None:
        if not self.encode_start(encoding_run):
            return

        quality = encoding_run.param_set.get_quality_value(encoding_run.qp_value)

        encode_cmd = \
            (
                str(self._exe_path),
            ) + encoding_run.param_set.to_cmdline_tuple(include_quality_param=False,
                                                        include_frames=False) + (
                "-i", str(encoding_run.input_sequence.get_encode_path()),
                "-s", f"{encoding_run.input_sequence.get_width()}x{encoding_run.input_sequence.get_height()}",
                f"--FrameRate={encoding_run.input_sequence.get_framerate()}",
                f"--InputBitDepth={encoding_run.input_sequence.get_bit_depth()}",
                f"--InputChromaFormat={encoding_run.input_sequence.get_chroma()}",
                "-b", str(encoding_run.output_file.get_filepath()),
                "-f", str(encoding_run.frames * tester.Cfg().frame_step_size),
                "-o", os.devnull,
            ) + quality
        self.encode_finish(encode_cmd, encoding_run)

    class ParamSet(EncoderBase.ParamSet):
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

            self._quality_formats[tester.QualityParam.QP] = "-q "
            for t in range(tester.QualityParam.BITRATE.value, len(tester.QualityParam) + 1):
                self._quality_formats[tester.QualityParam(t)] = "--RateControl=2 --TargetBitrate="

        def _to_unordered_args_list(self,
                                    include_quality_param: bool = True,
                                    include_seek: bool = True,
                                    include_frames: bool = True,
                                    include_directory_data: bool = False) -> list:
            args = self._cl_args

            if include_quality_param:
                args += " " + " ".join(self.get_quality_value(self.get_quality_param_value()))

            if include_seek and self._seek:
                args += f" -fs {self._seek}"
            if include_frames and self._frames:
                args += f" -f {self._frames}"

            if include_directory_data:
                if tester.Cfg().frame_step_size != 1 and "TemporalSubsampleRatio" not in args:
                    args += f" --TemporalSubsampleRatio={tester.Cfg().frame_step_size}"
                args = args.replace("/", "-").replace("\\", "-").replace(":", "-")

            return args.split()

        @staticmethod
        def _get_arg_order() -> list:
            return ["-c"]
