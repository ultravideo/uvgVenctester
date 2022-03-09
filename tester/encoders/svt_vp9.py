from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Iterable

import tester
import tester.core.test as test
from tester.core import vs, ffmpeg
from tester.core.log import console_log
from . import EncoderBase


class SvtVp9(EncoderBase):
    file_suffix = "vp9"

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

            self._quality_formats[tester.QualityParam.QP] = "-rc 0 -q "
            for t in range(tester.QualityParam.BITRATE.value, len(tester.QualityParam) + 1):
                self._quality_formats[tester.QualityParam(t)] = "-tbr "
            # This checks the integrity of the parameters.
            self.to_cmdline_tuple(include_quality_param=False)

        def _to_unordered_args_list(self,
                                    include_quality_param: bool = True,
                                    include_seek: bool = True,
                                    include_frames: bool = True,
                                    include_directory_data: bool = False) -> list:
            args = self.get_cl_args()

            if include_quality_param:
                args += " " + " ".join(self.get_quality_value(self.get_quality_param_value()))

            if include_seek and self._seek:
                raise ValueError("SVT VP9 does not support seeking")

            if include_frames and self._frames:
                args += f" -n {self._frames}"

            if include_directory_data:
                if tester.Cfg().frame_step_size != 1:
                    args += f" --temporal_subsample {tester.Cfg().frame_step_size}"
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
            name="svt_vp9",
            user_given_revision=user_given_revision,
            defines=defines,
            git_local_path=tester.Cfg().tester_sources_dir_path / "svt_vp9",
            git_remote_url=tester.Cfg().svt_vp9_remote_url,
            use_prebuilt=use_prebuilt,
        )

        self._exe_src_path: Path = None
        self._dll_name: str = "SvtVp9Enc.dll"
        self.sln = "svt-vp9.sln"
        if tester.Cfg().system_os_name == "Windows":
            self._exe_src_path = self._git_local_path / "Bin" / "Release" / "SvtVp9EncApp.exe"
        elif tester.Cfg().system_os_name == "Linux":
            self._exe_src_path = self._git_local_path / "Bin" / "Release" / "SvtVp9EncApp"

    def build(self) -> bool:
        if not self.build_start():
            return False

        env = None

        if tester.Cfg().system_os_name == "Windows":
            if self.get_defines():
                env = os.environ
                temp = " ".join([f"/D{x}".replace("=", "#") for x in self.get_defines()])
                env["CL"] = temp

            build_cmd = (
                "cd", str(self._git_local_path / "Build" / "windows"),
                "&&", r".\build.bat", "release"
            )

        elif tester.Cfg().system_os_name == "Linux":
            raise NotImplementedError

        finish = self.build_finish(build_cmd, env)
        if finish:
            shutil.copy(self._exe_src_path / ".." / self._dll_name,
                        self._exe_path / ".." / self._dll_name)
        return finish

    def clean(self) -> None:
        self.clean_start()

        clean_cmd = ()

        if tester.Cfg().system_os_name == "Linux":
            raise NotImplementedError

        elif tester.Cfg().system_os_name == "Windows":
            msbuild_args = vs.get_msbuild_args(target="Clean")
            clean_cmd = (
                            "call", str(vs.get_vsdevcmd_bat_path()),
                            "&&", "msbuild", str(self._git_local_path / "build" / "windows" / self.sln)
                        ) + tuple(msbuild_args)

        self.clean_finish(clean_cmd)

    def dummy_run(self, param_set: EncoderBase.ParamSet, env) -> bool:

        self.dummy_run_start(param_set)

        RESOLUTION_PLACEHOLDER = "64"

        dummy_cmd = \
            (
                str(self._exe_path),
                "-i", os.devnull,
                "-w", RESOLUTION_PLACEHOLDER,
                "-h", RESOLUTION_PLACEHOLDER,
                "-b", os.devnull,
                "-n", "1"
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
                "-i", str(encoding_run.input_sequence.get_encode_path()),
                "-w", str(encoding_run.input_sequence.get_width()),
                "-h", str(encoding_run.input_sequence.get_height()),
                "-fps", str(encoding_run.input_sequence.get_framerate()),
                "-n", str(encoding_run.frames),
                "-b", str(encoding_run.output_file.get_filepath()),
            ) + encoding_run.param_set.to_cmdline_tuple(include_quality_param=False,
                                                        include_frames=False) + quality

        self.encode_finish(encode_cmd, encoding_run)


class SvtAv1(SvtVp9):
    file_suffix = "av1"

    def __init__(self,
                 user_given_revision: str,
                 defines: Iterable,
                 use_prebuilt: bool):
        super(SvtVp9, self).__init__(
            name="svt_av1",
            user_given_revision=user_given_revision,
            defines=defines,
            git_local_path=tester.Cfg().tester_sources_dir_path / "svt_av1",
            git_remote_url=tester.Cfg().svt_av1_remote_url,
            use_prebuilt=use_prebuilt,
        )

        self._exe_src_path: Path = None
        self._dll_name: str = "SvtAv1Enc.dll"
        self.sln = "svt-av1.sln"
        if tester.Cfg().system_os_name == "Windows":
            self._exe_src_path = self._git_local_path / "Bin" / "Release" / "SvtAv1EncApp.exe"
        elif tester.Cfg().system_os_name == "Linux":
            self._exe_src_path = self._git_local_path / "Bin" / "Release" / "SvtAv1EncApp"

    def dummy_run(self, param_set: EncoderBase.ParamSet, env) -> bool:

        self.dummy_run_start(param_set)

        RESOLUTION_PLACEHOLDER = "64"
        dummy_sequence_path = ffmpeg.generate_dummy_sequence(RESOLUTION_PLACEHOLDER)

        dummy_cmd = \
            (
                str(self._exe_path),
                "-i", str(dummy_sequence_path),
                "-w", RESOLUTION_PLACEHOLDER,
                "-h", RESOLUTION_PLACEHOLDER,
                "-b", os.devnull,
                "-n", "1"
            ) + param_set.to_cmdline_tuple()

        finish = self.dummy_run_finish(dummy_cmd, param_set, env)
        os.remove(str(dummy_sequence_path))
        return finish


    def encode(self,
               encoding_run: test.EncodingRun) -> None:
        if not self.encode_start(encoding_run):
            return

        quality = encoding_run.param_set.get_quality_value(encoding_run.qp_value)

        encode_cmd = \
            (
                str(self._exe_path),
                "-i", str(encoding_run.input_sequence.get_encode_path()),
                "-w", str(encoding_run.input_sequence.get_width()),
                "-h", str(encoding_run.input_sequence.get_height()),
                "--fps", str(encoding_run.input_sequence.get_framerate()),
                "-n", str(encoding_run.frames),
                "-b", str(encoding_run.output_file.get_filepath()),
            ) + encoding_run.param_set.to_cmdline_tuple(include_quality_param=False,
                                                        include_frames=False) + quality

        self.encode_finish(encode_cmd, encoding_run)

    class ParamSet(SvtVp9.ParamSet):
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

            self._quality_formats[tester.QualityParam.QP] = "--rc 0 -q "
            for t in range(tester.QualityParam.BITRATE.value, len(tester.QualityParam) + 1):
                self._quality_formats[tester.QualityParam(t)] = "--tbr "
            # This checks the integrity of the parameters.
            self.to_cmdline_tuple(include_quality_param=False)
