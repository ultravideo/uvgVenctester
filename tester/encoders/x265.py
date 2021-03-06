"""This module defines all functionality specific to x265."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Iterable

import tester
import tester.core.git as git
import tester.core.test as test
from tester.core import cmake, vs
from tester.core.log import console_log
from . import EncoderBase


class X265(EncoderBase):
    """Represents a x265 executable."""

    def __init__(self,
                 user_given_revision: str,
                 defines: Iterable,
                 use_prebuilt: bool):

        super().__init__(
            name="x265",
            user_given_revision=user_given_revision,
            defines=defines,
            git_local_path=tester.Cfg().tester_sources_dir_path / "x265_git",
            git_remote_url=tester.Cfg().x265_remote_url,
            use_prebuilt=use_prebuilt,
        )
        # TODO: check that exe paths are correct
        self._exe_src_path: Path = None
        if tester.Cfg().system_os_name == "Windows":
            self._exe_src_path = self._git_local_path / "build" / tester.Cfg().x265_build_folder / "Release" / "x265.exe"
        elif tester.Cfg().system_os_name == "Linux":
            self._exe_src_path = self._git_local_path / "build" / "linux" / "x265"

    def build(self) -> bool:
        if not self.build_start():
            return False

        env = None
        build_cmd = tuple()

        if tester.Cfg().system_os_name == "Windows":
            build_dir = self._git_local_path / "build" / tester.Cfg().x265_build_folder
            if self.get_defines():
                env = os.environ
                temp = " ".join([f"/D{x}".replace("=", "#") for x in self.get_defines()])
                env["CL"] = temp
            build_cmd = \
                (
                    "cd", build_dir,
                    "&&", "call", str(vs.get_vsdevcmd_bat_path()),
                    "&&", "cmake", "../../source",
                    "-G", cmake.get_cmake_build_system_generator(),
                    "-A", cmake.get_cmake_architecture(),
                ) + (
                    (f"-DNASM_EXECUTABLE={tester.Cfg().nasm_path}",) if tester.Cfg().nasm_path else tuple()
                ) + (
                    "&&", "msbuild", "x265.sln",
                ) + tuple(vs.get_msbuild_args(self._defines))
        elif tester.Cfg().system_os_name == "Linux":
            build_cmd = \
                (
                    "cd", str(self._git_local_path / "build" / "linux"),
                    "&&", "cmake", "../../source", "-DENABLE_SHARED=OFF",
                )
            if tester.Cfg().nasm_path:
                build_cmd += (
                    f"-DNASM_EXECUTABLE={tester.Cfg().nasm_path}",
                )
            if self.get_defines():
                build_cmd += (
                    "-DCMAKE_CXX_FLAGS " + " ".join([f"-D{x}" for x in self.get_defines()])
                )

            build_cmd += (
                    "&&", "make",
                )
        return self.build_finish(build_cmd, env)

    def clean(self) -> None:
        self.clean_start()

        clean_cmd = ()

        if tester.Cfg().system_os_name == "Linux":
            clean_cmd = (
                "cd", str(self._git_local_path / "build" / "linux"),
                "&&", "make", "clean",
            )

        elif tester.Cfg().system_os_name == "Windows":
            msbuild_args = vs.get_msbuild_args(target="Clean")
            clean_cmd = (
                            "call", str(vs.get_vsdevcmd_bat_path()),
                            "&&", "msbuild", str(self._git_local_path / "build" / tester.Cfg().x265_build_folder)
                        ) + tuple(msbuild_args)

        self.clean_finish(clean_cmd)

    def dummy_run(self, param_set: EncoderBase.ParamSet, env) -> bool:
        self.dummy_run_start(param_set)

        RESOLUTION_PLACEHOLDER = "64x64"

        dummy_cmd = (
                        str(self._exe_path),
                        "--input", os.devnull,
                        "--input-res", RESOLUTION_PLACEHOLDER,
                        "--fps", "25",
                        "--output", os.devnull,
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
                "--input",
                str(encoding_run.input_sequence.get_encode_path()) if tester.Cfg().frame_step_size == 1 else "-",
                "--input-res", f"{encoding_run.input_sequence.get_width()}x{encoding_run.input_sequence.get_height()}",
                "--fps", str(encoding_run.input_sequence.get_framerate()),
                "--output", str(encoding_run.output_file.get_filepath()),
                "--frames", str(encoding_run.frames),
                "--input-csp", f"i{encoding_run.input_sequence.get_chroma()}"
            ) + encoding_run.param_set.to_cmdline_tuple(include_quality_param=False,
                                                        include_frames=False) + quality

        self.encode_finish(encode_cmd, encoding_run, tester.Cfg().frame_step_size != 1)

    @staticmethod
    def validate_config(test_config: test.Test):
        if not test_config.use_prebuilt and not git.git_remote_exists(tester.Cfg().x265_remote_url):
            console_log.error(f"x265: Remote '{tester.Cfg().x265_remote_url}' is unavailable")
            raise RuntimeError

        try:
            subprocess.check_output((tester.Cfg().nasm_path, "--version"))
        except FileNotFoundError:
            console_log.warning(f"x265: Executable 'nasm' was not found. The x265 is going to be much slower.")

    class ParamSet(EncoderBase.ParamSet):
        """Represents the commandline parameters passed to x265 when encoding."""

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
                self._quality_scales[tester.QualityParam(t)] = 1000
            # This checks the integrity of the parameters.
            self.to_cmdline_tuple(include_quality_param=False)

        @staticmethod
        def _get_arg_order() -> list:
            return []  # "--preset" and "--tune" should be handled correctly despite their position

        def _to_unordered_args_list(self,
                                    include_quality_param: bool = True,
                                    include_seek: bool = True,
                                    include_frames: bool = True,
                                    inode_safe: bool = False) -> list:

            args = self._cl_args

            if include_quality_param:
                args += " " + " ".join(self.get_quality_value(self.get_quality_param_value()))

            if include_seek and self._seek:
                args += f" --seek {self._seek}"
            if include_frames and self._frames:
                args += f" --frames {self._frames}"

            if inode_safe:
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
