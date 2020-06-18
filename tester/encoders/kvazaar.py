#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module defines all Kvazaar-specific functionality.
"""

import hashlib
import logging
import os
import platform
import shutil
import subprocess
import sys

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

# Set up global console logger.
formatter = logging.Formatter("--%(levelname)s: %(message)s")
handler = logging.StreamHandler(sys.stdout)
console_logger = logging.getLogger("console")
handler.setFormatter(formatter)
console_logger.addHandler(handler)
console_logger.setLevel(logging.DEBUG)

def setup_build_logger(log_name: str, log_filename: str) -> logging.Logger:
    """Initializes and returns a Logger object with the given name and filename.
    The returned object is intended to be used for build logging.
    NOTE: Make sure this function is always called with a different log_name!"""
    formatter = logging.Formatter("%(message)s")
    handler = logging.FileHandler(log_filename, "w")
    handler.setFormatter(formatter)
    build_logger = logging.getLogger(log_name)
    build_logger.addHandler(handler)
    build_logger.setLevel(logging.DEBUG)
    return build_logger

class TestInstance():
    """
    This class defines all Kvazaar-specific functionality.
    """

    def __init__(self, revision: str, defines: list):
        self.defines: list = sorted(set(defines)) # ensure no duplicates
        self.define_hash: str = hashlib.md5(str(self.defines).encode()).digest().hex()[:16] # first 16 digits of MD5
        self.revision: str = revision
        self.exe_name: str = f"kvazaar_{self.revision}_{self.define_hash}{'.exe' if OS_NAME == 'Windows' else ''}"
        self.exe_dest_path: str = os.path.join(BINARIES_DIR_PATH, self.exe_name)
        self.build_log_name: str = f"kvazaar_{self.revision}_{self.define_hash}_build_log.txt"
        self.build_log_path: str = os.path.join(BINARIES_DIR_PATH, self.build_log_name)

    def build(self):
        console_logger.info(f"Building Kvazaar (revision '{self.revision}')")

        # Don't build unnecessarily.
        if (os.path.exists(self.exe_dest_path)):
            console_logger.info(f"Executable '{self.exe_dest_path}' already exists - aborting build")
            return

        if not os.path.exists(BINARIES_DIR_PATH):
            os.makedirs(BINARIES_DIR_PATH)

        build_logger: logging.Logger = setup_build_logger(self.exe_name, self.build_log_path)

        # Clone the remote if the local repo doesn't exist yet.
        if not os.path.exists(KVZ_GIT_REPO_PATH):
            try:
                clone_command: tuple = ("git", "clone", KVZ_GITLAB_REPO_SSH_URL, KVZ_GIT_REPO_PATH)
                build_logger.info(subprocess.list2cmdline(clone_command))
                output: bytes = subprocess.check_output(clone_command)
                build_logger.info(output.decode())
            except subprocess.CalledProcessError as exception:
                build_logger.error(exception.output.decode())
                console_logger.error(exception.output.decode())
                raise

        # Checkout to the desired version.
        try:
            checkout_command: tuple = ("git",
                                       "--work-tree", KVZ_GIT_REPO_PATH,
                                       "--git-dir", KVZ_GIT_DIR_PATH,
                                       "checkout", self.revision)
            build_logger.info(subprocess.list2cmdline(checkout_command))
            output: bytes = subprocess.check_output(checkout_command, stderr=subprocess.STDOUT)
            build_logger.info(output.decode())
        except subprocess.CalledProcessError as exception:
            console_logger.error(exception.output.decode())
            build_logger.error(exception.output.decode())
            raise

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
                console_logger.error(exception.output.decode())
                build_logger.error(exception.output.decode())
                raise

            # Copy the executable to its destination.
            assert os.path.exists(KVZ_EXE_SRC_PATH_WINDOWS)
            try:
                build_logger.info(f"Copying file '{KVZ_EXE_SRC_PATH_WINDOWS}' to '{self.exe_dest_path}'")
                shutil.copy(KVZ_EXE_SRC_PATH_WINDOWS, self.exe_dest_path)

            except FileNotFoundError as exception:
                console_logger.error(str(exception))
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
                console_logger.error(exception.output.decode())
                build_logger.error(exception.output.decode())
                raise

            # Copy the executable to its destination.
            assert os.path.exists(KVZ_EXE_SRC_PATH_LINUX)
            build_logger.info(f"Copying file '{KVZ_EXE_SRC_PATH_LINUX}' to '{self.exe_dest_path}'")
            try:
                shutil.copy(KVZ_EXE_SRC_PATH_LINUX, self.exe_dest_path)
            except FileNotFoundError as exception:
                console_logger.error(str(exception))
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
                console_logger.error(exception.output.decode())
                raise

        # Only Linux and Windows are supported.
        else:
            exception = RuntimeError(f"Unsupported OS '{OS_NAME}'. Expected one of ['Linux', 'Windows']")
            console_logger.error(str(exception))
            raise exception
