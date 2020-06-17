#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module defines all Kvazaar-specific functionality.
"""

from time import strftime
import os
import platform
import shutil
import subprocess

OS_NAME = platform.system()

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
KVZ_MSBUILD_CONFIGURATION: str = "Release"
KVZ_MSBUILD_PLATFORM: str = "x64"
KVZ_MSBUILD_PLATFORMTOOLSET: str = "v142"
KVZ_MSBUILD_WINDOWSTARGETPLATFORMVERSION: str = "10.0"
KVZ_MSBUILD_ARGS: tuple = (f"/p:Configuration={KVZ_MSBUILD_CONFIGURATION}",
                           f"/p:Platform={KVZ_MSBUILD_PLATFORM}",
                           f"/p:PlatformToolset={KVZ_MSBUILD_PLATFORMTOOLSET}",
                           f"/p:WindowsTargetPlatformVersion={KVZ_MSBUILD_WINDOWSTARGETPLATFORMVERSION}")
KVZ_VS_SOLUTION_NAME: str = "kvazaar_VS2015.sln"
KVZ_VS_SOLUTION_PATH: str = os.path.join(KVZ_GIT_REPO_PATH, "build", KVZ_VS_SOLUTION_NAME)

class TestInstance():
    """
    This class defines all Kvazaar-specific functionality.
    """

    def __init__(self, revision: str):
        self.revision: str = revision
        self.exe_name: str = f"kvazaar_{revision}{'.exe' if OS_NAME == 'Windows' else ''}"
        self.exe_dest_path: str = os.path.join(BINARIES_DIR_PATH, self.exe_name)

    def build(self):
        print(f"--INFO: Building Kvazaar (revision '{self.revision}')")

        # Don't build unnecessarily.
        if (os.path.exists(self.exe_dest_path)):
            print(f"--WARNING: Executable '{self.exe_dest_path}' already exists - aborting build")
            return

        # Clone the remote if the local repo doesn't exist yet.
        if not os.path.exists(KVZ_GIT_REPO_PATH):
            try:
                clone_command: tuple = ("git", "clone", KVZ_GITLAB_REPO_SSH_URL, KVZ_GIT_REPO_PATH)
                print(subprocess.list2cmdline(clone_command))
                output: bytes = subprocess.check_output(clone_command)
                print(output.decode())
            except subprocess.CalledProcessError as exception:
                print(exception.output.decode())
                raise

        # Checkout to the desired version.
        try:
            checkout_command: tuple = ("git",
                                       "--work-tree", KVZ_GIT_REPO_PATH,
                                       "--git-dir", KVZ_GIT_DIR_PATH,
                                       "checkout", self.revision)
            print(subprocess.list2cmdline(checkout_command))
            output: bytes = subprocess.check_output(checkout_command)
            print(output.decode())
        except subprocess.CalledProcessError as exception:
            print(exception.output.decode())
            raise

        if OS_NAME == "Windows":
            assert os.path.exists(KVZ_VS_SOLUTION_PATH)

            # Run VsDevCmd.bat, then msbuild. Return 0 on success, 1 on failure.
            # KVZ_MSDBUILD_ARGS has to be a tuple so the syntax below is pretty stupid.
            # TODO: Find a less idiotic and more readable way to do this.
            compile_cmd: tuple = ("(", "call", VS_VSDEVCMD_BAT_PATH,
                                        "&&", "msbuild", KVZ_VS_SOLUTION_PATH) + KVZ_MSBUILD_ARGS + (
                                        "&&", "exit", "0",
                                   ")", "||", "exit", "1")
            print(subprocess.list2cmdline(compile_cmd))
            try:
                output: bytes = subprocess.check_output(compile_cmd, shell=True)
                print(output.decode(encoding="cp1252"))
            except subprocess.CalledProcessError as exception:
                print(exception.output.decode())
                raise

            if not os.path.exists(BINARIES_DIR_PATH):
                os.makedirs(BINARIES_DIR_PATH)

            assert os.path.exists(KVZ_EXE_SRC_PATH_WINDOWS)

            try:
                shutil.copy(KVZ_EXE_SRC_PATH_WINDOWS, self.exe_dest_path)
            except FileNotFoundError as exception:
                raise

        elif OS_NAME == "Linux":
            # Prepare Bourne shell script call. The script compiles Kvazaar using the scripts provided in the Kvazaar
            # repo.
            compile_cmd: tuple = (KVZ_COMPILE_SCRIPT_LINUX_PATH, KVZ_GIT_REPO_PATH, self.exe_dest_path)

        # Only Linux and Windows are supported.
        else:
            raise RuntimeError(f"--ERROR: Unsupported OS '{OS_NAME}'. Expected one of ['Linux', 'Windows']")

        # Compile or die trying.
        print(subprocess.list2cmdline(compile_cmd))
        try:
            # Shell required on Linux.
            output: bytes = subprocess.check_output(compile_cmd, shell=True, stderr=subprocess.STDOUT)
            print(output.decode())
        except subprocess.CalledProcessError as exception:
            print(exception.output.decode())
            raise
