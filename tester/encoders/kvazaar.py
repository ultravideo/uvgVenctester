"""This module defines all functionality specific to Kvazaar."""

from __future__ import annotations

from .base import *
from tester.core.test import *


class KvazaarParamSet(ParamSetBase):
    """Represents the command line parameters passed to Kvazaar when encoding."""

    # These have to be the first two arguments on the command line.
    POSITIONAL_ARGS = ("--preset", "--gop")

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

        # This checks the integrity of the parameters.
        self.to_cmdline_tuple()

    def _to_unordered_args_list(self,
                                include_quality_param: bool = True,
                                include_seek: bool = True,
                                include_frames: bool = True) -> list:

        args = self._cl_args

        if include_quality_param:
            if self._quality_param_type == QualityParam.QP:
                args += f" --qp {self._quality_param_value}"
            elif self._quality_param_type == QualityParam.BITRATE:
                args += f" --bitrate {self._quality_param_value}"
        if include_seek and self._seek:
            args += f" --seek {self._seek}"
        if include_frames and self._frames:
            args += f" --frames {self._frames}"

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
                 defines: list):

        super().__init__(
            id=Encoder.KVAZAAR,
            user_given_revision=user_given_revision,
            defines = defines,
            git_local_path=Cfg().kvz_git_repo_path,
            git_remote_url=Cfg().kvz_git_repo_ssh_url
        )

        self._exe_src_path: Path = Cfg().kvz_exe_src_path_windows if Cfg().os_name == "Windows"\
                              else Cfg().kvz_exe_src_path_linux

    def build(self) -> None:

        if not super().build_start():
            return

        build_cmd = ()

        if Cfg().os_name == "Windows":

            assert Cfg().kvz_vs_solution_path.exists()

            # Add defines to msbuild arguments.
            # Semicolons cannot be used as literals, so use %3B instead. Read these for reference:
            # https://docs.microsoft.com/en-us/visualstudio/msbuild/how-to-escape-special-characters-in-msbuild
            # https://docs.microsoft.com/en-us/visualstudio/msbuild/msbuild-special-characters
            MSBUILD_SEMICOLON_ESCAPE = "%3B"
            msbuild_args = Cfg().msbuild_args
            msbuild_args.append(f"/p:DefineConstants={MSBUILD_SEMICOLON_ESCAPE.join(self._defines)}")

            # Run VsDevCmd.bat, then msbuild.
            build_cmd = (
                "call", str(Cfg().vs_vsdevcmd_bat_path),
                "&&", "msbuild", str(Cfg().kvz_vs_solution_path)
            ) + tuple(msbuild_args)

        elif Cfg().os_name == "Linux":

            assert Cfg().kvz_configure_script_path.exists()
            assert Cfg().kvz_autogen_script_path.exists()

            # Add defines to configure arguments.
            cflags_str = f"CFLAGS={''.join([f'-D{define} ' for define in self._defines])}"
            kvz_configure_args = Cfg().KVZ_CONFIGURE_ARGS
            kvz_configure_args.append(cflags_str.strip())

            # Run autogen.sh, then configure, then make.
            build_cmd = (
                "cd", str(Cfg().kvz_git_repo_path),
                "&&", str(Cfg().kvz_autogen_script_path),
                "&&", str(Cfg().kvz_configure_script_path),) + tuple(kvz_configure_args) + (
                "&&", "make",
            )

        super().build_finish(build_cmd)

    def clean(self) -> None:

        super().clean_start()

        clean_cmd = ()

        if Cfg().os_name == "Linux":
            clean_cmd = (
                "cd", str(Cfg().kvz_git_repo_path),
                "&&", "make", "clean",
            )

        super().clean_finish(clean_cmd)

    def dummy_run(self,
                  param_set: KvazaarParamSet) -> bool:

        super().dummy_run_start(param_set)

        null_device = "NUL" if Cfg().os_name == "Windows" else "/dev/null"
        RESOLUTION_PLACEHOLDER = "2x2"

        dummy_cmd = (
            str(self._exe_path),
            "-i", null_device,
            "--input-res", RESOLUTION_PLACEHOLDER,
            "-o", null_device,
        ) + param_set.to_cmdline_tuple()

        return super().dummy_run_finish(dummy_cmd, param_set)

    def encode(self,
               encoding_run: EncodingRun) -> None:

        if not super().encode_start(encoding_run):
            return

        encode_cmd = (
            self._exe_path,
            "-i", str(encoding_run.input_sequence.get_filepath()),
            "--input-res", f"{encoding_run.input_sequence.get_width()}x{encoding_run.input_sequence.get_height()}",
            "-o", str(encoding_run.output_file.get_filepath()),
        ) + encoding_run.param_set.to_cmdline_tuple()

        super().encode_finish(encode_cmd, encoding_run)
