#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module defines configuration variables that affect the global state
and execution flow of the tester.
"""

import os
import platform

OS_NAME: str = platform.system()

TESTER_ROOT_PATH: str = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))
PROJECT_ROOT_PATH: str = os.path.dirname(os.path.realpath(os.path.join(str(TESTER_ROOT_PATH), "..")))

BINARIES_DIR_NAME: str = "_binaries"
BINARIES_DIR_PATH: str = os.path.join(TESTER_ROOT_PATH, BINARIES_DIR_NAME)
REPORTS_DIR_NAME: str = "_reports"
REPORTS_DIR_PATH: str = os.path.join(TESTER_ROOT_PATH, REPORTS_DIR_NAME)
SOURCES_DIR_NAME: str = "_sources"
SOURCES_DIR_PATH: str = os.path.join(TESTER_ROOT_PATH, SOURCES_DIR_NAME)

SHORT_COMMIT_HASH_LEN: int = 16
SHORT_DEFINE_HASH_LEN: int = 8

VS_VSDEVCMD_BAT_PATH: str = r"C:\Program Files (x86)\Microsoft Visual Studio\2019\Enterprise\Common7\Tools\VsDevCmd.bat"

KVZ_GIT_REPO_PATH: str = os.path.join(SOURCES_DIR_PATH, "kvazaar")
KVZ_GIT_DIR_PATH: str = os.path.join(KVZ_GIT_REPO_PATH, ".git")
KVZ_COMPILE_SCRIPT_PATH_LINUX: str = os.path.join(TESTER_ROOT_PATH, "encoders", "kvazaar_compile_linux.sh")
KVZ_COMPILE_SCRIPT_PATH_WINDOWS: str = os.path.join(TESTER_ROOT_PATH, "encoders", "kvazaar_compile_windows.ps1")
KVZ_GITHUB_REPO_SSH_URL: str = "git@github.com:ultravideo/kvazaar.git"
KVZ_GITLAB_REPO_SSH_URL: str = "git@gitlab.tut.fi:TIE/ultravideo/kvazaar.git"
KVZ_EXE_SRC_NAME: str = f"kvazaar{'.exe' if OS_NAME == 'Windows' else ''}"
KVZ_EXE_SRC_PATH_WINDOWS: str = os.path.join(KVZ_GIT_REPO_PATH, "bin", "x64-Release", KVZ_EXE_SRC_NAME)
KVZ_EXE_SRC_PATH_LINUX: str = os.path.join(KVZ_GIT_REPO_PATH, "src", "kvazaar")
KVZ_MSBUILD_CONFIGURATION: str = "Release"
KVZ_MSBUILD_PLATFORM: str = "x64"
KVZ_MSBUILD_PLATFORMTOOLSET: str = "v142"
KVZ_MSBUILD_WINDOWSTARGETPLATFORMVERSION: str = "10.0"
KVZ_MSBUILD_ARGS: list = [
    f"/p:Configuration={KVZ_MSBUILD_CONFIGURATION}",
    f"/p:Platform={KVZ_MSBUILD_PLATFORM}",
    f"/p:PlatformToolset={KVZ_MSBUILD_PLATFORMTOOLSET}",
    f"/p:WindowsTargetPlatformVersion={KVZ_MSBUILD_WINDOWSTARGETPLATFORMVERSION}",
]
KVZ_VS_SOLUTION_NAME: str = "kvazaar_VS2015.sln"
KVZ_VS_SOLUTION_PATH: str = os.path.join(KVZ_GIT_REPO_PATH, "build", KVZ_VS_SOLUTION_NAME)
KVZ_AUTOGEN_SCRIPT_PATH: str = os.path.join(KVZ_GIT_REPO_PATH, "autogen.sh")
KVZ_CONFIGURE_SCRIPT_PATH: str = os.path.join(KVZ_GIT_REPO_PATH, "configure")
KVZ_CONFIGURE_ARGS: list = [
    "--disable-shared",
    "--enable-static",
]
