"""This module defines functionality to enable customization of the tester functionality."""

from .log import *
from .singleton import *
from . import csv # To avoid circular import

import platform
import re
from pathlib import Path

# Import the user's configuration file if it exists.
try:
    import userconfig
except ImportError:
    userconfig = None


class Cfg(metaclass=Singleton):
    """Global tester configuration singleton. Contains all variables that can be used to customize
    the functionality of the tester. Default values can be overridden in userconfig.py."""

    # Regex to recognize configuration variables.
    __VALID_VARIABLE_PATTERN: re.Pattern = re.compile(r"^[A-Z][0-9A-Z_]+$")
    # Regex to recognize properties (i.e. getters).
    __VALID_PROPERTY_PATTERN: re.Pattern = re.compile(r"^[a-z][0-9a-z_]+$")

    def __init__(self):
        pass

    # INTERNAL FUNCTIONS

    def read_userconfig(self) -> None:
        """Reads userconfig.py if it exists and overrides default variable values with those
        presented in it. Meant to be called by the tester."""

        if userconfig:
            console_log.info("Cfg: Reading userconfig")

            # Set and print values of variables with valid names.
            for variable_name in self._user_variable_names():
                if hasattr(self, variable_name):
                    value = getattr(userconfig, variable_name)
                    console_log.debug(f"Cfg: Variable userconfig.{variable_name} = {value}")
                    setattr(self, variable_name, value)

            # Check that all variables are recognized.
            for variable_name in self._user_variable_names():
                if not hasattr(self, variable_name):
                    console_log.error(f"Cfg: Unknown variable userconfig.{variable_name}")
                    raise RuntimeError
        else:
            console_log.warning("Cfg: Userconfig not found")

    def validate_all(self) -> None:
        """Validates configuration variables.
        - If a path does not exist, a warning is issued.
        Meant to be called by the tester."""

        # Print variable values.
        for variable_name in self._variable_names():
            console_log.debug(f"Cfg: Variable {variable_name} = {getattr(self, variable_name)}")

        # Print property values.
        for property_name in self._property_names():
            console_log.debug(f"Cfg: Property {property_name} = {getattr(self, property_name)}")

        # Check whether the paths defined by the properties exist - warn if not.
        for property_name in self._property_names():
            property = getattr(self, property_name)
            if isinstance(property, Path) and not property.exists():
                console_log.warning(f"Cfg: Property {property_name}:"
                                       f" Path '{getattr(self, property_name)}' does not exist")

        # Only Linux and Windows are supported.
        SUPPORTED_OSES = ["Linux", "Windows"]
        if not self.os_name in SUPPORTED_OSES:
            console_log.error(f"Cfg: Unsupported OS '{Cfg().os_name}'. Expected one of "
                                 f"{SUPPORTED_OSES}")
            raise RuntimeError

    def _property_names(self) -> list:
        """Returns the names of all properties (getters) in an alphabetically ordered list."""

        properties = []
        for property_name in dir(self):
            is_property = isinstance(getattr(type(self), property_name, None), property)
            if is_property:
                properties.append(property_name)
        return sorted(properties)

    def _variable_names(self) -> list:
        """Returns the names of all configuration variables in an alphabetically ordered list."""

        variables: list = []
        for variable_name in dir(self):
            if self.__VALID_VARIABLE_PATTERN.fullmatch(variable_name):
                variables.append(variable_name)
        return sorted(variables)

    def _user_variable_names(self) -> list:
        """Returns the names of all uppercase variables in userconfig.py in an alphabetically ordered list."""
        user_variables: list = []
        for variable_name in dir(userconfig):
            if variable_name.isupper():
                user_variables.append(variable_name)
        return sorted(user_variables)

    # PUBLIC VARIABLES AND PROPERTIES (GETTERS)
    # Private constants are named with capital letters and start with two underscores.
    # These must not be touched.
    # Public variables are named with capital letters. These can be changed freely by the user.
    # Every constant/variable should have a getter that is declared a property.
    # Some getters don't require a matching constant/variable because they can be derived from other
    # constants/variables.

    @property
    def os_name(self) -> str:
        """Returns the return value of platform.system()."""
        return platform.system()

    # Must not be overridden by the user.
    __PROJECT_ROOT_PATH: Path = (Path(__file__).parent / ".." / "..").resolve()
    @property
    def project_root_path(self) -> Path:
        """Returns the absolute path of the Git repository."""
        return self.__PROJECT_ROOT_PATH

    # Must not be overridden by the user.
    __TESTER_ROOT_PATH: Path = (Path(__file__).parent / "..").resolve()
    @property
    def tester_root_path(self) -> Path:
        """Returns the absolute path of the tester root directory."""
        return self.__TESTER_ROOT_PATH

    BINARIES_DIR_NAME: str = "_binaries"
    @property
    def binaries_dir_name(self) -> str:
        """Returns the name of the directory in which executables built by the tester
        will be placed."""
        return self.BINARIES_DIR_NAME

    @property
    def binaries_dir_path(self) -> Path:
        """Returns the absolute path of the directory in which executables built by the tester
        will be placed."""
        return self.tester_root_path / self.binaries_dir_name

    SOURCES_DIR_NAME = "_sources"
    @property
    def sources_dir_name(self) -> str:
        """Returns the name of the directory in which source code fetched by the tester
        will be placed."""
        return self.SOURCES_DIR_NAME

    @property
    def sources_dir_path(self) -> Path:
        """Returns the path of the directory in which source code fetched by the tester
        will be placed."""
        return self.tester_root_path / self.sources_dir_name

    SHORT_COMMIT_HASH_LEN: int = 16
    @property
    def short_commit_hash_len(self) -> int:
        """Returns the number of characters included in the commit hash part in the names of
        executables built by the tester."""
        return self.SHORT_COMMIT_HASH_LEN

    SHORT_DEFINE_HASH_LEN: int = 8
    @property
    def short_define_hash_len(self) -> int:
        """Returns the number of characters included in the define hash part in the names of
        executables built by the tester."""
        return self.SHORT_DEFINE_HASH_LEN

    VS_INSTALL_PATH: Path = Path("C:/") / "Program Files (x86)" / "Microsoft Visual Studio"
    @property
    def vs_install_path(self) -> Path:
        """Returns the absolute path of the Visual Studio base installation directory."""
        return self.VS_INSTALL_PATH

    VS_VERSION: str = "2019"
    @property
    def vs_version(self) -> str:
        """Returns the Visual Studio version (year) to be used."""
        return self.VS_VERSION

    VS_EDITION: str = "Enterprise"
    @property
    def vs_edition(self) -> str:
        """Returns the Visual Studio edition ("Community" or "Enterprise") to be used."""
        return self.VS_EDITION

    @property
    def vs_vsdevcmd_bat_path(self) -> Path:
        """Returns the absolute path of VsDevCmd.bat (Visual Studio command line environment setup
        batch script)."""
        return self.vs_install_path / self.vs_version / self.vs_edition / "Common7" / "Tools" / "VsDevCmd.bat"

    KVZ_GIT_REPO_NAME: str = "kvazaar"
    @property
    def kvz_git_repo_name(self) -> str:
        """Returns the name the tester will give to the Kvazaar Git repository when fetching
        source code."""
        return self.KVZ_GIT_REPO_NAME

    @property
    def kvz_git_repo_path(self) -> Path:
        """Returns the absolute path of the Kvazaar Git repository."""
        return self.sources_dir_path / self.kvz_git_repo_name

    @property
    def kvz_git_dir_path(self) -> Path:
        """Returns the absolute path of the .git directory within the Kvazaar Git repository."""
        return self.kvz_git_repo_path / ".git"

    KVZ_GIT_REPO_SSH_URL: str = "git@gitlab.tut.fi:TIE/ultravideo/kvazaar.git"
    @property
    def kvz_git_repo_ssh_url(self) -> str:
        """Returns the SSH URL to be used when cloning Kvazaar from a remote repository."""
        return self.KVZ_GIT_REPO_SSH_URL

    KVZ_EXE_SRC_NAME: str = f"kvazaar{'.exe' if platform.system() == 'Windows' else ''}"
    @property
    def kvz_exe_src_name(self) -> str:
        """Returns the default name the Kvazaar executable has when it has been compiled."""
        return self.KVZ_EXE_SRC_NAME

    @property
    def kvz_exe_src_path_windows(self) -> Path:
        """Returns the absolute path of the Kvazaar executable after compiling on Windows."""
        return self.kvz_git_repo_path / "bin" / "x64-Release" / self.kvz_exe_src_name

    @property
    def kvz_exe_src_path_linux(self) -> Path:
        """Returns the absolute path of the Kvazaar executable after compiling on Linux."""
        return self.kvz_git_repo_path / "src" / "kvazaar"

    KVZ_MSBUILD_CONFIGURATION: str = "Release"
    @property
    def kvz_msbuild_configuration(self) -> str:
        """Returns the value of the Configuration property (/p:Configuration)
        passed to MSBuild when compiling Kvazaar on Windows."""
        return self.KVZ_MSBUILD_CONFIGURATION

    KVZ_MSBUILD_PLATFORM: str = "x64"
    @property
    def kvz_msbuild_platform(self) -> str:
        """Returns the value of the Platform property (/p:Platform)
        passed to MSBuild when compiling Kvazaar on Windows."""
        return self.KVZ_MSBUILD_PLATFORM

    KVZ_MSBUILD_PLATFORMTOOLSET: str = "v142"
    @property
    def kvz_msbuild_platformtoolset(self) -> str:
        """Returns the value of the PlatformToolSet property (/p:PlatformToolSet)
        passed to MSBuild when compiling Kvazaar on Windows."""
        return self.KVZ_MSBUILD_PLATFORMTOOLSET

    KVZ_MSBUILD_WINDOWSTARGETPLATFORMVERSION: str = "10.0"
    @property
    def kvz_msbuild_windowstargetplatformversion(self) -> str:
        """Returns the value of the WindowsTargetPlatformVersion property (/p:WindowsTargetPlatformVersion)
        passed to MSBuild when compiling Kvazaar on Windows."""
        return self.KVZ_MSBUILD_WINDOWSTARGETPLATFORMVERSION

    KVZ_MSBUILD_ARGS: list = [
        f"/p:Configuration={KVZ_MSBUILD_CONFIGURATION}",
        f"/p:Platform={KVZ_MSBUILD_PLATFORM}",
        f"/p:PlatformToolset={KVZ_MSBUILD_PLATFORMTOOLSET}",
        f"/p:WindowsTargetPlatformVersion={KVZ_MSBUILD_WINDOWSTARGETPLATFORMVERSION}",
    ]
    @property
    def kvz_msbuild_args(self) -> list:
        """Returns the additional command line arguments to be passed to MSBuild
        when compiling Kvazaar on Windows."""
        return self.KVZ_MSBUILD_ARGS

    KVZ_VS_SOLUTION_NAME: str = "kvazaar_VS2015.sln"
    @property
    def kvz_vs_solution_name(self) -> str:
        """Returns the name of the Kvazaar Visual Studio solution."""
        return self.KVZ_VS_SOLUTION_NAME

    @property
    def kvz_vs_solution_path(self) -> Path:
        """Returns the absolute path of the Kvazaar Visual Studio solution."""
        return self.kvz_git_repo_path / "build" / self.kvz_vs_solution_name

    @property
    def kvz_autogen_script_path(self) -> Path:
        """Returns the absolute path of the autogen.sh script in the Kvazaar Git repository."""
        return self.kvz_git_repo_path / "autogen.sh"

    @property
    def kvz_configure_script_path(self) -> Path:
        """Returns the absolute path of the configure script in the Kvazaar Git repository."""
        return self.kvz_git_repo_path / "configure"

    KVZ_CONFIGURE_ARGS: list = [
        # We want a self-contained executable.
        "--disable-shared",
        "--enable-static",
    ]
    @property
    def kvz_configure_args(self) -> list:
        """Returns a list of arguments to be passed to the configure script
        when compiling Kvazaar on Linux."""
        return self.KVZ_CONFIGURE_ARGS

    ENCODING_OUTPUT_DIR_NAME: str = "_output"
    @property
    def encoding_output_dir_name(self) -> str:
        """Returns the name of the directory in which encoded video files
        will be placed by the tester."""
        return self.ENCODING_OUTPUT_DIR_NAME

    @property
    def encoding_output_dir_path(self) -> Path:
        """Returns the absolute path of the directory in which encoded video files
        will be placed by the tester."""
        return self.tester_root_path / self.encoding_output_dir_name

    CSV_FIELD_SEPARATOR: str = ";"
    @property
    def csv_field_separator(self) -> str:
        """Returns the character to be used as the field separator when generating CSV files."""
        return self.CSV_FIELD_SEPARATOR

    CSV_DECIMAL_POINT: str = "."
    @property
    def csv_decimal_point(self) -> str:
        """Returns the character to be used as the decimal point when generating CSV files."""
        return self.CSV_DECIMAL_POINT

    CSV_ENABLED_FIELDS: list = [
        csv.CsvFieldId.SEQUENCE_NAME,
        csv.CsvFieldId.SEQUENCE_CLASS,
        csv.CsvFieldId.SEQUENCE_FRAMECOUNT,
        csv.CsvFieldId.ENCODER_NAME,
        csv.CsvFieldId.ENCODER_REVISION,
        csv.CsvFieldId.ENCODER_DEFINES,
        csv.CsvFieldId.ENCODER_CMDLINE,
        csv.CsvFieldId.QUALITY_PARAM_NAME,
        csv.CsvFieldId.QUALITY_PARAM_VALUE,
        csv.CsvFieldId.CONFIG_NAME,
        csv.CsvFieldId.TIME_SECONDS,
        csv.CsvFieldId.PSNR_AVG,
        csv.CsvFieldId.SSIM_AVG,
        csv.CsvFieldId.ANCHOR_NAME,
        csv.CsvFieldId.SPEEDUP,
        csv.CsvFieldId.BDBR_PSNR,
        csv.CsvFieldId.BDBR_SSIM,
    ]
    @property
    def csv_enabled_fields(self) -> list:
        """Returns the CSV field IDs in the order they will appear in the CSV file."""
        return self.CSV_ENABLED_FIELDS

    CSV_FIELD_NAMES: dict = {
        csv.CsvFieldId.SEQUENCE_NAME: "Sequence name",
        csv.CsvFieldId.SEQUENCE_CLASS: "Sequence class",
        csv.CsvFieldId.SEQUENCE_FRAMECOUNT: "Frames",
        csv.CsvFieldId.ENCODER_NAME: "Encoder",
        csv.CsvFieldId.ENCODER_REVISION: "Revision",
        csv.CsvFieldId.ENCODER_DEFINES: "Defines",
        csv.CsvFieldId.ENCODER_CMDLINE: "Command",
        csv.CsvFieldId.QUALITY_PARAM_NAME: "Quality parameter",
        csv.CsvFieldId.QUALITY_PARAM_VALUE: "Quality parameter value",
        csv.CsvFieldId.CONFIG_NAME: "Configuration name",
        csv.CsvFieldId.ANCHOR_NAME: "Anchor name",
        csv.CsvFieldId.TIME_SECONDS: "Encoding time (s)",
        csv.CsvFieldId.SPEEDUP: "Speedup",
        csv.CsvFieldId.PSNR_AVG: "PSNR (avg)",
        csv.CsvFieldId.SSIM_AVG: "SSIM (avg)",
        csv.CsvFieldId.BDBR_PSNR: "BD-BR (PSNR)",
        csv.CsvFieldId.BDBR_SSIM: "BD-BR (SSIM)",
    }
    @property
    def csv_field_names(self) -> dict:
        """Returns the CSV field names in a dict where the key is the field ID and the value
        is the name of the field as a string."""
        return self.CSV_FIELD_NAMES

    CSV_FLOAT_ROUNDING_ACCURACY: int = 6
    @property
    def csv_float_rounding_accuracy(self) -> int:
        """Returns the number that will be used as the parameter to round() when rounding floats
        during CSV file generation."""
        return self.CSV_FLOAT_ROUNDING_ACCURACY
