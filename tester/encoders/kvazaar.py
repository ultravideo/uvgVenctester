#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module defines all Kvazaar-specific functionality.
"""

from time import strftime
import os
import platform
import subprocess

TESTER_ROOT_PATH: str = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))
PROJECT_ROOT_PATH: str = os.path.dirname(os.path.realpath(os.path.join(str(TESTER_ROOT_PATH), "..")))
RESULTS_DIR_PATH: str = os.path.join(TESTER_ROOT_PATH, "results_{}".format(strftime("%Y-%m-%d_%H-%M-%S")))
BINARIES_DIR_PATH: str = os.path.join(TESTER_ROOT_PATH, ".cache")

VS_VSDEVCMD_BAT_PATH: str = r"C:\Program Files (x86)\Microsoft Visual Studio\2019\Enterprise\Common7\Tools\VsDevCmd.bat"

KVZ_GIT_REPO_PATH: str = os.path.join(TESTER_ROOT_PATH, ".sources", "kvazaar")
KVZ_COMPILE_SCRIPT_LINUX_PATH: str = os.path.join(TESTER_ROOT_PATH, "encoders", "kvazaar_compile_linux.sh")
KVZ_COMPILE_SCRIPT_WINDOWS_PATH: str = os.path.join(TESTER_ROOT_PATH, "encoders", "kvazaar_compile_windows.ps1")
KVZ_GITHUB_REPO_SSH_URL: str = "git@github.com:ultravideo/kvazaar.git"
KVZ_GITLAB_REPO_SSH_URL: str = "git@gitlab.tut.fi:TIE/ultravideo/kvazaar.git"
KVZ_MSBUILD_CONFIGURATION: str = "Release"
KVZ_MSBUILD_PLATFORM: str = "x64"
KVZ_MSBUILD_PLATFORMTOOLSET: str = "v142"
KVZ_MSBUILD_WINDOWSTARGETPLATFORMVERSION: str = "10.0"
KVZ_MSBUILD_ARGS: str = f"/p:Configuration={KVZ_MSBUILD_CONFIGURATION} " \
                        f"/p:Platform={KVZ_MSBUILD_PLATFORM} " \
                        f"/p:PlatformToolset={KVZ_MSBUILD_PLATFORMTOOLSET} " \
                        f"/p:WindowsTargetPlatformVersion={KVZ_MSBUILD_WINDOWSTARGETPLATFORMVERSION}"
KVZ_VS_SOLUTION_NAME: str = "kvazaar_VS2015.sln"
KVZ_VS_SOLUTION_PATH: str = os.path.join(KVZ_GIT_REPO_PATH, "build", KVZ_VS_SOLUTION_NAME)

class TestInstance(object):
    """
    This class defines all Kvazaar-specific functionality.
    """

    def __init__(self, revision: str):
        self.revision: str = revision
        self.exe_name: str = f"kvazaar_rev-{revision}.exe" if platform.system() == "Windows" else f"kvazaar_rev-{revision}"
        self.exe_dest_path: str = os.path.join(BINARIES_DIR_PATH, self.exe_name)

    def build(self):
        print(f"--INFO: Building Kvazaar (revision '{self.revision}')")

        # Don't build unnecessarily.
        if (os.path.exists(self.exe_dest_path)):
            print(f"--WARNING: {self.exe_dest_path} already exists - aborting build")
            return

        # Clone the remote if the local repo doesn't exist yet.
        if not os.path.exists(KVZ_GIT_REPO_PATH):
            try:
                clone_command: str = f"git clone {KVZ_GITLAB_REPO_SSH_URL} {KVZ_GIT_REPO_PATH}"
                print(clone_command)
                output: bytes = subprocess.check_output(clone_command.split())
                print(output.decode())
            except subprocess.CalledProcessError as exception:
                print(exception.output.decode())
                raise exception

        # Checkout to the desired version.
        try:
            git_dir: str = os.path.join(KVZ_GIT_REPO_PATH, ".git")
            checkout_command: str = f"git --work-tree {KVZ_GIT_REPO_PATH} --git-dir {git_dir} checkout {self.revision}"
            print(checkout_command)
            output: bytes = subprocess.check_output(checkout_command.split())
            print(output.decode())
        except subprocess.CalledProcessError as exception:
            print(exception.output.decode())
            raise exception

        if platform.system() == "Windows":
            # Prepare PowerShell script call. The script compiles Kvazaar with the Visual Studio toolchain.
            compile_command: str = "powershell " \
                                   f"-File {KVZ_COMPILE_SCRIPT_WINDOWS_PATH} " \
                                   f"\"{VS_VSDEVCMD_BAT_PATH}\" " \
                                   f"\"{KVZ_VS_SOLUTION_PATH}\" " \
                                   f"\"{self.exe_dest_path}\" " \
                                   f"\"{KVZ_MSBUILD_ARGS}\""

        elif platform.system() == "Linux":
            # Prepare Bourne shell script call. The script compiles Kvazaar using the scripts provided in the Kvazaar
            # repo.
            compile_command: str = f"{KVZ_COMPILE_SCRIPT_LINUX_PATH} {KVZ_GIT_REPO_PATH} {self.exe_dest_path}"

        # Only Linux and Windows are supported.
        else:
            raise RuntimeError("--ERROR: Unsupported operating system '{}'. Expected one of ['Linux', 'Windows'].".format(platform.system()))

        # Compile or die trying.
        print(compile_command)
        try:
            # Shell required on Linux.
            output: bytes = subprocess.check_output(compile_command.split(), shell=True, stderr=subprocess.STDOUT)
            print(output.decode())
        except subprocess.CalledProcessError as exception:
            print(exception.output.decode())
            raise exception
