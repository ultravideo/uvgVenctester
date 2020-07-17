#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""This module defines all Kvazaar-specific functionality."""

from tester.core.git import *
from tester.core.cfg import *
from .base import *
import tester.core.videosequence

import hashlib
import os
import shutil
import subprocess


class KvazaarParamSet(ParamSetBase):
    """Represents the parameters passed to Kvazaar when encoding."""

    # These have to be the first two arguments on the command line.
    POSITIONAL_ARGS = ("--preset", "--gop")

    def __init__(self,
                 quality_param_type: QualityParamType,
                 quality_param_value: int,
                 cl_args: str):
        super().__init__(quality_param_type, quality_param_value, cl_args)

        if not self.quality_param_type in (QualityParamType.QP, QualityParamType.BITRATE):
            console_logger.error(f"Kvazaar: Invalid quality_param_type '{str(self.quality_param_type)}'")
            raise RuntimeError

        # Check integrity. TODO: Refactor to state intent.
        self.to_cmdline_str()

        hash = hashlib.md5()
        hash.update(str(quality_param_type).encode())
        hash.update(str(quality_param_value).encode())
        hash.update(cl_args.encode())
        self.hash = int(hash.hexdigest(), 16)

    def __eq__(self, other: ParamSetBase):
        return self.quality_param_type == other.quality_param_type\
               and self.quality_param_value == other.quality_param_value\
               and self.cl_args == other.cl_args

    def __hash__(self):
        return self.hash

    def to_cmdline_str(self, include_quality_param: bool = True) -> str:
        """Reorders command line arguments such that --preset is first, --gop second and all the rest last.
        Also checks that the args are syntactically valid. Returns the arguments as a string."""

        def is_long_option(candidate: str):
            return candidate.startswith("--")

        def is_short_option(candidate: str):
            return not is_long_option(candidate) and candidate.startswith("-")

        def is_option(candidate: str):
            return is_long_option(candidate) or is_short_option(candidate)

        def is_value(candidate: str):
            return not is_option(candidate)

        cl_args = self.cl_args

        if include_quality_param:
            if self.quality_param_type == QualityParamType.QP:
                cl_args += f" --qp {self.quality_param_value}"
            elif self.quality_param_type == QualityParamType.BITRATE:
                cl_args += f" --bitrate {self.quality_param_value}"

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
                raise RuntimeError(f"Kvazaar: Duplicate option {option_name}")

            option_values[option_name] = option_value

        # Check that no option is specified as both no-<option> and <option>.
        for option_name in option_values.keys():
            option_name = option_name.strip("--")
            if f"--no-{option_name}" in option_values.keys():
                raise RuntimeError(f"Kvazaar: Conflicting options '--{option_name}' and "
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

        return " ".join(reordered_cl_args)


class Kvazaar(EncoderBase):
    """Represents an instance of Kvazaar."""

    def __init__(self, user_given_revision: str, defines: list):
        super().__init__()
        self.git_repo: GitRepository = GitRepository(Cfg().kvz_git_repo_path)
        self.defines: list = sorted(set(defines)) # ensure no duplicates
        self.define_hash: str = hashlib.md5(str(self.defines).encode()).digest().hex()
        self.define_hash_short: str = self.define_hash[:Cfg().short_define_hash_len]
        self.user_given_revision: str = user_given_revision

        self.exe_name: str = ""
        self.exe_dest_path: str = ""
        self.commit_hash: str = ""
        self.commit_hash_short: str = ""
        self.build_log_name: str = ""
        self.build_log_path: str = ""
        # Initializes the attributes above.
        self.prepare_sources()

        console_logger.debug(f"Kvazaar: Initialized object:")
        for attribute_name in sorted(self.__dict__):
            console_logger.debug(f"Kvazaar: {attribute_name} = '{getattr(self, attribute_name)}'")

    def __eq__(self, other):
        return self.get_encoder_name() == other.get_encoder_name()\
                and self.commit_hash == other.commit_hash\
                and self.define_hash == other.define_hash

    def __hash__(self):
        return hashlib.md5(self.get_encoder_name())\
               + hashlib.md5(self.commit_hash)\
               + hashlib.md5(self.define_hash)

    def get_exe_path(self) -> str:
        return self.exe_dest_path

    def get_encoder_id(self) -> EncoderId:
        return EncoderId.KVAZAAR

    def get_encoder_name(self) -> str:
        return "Kvazaar"

    def get_defines(self) -> list:
        return self.defines

    def get_user_given_revision(self) -> str:
        return self.user_given_revision

    def get_revision(self) -> str:
        return self.commit_hash

    def get_short_revision(self) -> str:
        return self.commit_hash_short

    def get_output_base_dir(self) -> str:
        return os.path.join(
            Cfg().encoding_output_dir_path,
            self.exe_name.strip(".exe"),
        )

    def get_output_subdir(self, param_set: KvazaarParamSet) -> str:
        return os.path.join(
            self.get_output_base_dir(),
            param_set.to_cmdline_str(include_quality_param=False),
        )

    def prepare_sources(self):
        """Clones the Kvazaar repository from remote if it doesn't exist. Checks that the specified
        revision exists. Sets attributes that depend on the commit hash."""
        console_logger.info(f"Kvazaar: Preparing sources")
        console_logger.info(f"Kvazaar: Repository: '{self.git_repo.local_repo_path}'")
        console_logger.info(f"Kvazaar: Revision: '{self.user_given_revision}'")

        # Clone the remote if the local repo doesn't exist yet.
        if not os.path.exists(Cfg().kvz_git_repo_path):
            cmd_str, output, exception = self.git_repo.clone(Cfg().kvz_git_repo_ssh_url)
            if not exception:
                pass
            else:
                console_logger.error(cmd_str)
                console_logger.error(exception.output.decode())
                raise exception
        else:
            console_logger.info(f"Kvazaar: Repository '{Cfg().kvz_git_repo_path}' already exists")

        cmd, output, exception = self.git_repo.rev_parse(self.user_given_revision)
        if not exception:
            self.commit_hash = output.decode().strip()
        else:
            console_logger.error(f"Kvazaar: Invalid revision '{self.user_given_revision}'")
            raise exception
        # These can now be evaluated because the repo exists for certain.
        self.commit_hash_short = self.commit_hash[:Cfg().short_commit_hash_len]
        self.exe_name = f"kvazaar_{self.commit_hash_short}_{self.define_hash_short}"\
                        f"{'.exe' if Cfg().os_name == 'Windows' else ''}"
        self.exe_dest_path = os.path.join(Cfg().binaries_dir_path, self.exe_name)
        self.build_log_name = f"kvazaar_{self.commit_hash_short}_{self.define_hash_short}_build_log.txt"
        self.build_log_path = os.path.join(Cfg().binaries_dir_path, self.build_log_name)

        console_logger.info(f"Kvazaar: Revision '{self.user_given_revision}' maps to commit hash "
                            f"'{self.commit_hash}'")

    def build(self):
        console_logger.info(f"Kvazaar: Building executable '{self.exe_name}'")

        # Don't build unnecessarily.
        if (os.path.exists(self.exe_dest_path)):
            console_logger.info(f"Kvazaar: Executable '{self.exe_name}' already exists")
            return

        assert os.path.exists(Cfg().binaries_dir_path)

        # Set up build logger.
        build_logger = setup_build_logger(self.build_log_path)
        console_logger.info(f"Kvazaar: Log: '{self.build_log_name}'")

        # Checkout to the desired version.
        cmd_str, output, exception = self.git_repo.checkout(self.commit_hash)
        if not exception:
            build_logger.info(cmd_str)
            build_logger.info(output.decode())
        else:
            build_logger.info(cmd_str)
            build_logger.info(exception.output.decode())
            console_logger.error(exception.output.decode())
            raise exception

        if Cfg().os_name == "Windows":
            assert os.path.exists(Cfg().kvz_vs_solution_path)

            # Add defines to msbuild arguments.
            # Semicolons cannot be used as literals, so use %3B instead. Read these for reference:
            # https://docs.microsoft.com/en-us/visualstudio/msbuild/how-to-escape-special-characters-in-msbuild
            # https://docs.microsoft.com/en-us/visualstudio/msbuild/msbuild-special-characters
            MSBUILD_SEMICOLON_ESCAPE = "%3B"
            msbuild_args = Cfg().KVZ_MSBUILD_ARGS
            msbuild_args.append(f"/p:DefineConstants={MSBUILD_SEMICOLON_ESCAPE.join(self.defines)}")

            # Run VsDevCmd.bat, then msbuild. Return 0 on success, 1 on failure.
            # KVZ_MSBUILD_ARGS has to be a list/tuple so the syntax below is pretty stupid.
            # TODO: Find a less stupid and more readable way to do this.
            compile_cmd = (
                "(", "call", Cfg().vs_vsdevcmd_bat_path,
                     "&&", "msbuild", Cfg().kvz_vs_solution_path) + tuple(msbuild_args) + (
                     "&&", "exit", "0",
                ")", "||", "exit", "1",
            )
            build_logger.info(subprocess.list2cmdline(compile_cmd))
            try:
                output = subprocess.check_output(compile_cmd, shell=True)
                # "cp1252" is the encoding the Windows shell uses.
                build_logger.info(output.decode(encoding="cp1252"))
            except subprocess.CalledProcessError as exception:
                console_logger.error(exception.output.decode())
                build_logger.error(exception.output.decode())
                raise

            # Copy the executable to its destination.
            assert os.path.exists(Cfg().kvz_exe_src_path_windows)
            try:
                build_logger.debug(f"Kvazaar: Copying file '{Cfg().kvz_exe_src_path_windows}' "
                                   f"to '{self.exe_dest_path}'")
                shutil.copy(Cfg().kvz_exe_src_path_windows, self.exe_dest_path)

            except FileNotFoundError as exception:
                console_logger.error(str(exception))
                build_logger.error(str(exception))
                raise

        elif Cfg().os_name == "Linux":
            # Add defines to configure arguments.
            cflags_str = f"CFLAGS={''.join([f'-D{define} ' for define in self.defines])}"
            kvz_configure_args = Cfg().KVZ_CONFIGURE_ARGS
            kvz_configure_args.append(cflags_str.strip())

            # Run autogen.sh, then configure, then make. Return 0 on success, 1 on failure.
            # TODO: Find a better way to do this.
            compile_cmd = (
                "(", "cd", Cfg().kvz_git_repo_path,
                     "&&", Cfg().kvz_autogen_script_path,
                     "&&", Cfg().kvz_configure_script_path,) + tuple(kvz_configure_args) + (
                     "&&", "make",
                     "&&", "exit", "0",
                ")", "||", "exit", "1",
            )

            build_logger.info(subprocess.list2cmdline(compile_cmd))
            try:
                # The shell command needs to be converted into a string.
                output = subprocess.check_output(
                    subprocess.list2cmdline(compile_cmd),
                    shell=True,
                    stderr=subprocess.STDOUT
                )
                build_logger.info(output.decode())
            except subprocess.CalledProcessError as exception:
                console_logger.error(exception.output.decode())
                build_logger.error(exception.output.decode())
                raise

            # Copy the executable to its destination.
            assert os.path.exists(Cfg().kvz_exe_src_path_linux)
            build_logger.debug(f"Kvazaar: Copying file '{Cfg().kvz_exe_src_path_linux}' "
                               f"to '{self.exe_dest_path}'")
            try:
                shutil.copy(Cfg().kvz_exe_src_path_linux, self.exe_dest_path)
            except FileNotFoundError as exception:
                console_logger.error(str(exception))
                build_logger.error(str(exception))
                raise

            # Clean the build so that Kvazaar binaries of different versions
            # can be built without problems if desired. This is not logged.
            # Go to Kvazaar git repo, then run make clean. Return 0 on success, 1 on failure.
            clean_cmd = (
                "(", "cd", Cfg().kvz_git_repo_path,
                     "&&", "make", "clean",
                     "&&", "exit", "0",
                ")", "||", "exit", "1",
            )
            try:
                subprocess.check_output(subprocess.list2cmdline(clean_cmd), shell=True)
            except subprocess.CalledProcessError as exception:
                console_logger.error(exception.output.decode())
                raise

        # Only Linux and Windows are supported.
        else:
            exception = RuntimeError(f"Kvazaar: Unsupported OS '{Cfg().os_name}'. "
                                     f"Expected one of ['Linux', 'Windows']")
            console_logger.error(str(exception))
            raise exception

    def dummy_run(self, param_set: KvazaarParamSet) -> bool:
        console_logger.debug(f"Kvazaar: Dummy run with arguments '{param_set.to_cmdline_str()}'")

        dummy_cmd = ()

        if Cfg().os_name == "Windows":
            dummy_cmd = (
                self.exe_dest_path,
                "-i", "NUL",
                "--input-res", "2x2",
                "-o", "NUL",
            ) + param_set.to_cmdline_tuple()

        elif Cfg().os_name == "Linux":
            dummy_cmd = (
                self.exe_dest_path,
                "-i", "/dev/null",
                "--input-res", "2x2",
                "-o", "/dev/null",
            ) + param_set.to_cmdline_tuple()

        try:
            subprocess.check_output(dummy_cmd, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as exception:
            console_logger.error(f"Kvazaar: Invalid arguments: "
                                 f"'{param_set.to_cmdline_str()}'")
            console_logger.error(exception.output.decode().strip())
            return False
        return True

    def encode(self,
               input: tester.core.videosequence.VideoSequence,
               param_set: KvazaarParamSet):
        console_logger.debug(f"Kvazaar: Encoding file '{input.get_input_filename()}'")

        qp_name = param_set.get_quality_param_name()
        qp_value = param_set.get_quality_param_value()
        base_filename = f"{input.get_input_filename(include_extension=False)}"
        output_filename = f"{base_filename}_{qp_name.lower()}{qp_value}.hevc"
        output_filepath = os.path.join(self.get_output_subdir(param_set), output_filename)
        console_logger.debug(f"Kvazaar: Output: '{output_filename}'")

        console_logger.debug(f"Kvazaar: Arguments: '{param_set.to_cmdline_str()}'")

        encoding_log_filepath = output_filepath.strip(".hevc") + "_encoding_log.txt"
        encoding_log_filename = os.path.basename(encoding_log_filepath)
        console_logger.debug(f"Kvazaar: Log: '{encoding_log_filename}'")

        if not os.path.exists(os.path.dirname(output_filepath)):
            os.makedirs(os.path.dirname(output_filepath))

        encode_cmd = (
            self.exe_dest_path,
            "-i", input.get_input_filepath(),
            "--input-res", f"{input.get_width()}x{input.get_height()}",
            "-o", output_filepath
        ) + param_set.to_cmdline_tuple()

        try:
            output = subprocess.check_output(encode_cmd, stderr=subprocess.STDOUT)
            with open(encoding_log_filepath, "w") as encoding_log:
                encoding_log.write(output.decode())
        except subprocess.CalledProcessError as exception:
            console_logger.error(f"Kvazaar: Encoding failed (input: '{input.input_filepath()}', "
                                 f"output: '{output_filepath}')")
            console_logger.error(exception.output.decode().strip())
            raise
