"""This module defines all functionality specific to Kvazaar."""

from .base import *
import tester.core.video


class KvazaarParamSet(ParamSetBase):
    """Represents the command line parameters passed to Kvazaar when encoding."""

    # These have to be the first two arguments on the command line.
    POSITIONAL_ARGS = ("--preset", "--gop")

    def __init__(self,
                 quality_param_type: QualityParamType,
                 quality_param_value: int,
                 seek: int,
                 frames: int,
                 cl_args: str):

        if seek:
            cl_args += f" --seek {seek}"
        if frames:
            cl_args += f" --frames {frames}"

        super().__init__(
            quality_param_type,
            quality_param_value,
            seek,
            frames,
            cl_args
        )

        # This checks the integrity of the parameters.
        self.to_cmdline_tuple()

    def to_cmdline_tuple(self,
                         include_quality_param: bool = True) -> tuple:
        """Reorders command line arguments such that --preset is first,
        --gop second and all the rest last. Also checks that the args are syntactically valid.
        Returns the arguments as a string."""

        def is_long_option(candidate: str):
            return candidate.startswith("--")

        def is_short_option(candidate: str):
            return not is_long_option(candidate) and candidate.startswith("-")

        def is_option(candidate: str):
            return is_long_option(candidate) or is_short_option(candidate)

        def is_value(candidate: str):
            return not is_option(candidate)

        cl_args = self._cl_args

        if include_quality_param:
            if self._quality_param_type == QualityParamType.QP:
                cl_args += f" --qp {self._quality_param_value}"
            elif self._quality_param_type == QualityParamType.BITRATE:
                cl_args += f" --bitrate {self._quality_param_value}"

        split_args: list = []

        # Split the arguments such that each option and its value, if any, are separated.
        for item in cl_args.split():
            if is_short_option(item):
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

        # Put the options and their values into this dict. Value None indicates that the option
        # is a boolean with no explicit value.
        option_values = {}
        i = 0
        i_max = len(split_args)
        while i < i_max:
            option_name = split_args[i]
            if is_option(option_name) and i + 1 < i_max and is_value(split_args[i + 1]):
                # Has an explicit value.
                option_value = split_args[i + 1]
                i += 2
            else:
                # Has an implicit value (boolean).
                option_value = None
                i += 1

            if option_name in option_values:
                raise RuntimeError(f"KvazaarParamSet: Duplicate option {option_name}")

            option_values[option_name] = option_value

        # Check that no option is specified as both no-<option> and <option>.
        for option_name in option_values.keys():
            option_name = option_name.strip("--")
            if f"--no-{option_name}" in option_values.keys():
                raise RuntimeError(f"KvazaarParamSet: Conflicting options '--{option_name}' and "
                                   f"'--no-{option_name}'")

        # Reorder the options. --preset and --gop must be the first, in this order. The order
        # of the rest doesn't matter.

        # Handle --preset and --gop.
        reordered_cl_args: list = []
        for option_name in self.POSITIONAL_ARGS:
            if option_name in option_values:
                option_value = option_values[option_name]
                reordered_cl_args.append(option_name)
                if option_value:
                    reordered_cl_args.append(option_value)
                del option_values[option_name]

        # Handle option flags with implicit boolean values (for example --no-wpp).
        for option_name in sorted(option_values.keys()):
            option_value = option_values[option_name]
            if option_value is None:
                reordered_cl_args.append(option_name)
                del option_values[option_name]

        # Handle long options with explicit values (for example --frames 256)
        for option_name in sorted(option_values.keys()):
            option_value = option_values[option_name]
            if is_long_option(option_name):
                reordered_cl_args.append(option_name)
                reordered_cl_args.append(option_value)

        # Handle short options with explicit values (for example -n 256).
        for option_name in sorted(option_values.keys()):
            option_value = option_values[option_name]
            if is_short_option(option_name):
                reordered_cl_args.append(option_name)
                reordered_cl_args.append(option_value)

        return tuple(reordered_cl_args)


class Kvazaar(EncoderBase):
    """Represents a Kvazaar executable."""

    def __init__(self,
                 user_given_revision: str,
                 defines: list):

        super().__init__(
            id=EncoderId.KVAZAAR,
            user_given_revision=user_given_revision,
            defines = defines,
            git_repo_path=Cfg().kvz_git_repo_path,
            git_repo_ssh_url=Cfg().kvz_git_repo_ssh_url
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
            msbuild_args = Cfg().KVZ_MSBUILD_ARGS
            msbuild_args.append(f"/p:DefineConstants={MSBUILD_SEMICOLON_ESCAPE.join(self._defines)}")

            # Run VsDevCmd.bat, then msbuild.
            # KVZ_MSBUILD_ARGS has to be a list/tuple so the syntax below is pretty stupid.
            build_cmd = (
                "call", Cfg().vs_vsdevcmd_bat_path,
                "&&", "msbuild", Cfg().kvz_vs_solution_path
            ) + tuple(msbuild_args)

        elif Cfg().os_name == "Linux":

            assert Cfg().kvz_configure_script_path.exists()
            assert Cfg().kvz_autogen_script_path.exists()

            # Add defines to configure arguments.
            cflags_str = f"CFLAGS={''.join([f'-D{define} ' for define in self._defines])}"
            kvz_configure_args = Cfg().KVZ_CONFIGURE_ARGS
            kvz_configure_args.append(cflags_str.strip())

            # Run autogen.sh, then configure, then make. Return 0 on success, 1 on failure.
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

        dummy_cmd = ()

        if Cfg().os_name == "Windows":
            dummy_cmd = (
                str(self._exe_path),
                "-i", "NUL",
                "--input-res", "2x2",
                "-o", "NUL",
            ) + param_set.to_cmdline_tuple()

        elif Cfg().os_name == "Linux":
            dummy_cmd = (
                self._exe_path,
                "-i", "/dev/null",
                "--input-res", "2x2",
                "-o", "/dev/null",
            ) + param_set.to_cmdline_tuple()

        return super().dummy_run_finish(dummy_cmd, param_set)

    def encode(self,
               input_sequence: tester.core.video.RawVideoSequence,
               param_set: KvazaarParamSet) -> None:

        output_filepath = super().encode_start(input_sequence, param_set)
        if not output_filepath:
            return

        encode_cmd = (
                         self._exe_path,
            "-i", input_sequence.get_filepath(),
            "--input-res", f"{input_sequence.get_width()}x{input_sequence.get_height()}",
            "-o", str(output_filepath),
        ) + param_set.to_cmdline_tuple()

        super().encode_finish(encode_cmd, input_sequence, param_set)
