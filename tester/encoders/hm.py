"""This module defines all functionality specific to HM."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Iterable

import tester
import tester.core.git as git
import tester.core.test as test
from tester.core import cmake, vs
from tester.core.log import console_log
from . import EncoderBase


class Hm(EncoderBase):
    """Represents a HM executable."""

    def __init__(self,
                 user_given_revision: str,
                 defines: Iterable,
                 use_prebuilt: bool):
        super().__init__(
            name="HM",
            user_given_revision=user_given_revision,
            defines=defines,
            git_local_path=tester.Cfg().tester_sources_dir_path / "hm",
            git_remote_url=tester.Cfg().hm_remote_url,
            use_prebuilt=use_prebuilt,
        )

        self._exe_src_path: Path = None
        if tester.Cfg().system_os_name == "Windows":
            self._exe_src_path = \
                self._git_local_path \
                / "bin" \
                / f"vs{tester.Cfg().vs_major_version}" \
                / f"msvc-{tester.Cfg().vs_msvc_version}" \
                / "x86_64" \
                / "release" \
                / "TAppEncoder.exe"
        elif tester.Cfg().system_os_name == "Linux":
            self._exe_src_path = self._git_local_path / "bin" / "TAppEncoderStatic"

    def build(self) -> bool:

        if not self.build_start():
            return False

        build_cmd = ()
        env = None
        if not (self._git_local_path / "build").exists():
            (self._git_local_path / "build").mkdir()

        if tester.Cfg().system_os_name == "Windows":

            # Add defines to msbuild arguments.
            msbuild_args = vs.get_msbuild_args()
            if self.get_defines():
                env = os.environ
                temp = " ".join([f"/D{x}".replace("=", "#") for x in self.get_defines()])
                env["CL"] = temp

            # Configure CMake, run VsDevCmd.bat, then MSBuild.
            build_cmd = (
                            "cd", str(self._git_local_path),
                            "&&", "cd", "build",
                            "&&", "cmake", "..",
                            "-G", cmake.get_cmake_build_system_generator(),
                            "-A", cmake.get_cmake_architecture(),
                            "&&", "call", vs.get_vsdevcmd_bat_path(),
                            "&&", "msbuild", "HM.sln", f"/t:App\\TAppEncoder",
                        ) + tuple(msbuild_args)

        elif tester.Cfg().system_os_name == "Linux":

            # Add defines to make arguments.
            cflags_str = f"CFLAGS={''.join([f'-D{define} ' for define in self._defines])}".strip()

            build_cmd = (
                "cd", str(self._git_local_path),
                "&&", "make", "TAppEncoder-r", cflags_str
            )

        return self.build_finish(build_cmd, env)

    def clean(self) -> None:

        self.clean_start()

        clean_cmd = ()

        if tester.Cfg().system_os_name == "Windows":

            clean_cmd = (
                "call", str(vs.get_vsdevcmd_bat_path()),
                "&&", "cd", str(self._git_local_path),
                "&&", "cd", "build",
                "&&", "msbuild", "HM.sln", f"/t:App\\TAppEncoder:clean"
            )

        elif tester.Cfg().system_os_name == "Linux":
            clean_cmd = (
                "cd", str(self._git_local_path),
                "&&", "make", "clean"
            )

        self.clean_finish(clean_cmd)

    def dummy_run(self, param_set: EncoderBase.ParamSet, env) -> bool:

        self.dummy_run_start(param_set)

        FRAMERATE_PLACEHOLDER = "1"
        WIDTH_PLACEHOLDER = "16"
        HEIGHT_PLACEHOLDER = "16"
        FRAMECOUNT_PLACEHOLDER = "1"

        dummy_cmd = \
            (
                str(self._exe_path),
                "-i", os.devnull,
                "-fr", FRAMERATE_PLACEHOLDER,
                "-wdt", WIDTH_PLACEHOLDER,
                "-hgt", HEIGHT_PLACEHOLDER,
                # Just in case the parameter set doesn't contain the number of frames parameter.
                "-f", FRAMECOUNT_PLACEHOLDER,
            ) + param_set.to_cmdline_tuple(include_frames=False) + (
                "-b", os.devnull,
                "-o", os.devnull,
            )

        return self.dummy_run_finish(dummy_cmd, param_set, env)

    def encode(self,
               encoding_run: tester.EncodingRun) -> None:

        if not self.encode_start(encoding_run):
            return

        quality = encoding_run.param_set.get_quality_value(encoding_run.qp_value)

        encode_cmd = \
            (
                str(self._exe_path),
            ) + encoding_run.param_set.to_cmdline_tuple(include_quality_param=False,
                                                        include_frames=False) + (
                "-i", str(encoding_run.input_sequence.get_encode_path()),
                "-fr", str(encoding_run.input_sequence.get_framerate()),
                "-wdt", str(encoding_run.input_sequence.get_width()),
                "-hgt", str(encoding_run.input_sequence.get_height()),
                "-b", str(encoding_run.output_file.get_filepath()),
                f"--InputChromaFormat={encoding_run.input_sequence.get_chroma()}",
                "-f", str(encoding_run.frames * tester.Cfg().frame_step_size),
                "-o", os.devnull,
            ) + quality
        self.encode_finish(encode_cmd, encoding_run)

    @staticmethod
    def validate_config(test_config: test.Test):
        # Using the public property raises an exception, so access the private attribute instead.
        if not test_config.use_prebuilt and not git.git_remote_exists(tester.Cfg().hm_remote_url):
            console_log.error(f"HM: Remote '{tester.Cfg().hm_remote_url}' is not available")
            raise RuntimeError

        args = test_config.subtests[0].param_set._to_args_dict(False, False, False)
        pattern = re.compile(r"TemporalSubsampleRatio.*: (\d+)", re.DOTALL)
        # Test if
        for key, value in args.items():
            if key == "-c":
                with open(value, "r") as f:
                    for line in f:
                        match = pattern.match(line)
                        if match:
                            assert int(match[1]) == tester.Cfg().frame_step_size
                            break
            elif key == "--TemporalSubsampleRatio":
                assert int(value) == tester.Cfg().frame_step_size

    class ParamSet(EncoderBase.ParamSet):
        """Represents the command line parameters passed to HM when encoding."""
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

            self._quality_formats[tester.QualityParam.QP] = "--QP="
            for t in range(tester.QualityParam.BITRATE.value, len(tester.QualityParam) + 1):
                self._quality_formats[tester.QualityParam(t)] = "--RateControl=1 --TargetBitrate="

        @staticmethod
        def _get_arg_order() -> list:
            return ["-c"]

        def _to_unordered_args_list(self,
                                    include_quality_param: bool = True,
                                    include_seek: bool = True,
                                    include_frames: bool = True,
                                    include_directory_data=False) -> list:

            args = self._cl_args

            if include_quality_param:
                args += " " + " ".join(self.get_quality_value(self.get_quality_param_value()))

            if include_seek and self._seek:
                args += f" -fs {self._seek}"
            if include_frames and self._frames:
                args += f" -f {self._frames}"
            # TODO: Figure out why this is needed or if it's needed.
            if not "--SEIDecodedPictureHash" in args:
                args += " --SEIDecodedPictureHash=3"

            if include_directory_data:
                if tester.Cfg().frame_step_size != 1:
                    args += f" --TemporalSubsampleRatio={tester.Cfg().frame_step_size}"
                args = args.replace("/", "-").replace("\\", "-").replace(":", "-")

            return args.split()
