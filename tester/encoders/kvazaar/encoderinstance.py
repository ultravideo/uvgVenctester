#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module defines all Kvazaar-specific functionality.
"""

from core.cfg import *
from core.git import *
from core.log import *

from .encodingparamset import *

import test
from encoders import *

import hashlib
import logging
import os
import shutil
import subprocess

class EncoderInstance(test.EncoderInstanceBase):
    """
    This class defines all Kvazaar-specific functionality.
    """

    def __init__(self, revision: str, defines: list):
        super().__init__()
        self.git_repo: GitRepo = GitRepo(Cfg().kvz_git_repo_path)
        self.defines: list = sorted(set(defines)) # ensure no duplicates
        self.define_hash: str = hashlib.md5(str(self.defines).encode()).digest().hex()
        self.short_define_hash: str = self.define_hash[:Cfg().short_define_hash_len]
        self.revision: str = revision

        self.exe_name: str = ""
        self.exe_dest_path: str = ""
        self.commit_hash: str = ""
        self.short_commit_hash: str = ""
        self.build_log_name: str = ""
        self.build_log_path: str = ""
        self.prepare_sources()

        console_logger.debug(f"Initialized Kvazaar instance with"
                             f" revision='{self.revision}',"
                             f" commit_hash='{self.commit_hash}',"
                             f" defines={self.defines}")

    def __eq__(self, other):
        return self.get_encoder_name() == other.get_encoder_name()\
                and self.commit_hash == other.commit_hash\
                and self.define_hash == other.define_hash

    def get_exe_path(self):
        return self.exe_dest_path

    def get_encoder_id(self) -> test.EncoderId:
        return test.EncoderId.KVAZAAR

    def get_encoder_name(self) -> str:
        return "Kvazaar"

    def get_defines(self) -> list:
        return self.defines

    def get_user_revision(self) -> str:
        return self.revision

    def get_revision(self) -> str:
        return self.commit_hash

    def prepare_sources(self):
        """Clones the Kvazaar repository from remote if it doesn't exist. Checks that the specified
        revision exists. Sets attributes that depend on the commit hash."""
        console_logger.info(f"Preparing Kvazaar (revision '{self.revision}') sources")

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
            console_logger.info(f"Repository '{Cfg().kvz_git_repo_path}' already exists")

        # These can now be evaluated because the repo exists for certain.
        cmd, output, exception = self.git_repo.rev_parse(self.revision)
        if not exception:
            self.commit_hash = output.decode().strip()
        else:
            console_logger.error(f"Invalid Kvazaar revision '{self.revision}'")
            raise exception
        self.short_commit_hash = self.commit_hash[:Cfg().short_commit_hash_len]
        self.exe_name = f"kvazaar_{self.short_commit_hash}_{self.short_define_hash}{'.exe' if Cfg().os_name == 'Windows' else ''}"
        self.exe_dest_path = os.path.join(Cfg().binaries_dir_path, self.exe_name)
        self.build_log_name = f"kvazaar_{self.short_commit_hash}_{self.short_define_hash}_build_log.txt"
        self.build_log_path = os.path.join(Cfg().binaries_dir_path, self.build_log_name)

        console_logger.info(f"Kvazaar revision '{self.revision}' maps to commit hash '{self.commit_hash}'")

    def build(self):
        console_logger.info(f"Building Kvazaar (revision '{self.revision}')")

        # Don't build unnecessarily.
        if (os.path.exists(self.exe_dest_path)):
            console_logger.info(f"Executable '{self.exe_dest_path}' already exists - aborting build")
            return

        assert os.path.exists(Cfg().binaries_dir_path)

        # Set up build logger.
        build_logger: logging.Logger = setup_build_logger(self.build_log_path)

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
            compile_cmd: tuple = (
                "(", "call", Cfg().vs_vsdevcmd_bat_path,
                     "&&", "msbuild", Cfg().kvz_vs_solution_path) + tuple(msbuild_args) + (
                     "&&", "exit", "0",
                ")", "||", "exit", "1",
            )
            build_logger.info(subprocess.list2cmdline(compile_cmd))
            try:
                output: bytes = subprocess.check_output(compile_cmd, shell=True)
                # "cp1252" is the encoding the Windows shell uses.
                build_logger.info(output.decode(encoding="cp1252"))
            except subprocess.CalledProcessError as exception:
                console_logger.error(exception.output.decode())
                build_logger.error(exception.output.decode())
                raise

            # Copy the executable to its destination.
            assert os.path.exists(Cfg().kvz_exe_src_path_windows)
            try:
                build_logger.info(f"Copying file '{Cfg().kvz_exe_src_path_windows}' to '{self.exe_dest_path}'")
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
                output: bytes = subprocess.check_output(subprocess.list2cmdline(compile_cmd),
                                                        shell=True,
                                                        stderr=subprocess.STDOUT)
                build_logger.info(output.decode())
            except subprocess.CalledProcessError as exception:
                console_logger.error(exception.output.decode())
                build_logger.error(exception.output.decode())
                raise

            # Copy the executable to its destination.
            assert os.path.exists(Cfg().kvz_exe_src_path_linux)
            build_logger.info(f"Copying file '{Cfg().kvz_exe_src_path_linux}' to '{self.exe_dest_path}'")
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
            exception = RuntimeError(f"Unsupported OS '{Cfg().os_name}'. Expected one of ['Linux', 'Windows']")
            console_logger.error(str(exception))
            raise exception

    def dummy_run(self, param_set: EncodingParamSet) -> bool:
        console_logger.debug(
            f"Kvazaar: Executing dummy run to validate command line arguments")

        dummy_cmd: tuple = ()
        if Cfg().os_name == "Windows":
            dummy_cmd = (self.exe_dest_path, "-i", "NUL", "--input-res", "2x2", "-o", "NUL",)\
                        + param_set.to_cmdline_tuple()
        elif Cfg().os_name == "Linux":
            dummy_cmd = (self.exe_dest_path, "-i", "/dev/null", "--input-res", "2x2", "-o", "/dev/null",)\
                        + param_set.to_cmdline_tuple()

        try:
            subprocess.check_output(dummy_cmd, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as exception:
            console_logger.error(f"Kvazaar: Invalid arguments")
            console_logger.error(exception.output.decode().strip())
            return False
        return True

    def encode(self,
               input: test.VideoSequence,
               param_set: EncodingParamSet,):
        console_logger.debug(f"Kvazaar: Encoding file '{input.input_filepath}'")

        qp_name = param_set.get_quality_param_name()
        qp_value = param_set.get_quality_param_value()
        base_filename = f"{input.get_input_filename(include_extension=False)}"
        ext_filename = f"{base_filename}_{qp_name.lower()}{qp_value}.hevc"
        output_filepath = os.path.join(
            Cfg().encoding_output_dir_path,
            self.exe_name.strip(".exe"),
            param_set.to_cmdline_str(include_quality_param=False),
            ext_filename)

        if not os.path.exists(os.path.dirname(output_filepath)):
            os.makedirs(os.path.dirname(output_filepath))

        encode_cmd: tuple = (
            self.exe_dest_path,
            "-i", input.get_input_filepath(),
            "--input-res", f"{input.get_width()}x{input.get_width()}",
            "-o", output_filepath)\
            + param_set.to_cmdline_tuple()

        try:
            subprocess.check_output(encode_cmd, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as exception:
            console_logger.error(f"Kvazaar: Failed to encode file '{input}'")
            console_logger.error(exception.output.decode().strip())
            raise
