#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module defines all Kvazaar-specific functionality.
"""

import core
from core.cfg import *

import hashlib
import logging
import os
import shutil
import subprocess

class TestInstance():
    """
    This class defines all Kvazaar-specific functionality.
    """

    def __init__(self, revision: str, defines: list):
        self.git_repo: core.GitRepo = core.GitRepo(cfg.kvz_git_repo_path)
        self.defines: list = sorted(set(defines)) # ensure no duplicates
        self.define_hash: str = hashlib.md5(str(self.defines).encode()).digest().hex()
        self.short_define_hash: str = self.define_hash[:cfg.short_define_hash_len]
        self.revision: str = revision
        # These have to be evaluated once the existence of the repository is certain.
        self.exe_name: str = ""
        self.exe_dest_path: str = ""
        self.commit_hash: str = ""
        self.short_commit_hash: str = ""
        self.build_log_name: str = ""
        self.build_log_path: str = ""

    def build(self):
        core.console_logger.info(f"Building Kvazaar (revision '{self.revision}')")

        # The build log isn't initialized yet because the filename is based on the git commit hash
        # and that is only found out after the repo has been cloned, so buffer messages
        # until the logger is actually created.
        build_log_buffer: list = []

        # Clone the remote if the local repo doesn't exist yet.
        if not os.path.exists(cfg.kvz_git_repo_path):
            cmd_str, output, exception = self.git_repo.clone(cfg.kvz_git_repo_ssh_url)
            if not exception:
                build_log_buffer.append(cmd_str)
                build_log_buffer.append(output.decode())
            else:
                core.console_logger.error(cmd_str)
                core.console_logger.error(exception.output.decode())
                raise exception

        # These can now be evaluated because the repo exists for certain.
        self.commit_hash = self.git_repo.rev_parse(self.revision)[1].decode().strip()
        self.short_commit_hash = self.commit_hash[:cfg.short_commit_hash_len]
        self.exe_name = f"kvazaar_{self.short_commit_hash}_{self.short_define_hash}{'.exe' if cfg.os_name == 'Windows' else ''}"
        self.exe_dest_path = os.path.join(cfg.binaries_dir_path, self.exe_name)
        self.build_log_name = f"kvazaar_{self.short_commit_hash}_{self.short_define_hash}_build_log.txt"
        self.build_log_path = os.path.join(cfg.binaries_dir_path, self.build_log_name)

        core.console_logger.info(f"Kvazaar revision '{self.revision}' maps to commit hash '{self.commit_hash}'")

        # Don't build unnecessarily.
        if (os.path.exists(self.exe_dest_path)):
            core.console_logger.info(f"Executable '{self.exe_dest_path}' already exists - aborting build")
            return

        if not os.path.exists(cfg.binaries_dir_path):
            build_log_buffer.append(f"Creating directory '{cfg.binaries_dir_path}'")
            os.makedirs(cfg.binaries_dir_path)

        # Set up build logger now that the necessary information is known.
        build_logger: logging.Logger = core.setup_build_logger(self.build_log_path)
        for message in build_log_buffer:
            build_logger.info(message)

        # Checkout to the desired version.
        cmd_str, output, exception = self.git_repo.checkout(self.commit_hash)
        if not exception:
            build_logger.info(cmd_str)
            build_logger.info(output.decode())
        else:
            build_logger.info(cmd_str)
            build_logger.info(exception.output.decode())
            core.console_logger.error(exception.output.decode())
            raise exception

        if cfg.os_name == "Windows":
            assert os.path.exists(cfg.kvz_vs_solution_path)

            # Add defines to msbuild arguments.
            # Semicolons cannot be used as literals, so use %3B instead. Read these for reference:
            # https://docs.microsoft.com/en-us/visualstudio/msbuild/how-to-escape-special-characters-in-msbuild
            # https://docs.microsoft.com/en-us/visualstudio/msbuild/msbuild-special-characters
            MSBUILD_SEMICOLON_ESCAPE = "%3B"
            msbuild_args = cfg.KVZ_MSBUILD_ARGS
            msbuild_args.append(f"/p:DefineConstants={MSBUILD_SEMICOLON_ESCAPE.join(self.defines)}")

            # Run VsDevCmd.bat, then msbuild. Return 0 on success, 1 on failure.
            # KVZ_MSBUILD_ARGS has to be a list/tuple so the syntax below is pretty stupid.
            # TODO: Find a less stupid and more readable way to do this.
            compile_cmd: tuple = (
                "(", "call", cfg.vs_vsdevcmd_bat_path,
                     "&&", "msbuild", cfg.kvz_vs_solution_path) + tuple(msbuild_args) + (
                     "&&", "exit", "0",
                ")", "||", "exit", "1",
            )
            build_logger.info(subprocess.list2cmdline(compile_cmd))
            try:
                output: bytes = subprocess.check_output(compile_cmd, shell=True)
                # "cp1252" is the encoding the Windows shell uses.
                build_logger.info(output.decode(encoding="cp1252"))
            except subprocess.CalledProcessError as exception:
                core.console_logger.error(exception.output.decode())
                build_logger.error(exception.output.decode())
                raise

            # Copy the executable to its destination.
            assert os.path.exists(cfg.kvz_exe_src_path_windows)
            try:
                build_logger.info(f"Copying file '{cfg.kvz_exe_src_path_windows}' to '{self.exe_dest_path}'")
                shutil.copy(cfg.kvz_exe_src_path_windows, self.exe_dest_path)

            except FileNotFoundError as exception:
                core.console_logger.error(str(exception))
                build_logger.error(str(exception))
                raise

        elif cfg.os_name == "Linux":
            # Add defines to configure arguments.
            cflags_str = f"CFLAGS={''.join([f'-D{define} ' for define in self.defines])}"
            kvz_configure_args = cfg.KVZ_CONFIGURE_ARGS
            kvz_configure_args.append(cflags_str.strip())

            # Run autogen.sh, then configure, then make. Return 0 on success, 1 on failure.
            # TODO: Find a better way to do this.
            compile_cmd = (
                "(", "cd", cfg.kvz_git_repo_path,
                     "&&", cfg.kvz_autogen_script_path,
                     "&&", cfg.kvz_configure_script_path,) + tuple(kvz_configure_args) + (
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
                core.console_logger.error(exception.output.decode())
                build_logger.error(exception.output.decode())
                raise

            # Copy the executable to its destination.
            assert os.path.exists(cfg.kvz_exe_src_path_linux)
            build_logger.info(f"Copying file '{cfg.kvz_exe_src_path_linux}' to '{self.exe_dest_path}'")
            try:
                shutil.copy(cfg.kvz_exe_src_path_linux, self.exe_dest_path)
            except FileNotFoundError as exception:
                core.console_logger.error(str(exception))
                build_logger.error(str(exception))
                raise

            # Clean the build so that Kvazaar binaries of different versions
            # can be built without problems if desired. This is not logged.
            # Go to Kvazaar git repo, then run make clean. Return 0 on success, 1 on failure.
            clean_cmd = (
                "(", "cd", cfg.kvz_git_repo_path,
                     "&&", "make", "clean",
                     "&&", "exit", "0",
                ")", "||", "exit", "1",
            )
            try:
                subprocess.check_output(subprocess.list2cmdline(clean_cmd), shell=True)
            except subprocess.CalledProcessError as exception:
                core.console_logger.error(exception.output.decode())
                raise

        # Only Linux and Windows are supported.
        else:
            exception = RuntimeError(f"Unsupported OS '{cfg.os_name}'. Expected one of ['Linux', 'Windows']")
            core.console_logger.error(str(exception))
            raise exception
