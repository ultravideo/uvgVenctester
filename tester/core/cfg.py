#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module defines configuration variables that affect the global state
and execution flow of the tester. The user may set up a userconfig.py
to override the default values.
"""

from core.singleton import *
from core.log import *
import os
import platform
import re

# Import user's configuration file if it exists.
try:
    import userconfig
except ImportError:
    userconfig = None


class Cfg(metaclass=Singleton):

    # Normal variable naming, but must start with a letter
    # and uppercase only for variables, lowercase only for
    # properties (i.e. getters).
    __VALID_VARIABLE_PATTERN = re.compile(r"^[A-Z][0-9A-Z_]+$")
    __VALID_PROPERTY_PATTERN = re.compile(r"^[a-z][0-9a-z_]+$")

    def __init__(self):
        pass

    def read_userconfig(self):
        # Read userconfig.
        if userconfig:
            console_logger.debug("Reading userconfig")

            # Set and print values of variables with valid names.
            for variable_name in self.user_variable_names():
                if hasattr(self, variable_name):
                    value = getattr(userconfig, variable_name)
                    console_logger.debug(f"Userconfig: cfg.{variable_name} = {value}")
                    setattr(self, variable_name, value)

            # Print and warn of invalid variables.
            for variable_name in self.user_variable_names():
                if not hasattr(self, variable_name):
                    console_logger.warning(f"Userconfig: Unknown variable '{variable_name}' - is the spelling correct?")
        else:
            console_logger.warning("Userconfig not found")

    def validate_all(self):
        # Print variable values.
        for variable_name in self.variable_names():
            console_logger.debug(f"cfg.{variable_name} = {getattr(self, variable_name)}")

        # Print property values.
        for property_name in self.property_names():
            console_logger.debug(f"cfg.{property_name} = {getattr(self, property_name)}")

        # Check whether the paths defined by the properties exist - warn if not.
        for property_name in self.property_names():
            if "path" in property_name and not os.path.exists(getattr(self, property_name)):
                console_logger.warning(f"cfg.{property_name}: Path '{getattr(self, property_name)}'"
                                       f" does not exist")

    def property_names(self) -> list:
        properties = []
        for property_name in dir(self):
            is_property = isinstance(getattr(type(self), property_name, None), property)
            if is_property:
                properties.append(property_name)
        return sorted(properties)

    def variable_names(self) -> list:
        variables: list = []
        for variable_name in dir(self):
            if self.__VALID_VARIABLE_PATTERN.fullmatch(variable_name):
                variables.append(variable_name)
        return sorted(variables)

    def user_variable_names(self) -> list:
        user_variables: list = []
        for variable_name in dir(userconfig):
            if variable_name.isupper():
                user_variables.append(variable_name)
        return sorted(user_variables)

    ##########################################################################
    # ACTUAL CONFIGURATION VARIABLES
    ##########################################################################
    # Private constants are named with capital letters and start with two underscores.
    # These must not be touched.
    # Public variables are named with capital letters. These can be changed freely by the user.
    # Every constant/variable should have a getter that is declared a property.
    # Some getters don't require a matching constant/variable because they can be derived from other
    # constants/variables.

    @property
    def os_name(self) -> str:
        return platform.system()

    __PROJECT_ROOT_PATH: str = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", ".."))
    @property
    def project_root_path(self) -> str:
        return self.__PROJECT_ROOT_PATH

    __TESTER_ROOT_PATH: str = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))
    @property
    def tester_root_path(self) -> str:
        return self.__TESTER_ROOT_PATH

    BINARIES_DIR_NAME: str = "_binaries"
    @property
    def binaries_dir_name(self) -> str:
        return self.BINARIES_DIR_NAME

    @property
    def binaries_dir_path(self) -> str:
        return os.path.join(self.tester_root_path, self.binaries_dir_name)

    REPORTS_DIR_NAME = "_reports"
    @property
    def reports_dir_name(self) -> str:
        return self.REPORTS_DIR_NAME

    @property
    def reports_dir_path(self) -> str:
        return os.path.join(self.tester_root_path, self.reports_dir_name)

    SOURCES_DIR_NAME = "_sources"
    @property
    def sources_dir_name(self) -> str:
        return self.SOURCES_DIR_NAME

    @property
    def sources_dir_path(self) -> str:
        return os.path.join(self.tester_root_path, self.sources_dir_name)

    @property
    def short_commit_hash_len(self) -> int:
        return 16

    @property
    def short_define_hash_len(self) -> int:
        return 8

    VS_INSTALL_PATH: str = r"C:\Program Files (x86)\Microsoft Visual Studio"
    @property
    def vs_install_path(self) -> str:
        return self.VS_INSTALL_PATH

    VS_VERSION: str = "2019"
    @property
    def vs_version(self) -> str:
        return self.VS_VERSION

    VS_EDITION: str = "Enterprise"
    @property
    def vs_edition(self) -> str:
        return self.VS_EDITION

    @property
    def vs_vsdevcmd_bat_path(self) -> str:
        return os.path.join(self.VS_INSTALL_PATH, self.VS_VERSION, self.VS_EDITION,
                            "Common7", "Tools", "VsDevCmd.bat")

    KVZ_GIT_REPO_NAME: str = "kvazaar"
    @property
    def kvz_git_repo_name(self) -> str:
        return self.KVZ_GIT_REPO_NAME

    @property
    def kvz_git_repo_path(self) -> str:
        return os.path.join(self.sources_dir_path, self.kvz_git_repo_name)

    @property
    def kvz_git_dir_path(self) -> str:
        return os.path.join(self.kvz_git_repo_path, ".git")

    KVZ_GIT_REPO_SSH_URL: str = "git@gitlab.tut.fi:TIE/ultravideo/kvazaar.git"
    @property
    def kvz_git_repo_ssh_url(self) -> str:
        return self.KVZ_GIT_REPO_SSH_URL

    KVZ_EXE_SRC_NAME: str = f"kvazaar{'.exe' if platform.system() == 'Windows' else ''}"
    @property
    def kvz_exe_src_name(self) -> str:
        return self.KVZ_EXE_SRC_NAME

    @property
    def kvz_exe_src_path_windows(self) -> str:
        return os.path.join(self.kvz_git_repo_path, "bin", "x64-Release", self.kvz_exe_src_name)

    @property
    def kvz_exe_src_path_linux(self) -> str:
        return os.path.join(self.kvz_git_repo_path, "src", "kvazaar")

    KVZ_MSBUILD_CONFIGURATION: str = "Release"
    @property
    def kvz_msbuild_configuration(self) -> str:
        return self.KVZ_MSBUILD_CONFIGURATION

    KVZ_MSBUILD_PLATFORM: str = "x64"
    @property
    def kvz_msbuild_platform(self) -> str:
        return self.KVZ_MSBUILD_PLATFORM

    KVZ_MSBUILD_PLATFORMTOOLSET: str = "v142"
    @property
    def kvz_msbuild_platformtoolset(self) -> str:
        return self.KVZ_MSBUILD_PLATFORMTOOLSET

    KVZ_MSBUILD_WINDOWSTARGETPLATFORMVERSION: str = "10.0"
    @property
    def kvz_msbuild_windowstargetplatformversion(self) -> str:
        return self.KVZ_MSBUILD_WINDOWSTARGETPLATFORMVERSION

    KVZ_MSBUILD_ARGS: list = [
        f"/p:Configuration={KVZ_MSBUILD_CONFIGURATION}",
        f"/p:Platform={KVZ_MSBUILD_PLATFORM}",
        f"/p:PlatformToolset={KVZ_MSBUILD_PLATFORMTOOLSET}",
        f"/p:WindowsTargetPlatformVersion={KVZ_MSBUILD_WINDOWSTARGETPLATFORMVERSION}",
    ]
    @property
    def kvz_msbuild_args(self) -> list:
        return self.KVZ_MSBUILD_ARGS

    KVZ_VS_SOLUTION_NAME: str = "kvazaar_VS2015.sln"
    @property
    def kvz_vs_solution_name(self) -> str:
        return self.KVZ_VS_SOLUTION_NAME

    @property
    def kvz_vs_solution_path(self) -> str:
        return os.path.join(self.kvz_git_repo_path, "build", self.kvz_vs_solution_name)

    @property
    def kvz_autogen_script_path(self) -> str:
        return os.path.join(self.kvz_git_repo_path, "autogen.sh")

    @property
    def kvz_configure_script_path(self) -> str:
        return os.path.join(self.kvz_git_repo_path, "configure")

    KVZ_CONFIGURE_ARGS: list = [
        # We want a self-contained executable.
        "--disable-shared",
        "--enable-static",
    ]
    @property
    def kvz_configure_args(self) -> list:
        return self.KVZ_CONFIGURE_ARGS

    CONSOLE_LOG_LEVEL: int = logging.DEBUG
    @property
    def console_log_level(self) -> int:
        return self.CONSOLE_LOG_LEVEL

    BUILD_LOG_LEVEL: int = logging.DEBUG
    @property
    def build_log_level(self) -> int:
        return self.BUILD_LOG_LEVEL

    ENCODING_OUTPUT_DIR_NAME: str = "_output"
    @property
    def encoding_output_dir_name(self) -> str:
        return self.ENCODING_OUTPUT_DIR_NAME

    @property
    def encoding_output_dir_path(self) -> str:
        return os.path.join(self.tester_root_path, self.encoding_output_dir_name)
