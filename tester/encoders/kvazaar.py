#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module defines all Kvazaar-specific functionality.
"""

import core
import hashlib
import logging
import os
import platform
import shutil
import subprocess

OS_NAME: str = platform.system()

TESTER_ROOT_PATH: str = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))
PROJECT_ROOT_PATH: str = os.path.dirname(os.path.realpath(os.path.join(str(TESTER_ROOT_PATH), "..")))
BINARIES_DIR_NAME: str = "_binaries"
BINARIES_DIR_PATH: str = os.path.join(TESTER_ROOT_PATH, BINARIES_DIR_NAME)
REPORTS_DIR_NAME: str = "_reports"
REPORTS_DIR_PATH: str = os.path.join(TESTER_ROOT_PATH, REPORTS_DIR_NAME)
SOURCES_DIR_NAME: str = "_sources"
SOURCES_DIR_PATH: str = os.path.join(TESTER_ROOT_PATH, SOURCES_DIR_NAME)

VS_VSDEVCMD_BAT_PATH: str = r"C:\Program Files (x86)\Microsoft Visual Studio\2019\Enterprise\Common7\Tools\VsDevCmd.bat"

KVZ_GIT_REPO_PATH: str = os.path.join(SOURCES_DIR_PATH, "kvazaar")
KVZ_GIT_DIR_PATH: str = os.path.join(KVZ_GIT_REPO_PATH, ".git")
KVZ_COMPILE_SCRIPT_LINUX_PATH: str = os.path.join(TESTER_ROOT_PATH, "encoders", "kvazaar_compile_linux.sh")
KVZ_COMPILE_SCRIPT_WINDOWS_PATH: str = os.path.join(TESTER_ROOT_PATH, "encoders", "kvazaar_compile_windows.ps1")
KVZ_GITHUB_REPO_SSH_URL: str = "git@github.com:ultravideo/kvazaar.git"
KVZ_GITLAB_REPO_SSH_URL: str = "git@gitlab.tut.fi:TIE/ultravideo/kvazaar.git"
KVZ_EXE_SRC_NAME: str = f"kvazaar{'.exe' if OS_NAME == 'Windows' else ''}"
KVZ_EXE_SRC_PATH_WINDOWS: str = os.path.join(KVZ_GIT_REPO_PATH, "bin", "x64-Release", KVZ_EXE_SRC_NAME)
KVZ_EXE_SRC_PATH_LINUX: str = os.path.join(KVZ_GIT_REPO_PATH, "src", "kvazaar")
KVZ_MSBUILD_CONFIGURATION: str = "Release"
KVZ_MSBUILD_PLATFORM: str = "x64"
KVZ_MSBUILD_PLATFORMTOOLSET: str = "v142"
KVZ_MSBUILD_WINDOWSTARGETPLATFORMVERSION: str = "10.0"
KVZ_MSBUILD_ARGS: list = [f"/p:Configuration={KVZ_MSBUILD_CONFIGURATION}",
                          f"/p:Platform={KVZ_MSBUILD_PLATFORM}",
                          f"/p:PlatformToolset={KVZ_MSBUILD_PLATFORMTOOLSET}",
                          f"/p:WindowsTargetPlatformVersion={KVZ_MSBUILD_WINDOWSTARGETPLATFORMVERSION}"]
KVZ_VS_SOLUTION_NAME: str = "kvazaar_VS2015.sln"
KVZ_VS_SOLUTION_PATH: str = os.path.join(KVZ_GIT_REPO_PATH, "build", KVZ_VS_SOLUTION_NAME)
KVZ_AUTOGEN_SCRIPT_PATH: str = os.path.join(KVZ_GIT_REPO_PATH, "autogen.sh")
KVZ_CONFIGURE_SCRIPT_PATH: str = os.path.join(KVZ_GIT_REPO_PATH, "configure")
KVZ_CONFIGURE_ARGS: list = ["--disable-shared", "--enable-static",]

FILENAME_COMMIT_HASH_LEN: int = 16
FILENAME_DEFINE_HASH_LEN: int = 8

class TestInstance():
    """
    This class defines all Kvazaar-specific functionality.
    """

    def __init__(self, revision: str, defines: list):
        self.git_repo: core.GitRepo = core.GitRepo(KVZ_GIT_REPO_PATH)
        self.defines: list = sorted(set(defines)) # ensure no duplicates
        self.define_hash: str = hashlib.md5(str(self.defines).encode()).digest().hex()[:FILENAME_DEFINE_HASH_LEN]
        self.revision: str = revision
        # These have to be evaluated once the existence of the repository is certain.
        self.exe_name: str = ""
        self.exe_dest_path: str = ""
        self.commit_hash: str = ""
        self.build_log_name: str = ""
        self.build_log_path: str = ""

    def build(self):
        core.console_logger.info(f"Building Kvazaar (revision '{self.revision}')")

        # The build log isn't initialized yet because the filename is based on the git commit hash
        # and that is only found out after the repo has been cloned.
        build_log_buffer: list = []

        # Clone the remote if the local repo doesn't exist yet.
        if not os.path.exists(KVZ_GIT_REPO_PATH):
            cmd_str, output, exception = self.git_repo.clone(KVZ_GITLAB_REPO_SSH_URL)
            if not exception:
                build_log_buffer.append(cmd_str)
                build_log_buffer.append(output.decode())
            else:
                core.console_logger.error(cmd_str)
                core.console_logger.error(exception.output.decode())
                raise exception

        self.commit_hash = self.git_repo.rev_parse(self.revision)[1].decode().strip()
        self.exe_name = f"kvazaar_{self.commit_hash[:FILENAME_COMMIT_HASH_LEN]}_{self.define_hash}{'.exe' if OS_NAME == 'Windows' else ''}"
        self.exe_dest_path = os.path.join(BINARIES_DIR_PATH, self.exe_name)
        self.build_log_name = f"kvazaar_{self.commit_hash[:FILENAME_COMMIT_HASH_LEN]}_{self.define_hash}_build_log.txt"
        self.build_log_path = os.path.join(BINARIES_DIR_PATH, self.build_log_name)

        core.console_logger.info(f"Kvazaar revision '{self.revision}' maps to commit hash '{self.commit_hash}'")

        # Don't build unnecessarily.
        if (os.path.exists(self.exe_dest_path)):
            core.console_logger.info(f"Executable '{self.exe_dest_path}' already exists - aborting build")
            return

        if not os.path.exists(BINARIES_DIR_PATH):
            build_log_buffer.append(f"Creating directory '{BINARIES_DIR_PATH}'")
            os.makedirs(BINARIES_DIR_PATH)

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

        if OS_NAME == "Windows":
            assert os.path.exists(KVZ_VS_SOLUTION_PATH)

            # Add defines to msbuild arguments.
            MSBUILD_SEMICOLON_ESCAPE = "%3B"
            KVZ_MSBUILD_ARGS.append("/p:DefineConstants={}".format(MSBUILD_SEMICOLON_ESCAPE.join(self.defines)))

            # Run VsDevCmd.bat, then msbuild. Return 0 on success, 1 on failure.
            # KVZ_MSBUILD_ARGS has to be a list/tuple so the syntax below is pretty stupid.
            # TODO: Find a less idiotic and more readable way to do this.
            compile_cmd: tuple = ("(", "call", VS_VSDEVCMD_BAT_PATH,
                                       "&&", "msbuild", KVZ_VS_SOLUTION_PATH) + tuple(KVZ_MSBUILD_ARGS) + (
                                       "&&", "exit", "0",
                                  ")", "||", "exit", "1")
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
            assert os.path.exists(KVZ_EXE_SRC_PATH_WINDOWS)
            try:
                build_logger.info(f"Copying file '{KVZ_EXE_SRC_PATH_WINDOWS}' to '{self.exe_dest_path}'")
                shutil.copy(KVZ_EXE_SRC_PATH_WINDOWS, self.exe_dest_path)

            except FileNotFoundError as exception:
                core.console_logger.error(str(exception))
                build_logger.error(str(exception))
                raise

        elif OS_NAME == "Linux":
            # Add defines to configure arguments.
            cflags_str = f"CFLAGS={''.join([f'-D{define} ' for define in self.defines])}"
            KVZ_CONFIGURE_ARGS.append(cflags_str.strip())

            # Run autogen.sh, then configure, then make. Return 0 on success, 1 on failure.
            # TODO: Find a better way to do this (KVZ_CONFIGURE_ARGS is a tuple).
            compile_cmd = (
                "(", "cd", KVZ_GIT_REPO_PATH,
                     "&&", KVZ_AUTOGEN_SCRIPT_PATH,
                     "&&", KVZ_CONFIGURE_SCRIPT_PATH,) + tuple(KVZ_CONFIGURE_ARGS) + (
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
            assert os.path.exists(KVZ_EXE_SRC_PATH_LINUX)
            build_logger.info(f"Copying file '{KVZ_EXE_SRC_PATH_LINUX}' to '{self.exe_dest_path}'")
            try:
                shutil.copy(KVZ_EXE_SRC_PATH_LINUX, self.exe_dest_path)
            except FileNotFoundError as exception:
                core.console_logger.error(str(exception))
                build_logger.error(str(exception))
                raise

            # Clean the build so that Kvazaar binaries of different versions
            # can be built without problems if desired. This is not logged.
            clean_cmd = (
                "(", "cd", KVZ_GIT_REPO_PATH,
                     "&&", "make", "clean",
                     "&&", "exit", "0",
                ")", "||", "exit", "1"
            )
            try:
                subprocess.check_output(subprocess.list2cmdline(clean_cmd), shell=True)
            except subprocess.CalledProcessError as exception:
                core.console_logger.error(exception.output.decode())
                raise

        # Only Linux and Windows are supported.
        else:
            exception = RuntimeError(f"Unsupported OS '{OS_NAME}'. Expected one of ['Linux', 'Windows']")
            core.console_logger.error(str(exception))
            raise exception
