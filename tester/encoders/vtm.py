"""This module defines all functionality specific to VTM."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from typing import Iterable
from pathlib import Path

import tester
import tester.core.test as test
from tester.core import ffmpeg, cmake, git, vs
import tester.core.cfg as cfg
from tester.core.log import console_log
from . import EncoderBase


class Vtm(EncoderBase):
    """Represents a VTM executable."""

    file_suffix = "vvc"

    def __init__(self,
                 user_given_revision: str,
                 defines: Iterable,
                 use_prebuilt: bool):
        super().__init__(
            name="VTM",
            user_given_revision=user_given_revision,
            defines=defines,
            git_local_path=cfg.Cfg().tester_sources_dir_path / "vtm",
            git_remote_url=cfg.Cfg().vtm_remote_url,
            use_prebuilt=use_prebuilt
        )

        self._exe_src_path: Path = None
        if cfg.Cfg().system_os_name == "Windows":
            self._exe_src_path = \
                self._git_local_path \
                / "bin" \
                / f"vs{cfg.Cfg().vs_major_version}" \
                / f"msvc-{cfg.Cfg().vs_msvc_version}" \
                / "x86_64" \
                / "release" \
                / "EncoderApp.exe"
        elif cfg.Cfg().system_os_name == "Linux":
            self._exe_src_path = self._git_local_path / "bin" / "EncoderAppStatic"

        self._decoder_exe_src_path: Path = None
        self._decoder_exe_path: Path = cfg.Cfg().tester_binaries_dir_path / f"vtmdecoder_{self._commit_hash_short}.exe"

        if cfg.Cfg().system_os_name == "Windows":
            self._decoder_exe_src_path = self._exe_src_path.with_name("DecoderApp.exe")
        elif cfg.Cfg().system_os_name == "Linux":
            self._decoder_exe_src_path = self._exe_src_path.with_name("DecoderAppStatic")

    def build(self) -> None:

        if not self.build_start():
            return

        build_cmd = ()
        if not (self._git_local_path / "build").exists():
            (self._git_local_path / "build").mkdir()

        if cfg.Cfg().system_os_name == "Windows":

            # Add defines to msbuild arguments.
            msbuild_args = vs.get_msbuild_args(add_defines=self._defines)

            # Configure CMake, run VsDevCmd.bat, then MSBuild.
            build_cmd = (
                            "cd", str(self._git_local_path),
                            "&&", "cd", "build",
                            "&&", "cmake", "..",
                            "-G", cmake.get_cmake_build_system_generator(),
                            "-A", cmake.get_cmake_architecture(),
                            "&&", "call", vs.get_vsdevcmd_bat_path(),
                            "&&", "msbuild", "NextSoftware.sln", r"/t:App\EncoderApp",
                        ) + tuple(msbuild_args)

        elif cfg.Cfg().system_os_name == "Linux":

            # Add defines to make arguments.
            cflags_str = f"CFLAGS={''.join([f'-D{define} ' for define in self._defines])}".strip()

            build_cmd = (
                "cd", str(self._git_local_path),
                "&&", "make", "EncoderApp-r", cflags_str
            )

        self.build_finish(build_cmd)

        self._build_decoder()

    def _build_decoder(self):

        console_log.info(f"VTM: Building executable {self._decoder_exe_src_path.name}")
        if self._decoder_exe_src_path.exists():
            console_log.info(f"VTM: Executable {self._decoder_exe_src_path.name} already exists")

        if cfg.Cfg().system_os_name == "Windows":

            decoder_build_cmd = (
                                    "cd", str(self._git_local_path),
                                    "&&", "cd", "build",
                                    "&&", "call", vs.get_vsdevcmd_bat_path(),
                                    "&&", "msbuild", "NextSoftware.sln", r"/t:App\DecoderApp",
                                ) + tuple(vs.get_msbuild_args())

        else:

            decoder_build_cmd = (
                "cd", str(self._git_local_path),
                "&&", "make", "DecoderApp-r",
            )

        # Build the executable.
        try:
            subprocess.check_output(
                subprocess.list2cmdline(decoder_build_cmd),
                shell=True,
                stderr=subprocess.STDOUT
            )
        except subprocess.CalledProcessError as exception:
            console_log.error(exception.output.decode())
            raise

        assert self._decoder_exe_src_path.exists()
        self._build_log.debug(f"{type(self).__name__}: Copying file '{self._decoder_exe_src_path}' "
                              f"to '{self._decoder_exe_path}'")
        try:
            shutil.copy(str(self._decoder_exe_src_path), str(self._decoder_exe_path))
        except FileNotFoundError as exception:
            console_log.error(str(exception))
            raise

    def clean(self) -> None:

        self.clean_start()

        clean_cmd = ()

        if cfg.Cfg().system_os_name == "Windows":

            clean_cmd = (
                "call", str(vs.get_vsdevcmd_bat_path()),
                "&&", "cd", str(self._git_local_path),
                "&&", "cd", "build",
                "&&", "msbuild", "NextSoftware.sln", r"/t:App\EncoderApp:clean"
            )

        elif cfg.Cfg().system_os_name == "Linux":

            clean_cmd = (
                "cd", str(self._git_local_path),
                "&&", "make", "clean", "EncoderApp-r"
            )

        self.clean_finish(clean_cmd)

        self._clean_decoder()

    def _clean_decoder(self):

        decoder_clean_cmd = ()

        if cfg.Cfg().system_os_name == "Windows":

            decoder_clean_cmd = (
                "call", str(vs.get_vsdevcmd_bat_path()),
                "&&", "cd", str(self._git_local_path),
                "&&", "cd", "build",
                "&&", "msbuild", "NextSoftware.sln", r"/t:App\DecoderApp:clean"
            )

        elif cfg.Cfg().system_os_name == "Linux":

            decoder_clean_cmd = (
                "cd", str(self._git_local_path),
                "&&", "make", "clean", "DecoderApp-r"
            )

        try:
            subprocess.check_output(
                subprocess.list2cmdline(decoder_clean_cmd),
                shell=True,
                stderr=subprocess.STDOUT
            )
        except subprocess.CalledProcessError as exception:
            console_log.error(exception.output.decode())
            raise

    def dummy_run(self, param_set: EncoderBase.ParamSet, env) -> bool:

        self.dummy_run_start(param_set)

        FRAMERATE_PLACEHOLDER = "1"
        WIDTH_PLACEHOLDER = "16"
        HEIGHT_PLACEHOLDER = "16"
        FRAMECOUNT_PLACEHOLDER = "1"

        dummy_sequence_path = ffmpeg.generate_dummy_sequence()

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

        return_value = self.dummy_run_finish(dummy_cmd, param_set, env)

        os.remove(str(dummy_sequence_path))

        return return_value

    def encode(self,
               encoding_run: test.EncodingRun) -> None:

        if not self.encode_start(encoding_run):
            return

        if encoding_run.qp_name == tester.QualityParam.QP:
            quality = (f"--QP={encoding_run.qp_value}",)
        elif encoding_run.qp_name in (tester.QualityParam.BITRATE,
                                      tester.QualityParam.RES_SCALED_BITRATE,
                                      tester.QualityParam.BPP,
                                      tester.QualityParam.RES_ROOT_SCALED_BITRATE):
            quality = (f"--TargetBitrate={encoding_run.qp_value}", "--RateControl=1")
        else:
            assert 0, "Invalid quality parameter"

        encode_cmd = \
            (
                str(self._exe_path),
            ) + encoding_run.param_set.to_cmdline_tuple(include_quality_param=False,
                                                        include_frames=False) + (
                "-i", str(encoding_run.input_sequence.get_filepath()),
                "-fr", str(encoding_run.input_sequence.get_framerate()),
                "-wdt", str(encoding_run.input_sequence.get_width()),
                "-hgt", str(encoding_run.input_sequence.get_height()),
                "-b", str(encoding_run.output_file.get_filepath()),
                "-f", str(encoding_run.frames * cfg.Cfg().frame_step_size),
                "-o", os.devnull,
            ) + quality

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

    @staticmethod
    def validate_config(test_config: test.Test):
        if not git.git_remote_exists(cfg.Cfg().vtm_remote_url):
            console_log.error(f"VTM: Remote '{cfg.Cfg().vtm_remote_url}' is not available")
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
        """Represents the command line parameters passed to VTM when encoding."""

        @staticmethod
        def _get_arg_order() -> list:
            return ["-c"]

        def _to_unordered_args_list(self,
                                    include_quality_param: bool = True,
                                    include_seek: bool = True,
                                    include_frames: bool = True,
                                    include_directory_data: bool = False) -> list:

            args = self._cl_args

            if include_quality_param:
                if self._quality_param_type == tester.QualityParam.QP:
                    args += f" --QP={self._quality_param_value}"
                elif self._quality_param_type == tester.QualityParam.BITRATE:
                    args += f" --TargetBitrate={self._quality_param_value}"
                elif self.get_quality_param_type() == tester.QualityParam.BPP:
                    args += f" --TargetBitrate={self._quality_param_value}"
                elif self.get_quality_param_type() == tester.QualityParam.RES_SCALED_BITRATE:
                    args += f" --TargetBitrate={self._quality_param_value}"
                elif self.get_quality_param_type() == tester.QualityParam.RES_ROOT_SCALED_BITRATE:
                    args += f" --TargetBitrate={self._quality_param_value}"
                else:
                    raise ValueError(
                        f"{self.get_quality_param_type().pretty_name} not available for encoder {str(self)}")
            if include_seek and self._seek:
                args += f" -fs {self._seek}"
            if include_frames and self._frames:
                args += f" -f {self._frames}"

            # TODO: Figure out why this is needed or if it's needed.
            if not "--SEIDecodedPictureHash" in args:
                args += " --SEIDecodedPictureHash=3"
            if not "--ConformanceWindowMode" in args:
                args += " --ConformanceWindowMode=1"

            if include_directory_data:
                if tester.Cfg().frame_step_size != 1:
                    args += f" --TemporalSubsampleRatio={tester.Cfg().frame_step_size}"
                args = args.replace("/", "-").replace("\\", "-").replace(":", "-")

            return args.split()
