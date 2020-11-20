"""This module defines all functionality specific to x265."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

import tester
import tester.core.git as git
import tester.core.test as test
from . import EncoderBase
from ..core import vs, cmake


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

    def build(self) -> None:
        if not self.build_start():
            return
        
        build_cmd = tuple()

        if tester.Cfg().system_os_name == "Windows":
            build_dir = self._git_local_path / "build" / tester.Cfg().x265_build_folder
            cmake_cmd = ""
            # A bit hacky, but minimizes user configuration. TODO: Unify with vs handling?
            with open(build_dir / tester.Cfg().x265_make_solution_bat) as cmake_bat:
                for line in cmake_bat:
                    if line.strip().startswith("cmake"):
                        cmake_cmd = line.split("&&")[0].strip()

            build_cmd = (
                "cd", build_dir,
                "&&", "call", str(vs.get_vsdevcmd_bat_path()),
                "&&", "cmake", "../../source",
                "-G", cmake.get_cmake_build_system_generator(),
                "-A", cmake.get_cmake_architecture(),
                f"-DNASM_EXECUTABLE={tester.Cfg().nasm_path}" if tester.Cfg().nasm_path else "",
                "&&", "msbuild", "x265.sln"
            ) + tuple(vs.get_msbuild_args(self._defines))
        elif tester.Cfg().system_os_name == "Linux":
            build_cmd = (
                "cd", str(self._git_local_path / "build" / "linux"),
                "&&", "./make-Makefiles.bash",
                "&&", "make",
            )

        self.build_finish(build_cmd)

    def clean(self) -> None:
        self.clean_start()

        clean_cmd = ()

        if tester.Cfg().system_os_name == "Linux":
            clean_cmd = (
                "cd", str(self._git_local_path / "build" / "linux"),
                "&&", "make", "clean",
            )

        self.clean_finish(clean_cmd)

    def dummy_run(self,
                  param_set: EncoderBase.ParamSet) -> bool:
        self.dummy_run_start(param_set)

        RESOLUTION_PLACEHOLDER = "64x64"

        dummy_cmd = (
            str(self._exe_path),
            "--input", os.devnull,
            "--input-res", RESOLUTION_PLACEHOLDER,
            "--fps", "25",
            "--output", os.devnull,
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
        elif encoding_run.qp_name == tester.QualityParam.CRF:
            quality = ("--crf", str(encoding_run.qp_value))
        else:
            assert 0, "Invalid quality parameter"

        encode_cmd = (
            str(self._exe_path),
            "--input", str(encoding_run.input_sequence.get_filepath()) if tester.Cfg().frame_step_size == 1 else "-",
            "--input-res", f"{encoding_run.input_sequence.get_width()}x{encoding_run.input_sequence.get_height()}",
            "--fps", str(encoding_run.input_sequence.get_framerate()),
            "--output", str(encoding_run.output_file.get_filepath()),
            "--frames", str(encoding_run.frames),
        ) + encoding_run.param_set.to_cmdline_tuple(include_quality_param=False, include_frames=False) + quality

        self.encode_finish(encode_cmd, encoding_run, tester.Cfg().frame_step_size != 1)

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

            # This checks the integrity of the parameters.
            self.to_cmdline_tuple(include_quality_param=False)

        @staticmethod
        def _get_arg_order() -> list:
            return [] # "--preset" and "--tune" should be handled correctly despite their position

        def _to_unordered_args_list(self,
                                    include_quality_param: bool = True,
                                    include_seek: bool = True,
                                    include_frames: bool = True,
                                    inode_safe: bool = False) -> list:

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
                elif self.get_quality_param_type() == tester.QualityParam.CRF:
                    args += f" --crf {self._quality_param_value}"
                else:
                    raise ValueError(f"{self.get_quality_param_type().pretty_name} not available for encoder {str(self)}")

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
