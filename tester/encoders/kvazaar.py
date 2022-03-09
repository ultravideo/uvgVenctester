"""This module defines all functionality specific to Kvazaar."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Iterable

import tester
import tester.core.git as git
import tester.core.test as test
from tester.core import vs
from tester.core.log import console_log
from . import EncoderBase


class Kvazaar(EncoderBase):
    """Represents a Kvazaar executable."""

    class ParamSet(EncoderBase.ParamSet):
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

            self._quality_formats[tester.QualityParam.QP] = "--qp "
            self._quality_formats[tester.QualityParam.CRF] = "--crf "
            for t in range(tester.QualityParam.BITRATE.value, len(tester.QualityParam) + 1):
                self._quality_formats[tester.QualityParam(t)] = "--bitrate "
            # This checks the integrity of the parameters.
            self.to_cmdline_tuple(include_quality_param=False)

        def _to_unordered_args_list(self,
                                    include_quality_param: bool = True,
                                    include_seek: bool = True,
                                    include_frames: bool = True,
                                    include_directory_data=False) -> list:

            args = self._cl_args

            if include_quality_param:
                args += " " + " ".join(self.get_quality_value(self.get_quality_param_value()))

            if include_seek and self._seek:
                args += f" --seek {self._seek}"
            if include_frames and self._frames:
                args += f" --frames {self._frames}"

            if include_directory_data:
                if tester.Cfg().frame_step_size != 1:
                    args += f" --temporal_subsample {tester.Cfg().frame_step_size}"
                args = args.replace("/", "-").replace("\\", "-").replace(":", "-")

            split_args: list = []

            # Split the arguments such that each option and its value, if any, are separated.
            for item in args.split():
                if EncoderBase.ParamSet._is_short_option(item):
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

    def __init__(self,
                 user_given_revision: str,
                 defines: Iterable,
                 use_prebuilt: bool):
        super().__init__(
            name="Kvazaar",
            user_given_revision=user_given_revision,
            defines=defines,
            git_local_path=tester.Cfg().tester_sources_dir_path / "kvazaar",
            git_remote_url=tester.Cfg().kvazaar_remote_url,
            use_prebuilt=use_prebuilt,
        )
        self._solution = "kvazaar_VS2015.sln"
        self._exe_src_path: Path = None
        if tester.Cfg().system_os_name == "Windows":
            self._exe_src_path = self._git_local_path / "bin" / "x64-Release" / "kvazaar.exe"
        elif tester.Cfg().system_os_name == "Linux":
            self._exe_src_path = self._git_local_path / "src" / "kvazaar"

    def build(self) -> bool:

        if not self.build_start():
            return False

        build_cmd = ()
        env = None

        if tester.Cfg().system_os_name == "Windows":

            # Add defines to msbuild arguments.
            msbuild_args = vs.get_msbuild_args()
            if self.get_defines():
                env = os.environ
                temp = " ".join([f"/D{x}".replace("=", "#") for x in self.get_defines()])
                env["CL"] = temp

            # Run VsDevCmd.bat, then msbuild.
            build_cmd = (
                            "call", str(vs.get_vsdevcmd_bat_path()),
                            "&&", "msbuild", str(self._git_local_path / "build" / self._solution)
                        ) + tuple(msbuild_args)

        elif tester.Cfg().system_os_name == "Linux":

            # Add defines to configure arguments.
            kvz_configure_args = ["--disable-shared", "--enable-static", ]
            if self._defines:
                cflags_str = f"CFLAGS={''.join([f'-D{define} ' for define in self._defines])}"
                kvz_configure_args.append(cflags_str.strip())

            # Run autogen.sh, then configure, then make.
            build_cmd = (
                            "cd", str(self._git_local_path),
                            "&&", "./autogen.sh",
                            "&&", "./configure",) + tuple(kvz_configure_args) + (
                            "&&", "make",
                        )

        return self.build_finish(build_cmd, env)

    def clean(self) -> None:

        self.clean_start()

        clean_cmd = ()

        if tester.Cfg().system_os_name == "Linux":
            clean_cmd = (
                "cd", str(self._git_local_path),
                "&&", "make", "clean",
            )

        elif tester.Cfg().system_os_name == "Windows":
            msbuild_args = vs.get_msbuild_args(target="Clean")
            clean_cmd = (
                            "call", str(vs.get_vsdevcmd_bat_path()),
                            "&&", "msbuild", str(self._git_local_path / "build" / self._solution)
                        ) + tuple(msbuild_args)

        self.clean_finish(clean_cmd)

    def dummy_run(self, param_set: EncoderBase.ParamSet, env) -> bool:

        self.dummy_run_start(param_set)

        RESOLUTION_PLACEHOLDER = "2x2"

        dummy_cmd = \
            (
                str(self._exe_path),
                "-i", os.devnull,
                "--input-res", RESOLUTION_PLACEHOLDER,
                "-o", os.devnull,
            ) + param_set.to_cmdline_tuple()

        return self.dummy_run_finish(dummy_cmd, param_set, env)

    def encode(self,
               encoding_run: test.EncodingRun) -> None:

        if not self.encode_start(encoding_run):
            return

        quality = encoding_run.param_set.get_quality_value(encoding_run.qp_value)

        encode_cmd = \
            (
                str(self._exe_path),
                "-i",
                str(encoding_run.input_sequence.get_encode_path()) if tester.Cfg().frame_step_size == 1 else "-",
                "--input-res",
                f"{encoding_run.input_sequence.get_width()}x{encoding_run.input_sequence.get_height()}",
                "--input-fps", str(encoding_run.input_sequence.get_framerate()),
                "-o", str(encoding_run.output_file.get_filepath()),
                "--frames", str(encoding_run.frames),
                "--input-format", f"P{encoding_run.input_sequence.get_chroma()}"
            ) + encoding_run.param_set.to_cmdline_tuple(include_quality_param=False,
                                                        include_frames=False) + quality

        self.encode_finish(encode_cmd, encoding_run, tester.Cfg().frame_step_size != 1)

    @staticmethod
    def validate_config(test_config: test.Test):
        if not test_config.use_prebuilt and not git.git_remote_exists(tester.Cfg().kvazaar_remote_url):
            console_log.error(f"Kvazaar: Remote '{tester.Cfg().kvazaar_remote_url}' is unavailable")
            raise RuntimeError


class Uvg266(Kvazaar):
    file_suffix = "vvc"

    def __init__(self,
                 user_given_revision: str,
                 defines: Iterable,
                 use_prebuilt: bool):
        super(Kvazaar, self).__init__(
            name="UVG266",
            user_given_revision=user_given_revision,
            defines=defines,
            git_local_path=tester.Cfg().tester_sources_dir_path / "uvg266",
            git_remote_url=tester.Cfg().uvg266_remote_url,
            use_prebuilt=use_prebuilt,
        )

        self._solution = "kvazaar_VS2017.sln"
        self._exe_src_path: Path = None
        if tester.Cfg().system_os_name == "Windows":
            self._exe_src_path = self._git_local_path / "bin" / "x64-Release" / "kvazaar.exe"
        elif tester.Cfg().system_os_name == "Linux":
            self._exe_src_path = self._git_local_path / "src" / "kvazaar"

        self._decoder_exe_path: Path = tester.Cfg().vvc_reference_decoder

    def _decode(self,
                encoding_run: test.EncodingRun):

        decode_cmd = (
            str(self._decoder_exe_path),
            "-b", str(encoding_run.output_file.get_filepath()),
            "-o", str(encoding_run.decoded_output_file_path),
            "-d", str(encoding_run.input_sequence.get_bit_depth())
        )

        try:
            with open(encoding_run.get_log_path("decode"), "w") as decode_log:
                subprocess.run(
                    decode_cmd,
                    stderr=decode_log,
                    stdout=decode_log
                )
        except Exception:
            console_log.error(f"{type(self.__name__)}: Failed to decode file "
                              f"'{encoding_run.output_file.get_filepath()}'")
            raise

    @staticmethod
    def validate_config(test_config: test.Test):
        # Using the public property raises an exception, so access the private attribute instead.
        if not git.git_remote_exists(tester.Cfg().uvg266_remote_url):
            console_log.error(f"UVG266: Remote '{tester.Cfg().uvg266_remote_url}' is not available")
            raise RuntimeError

        if not tester.Cfg().vvc_reference_decoder.exists() or tester.Cfg().vvc_reference_decoder == Path("."):
            raise RuntimeError("UVG266: VVC reference decoder is needed for decoding VVC currently")
