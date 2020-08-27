"""This module defines functionality to enable customization of the tester functionality."""

import platform
from pathlib import Path
from typing import Union

import tester.core.csv as csv
from .singleton import Singleton


class Cfg(metaclass=Singleton):
    """Global tester configuration singleton. Contains all variables that can be used to customize
    the functionality of the tester. The user may override values not prefixed with underscores freely."""

    ##########################################################################
    # CONSTANTS
    # Do not touch.
    ##########################################################################

    ##########################################################################
    # Tester
    ##########################################################################

    # NOTE: These rely on that the working directory has not been changed since the program
    # was launched.
    __TESTER_PROJECT_ROOT_PATH: Path = (Path(__file__).parent / ".." / "..").resolve()
    __TESTER_ROOT_PATH: Path = (Path(__file__).parent / "..").resolve()

    ##########################################################################
    # System
    ##########################################################################

    @property
    def system_os_name(self) -> str:
        """The return value of platform.system()."""
        return platform.system()

    @property
    def system_cpu_arch(self) -> str:
        """The CPU architecture. 'x64' if x64, else whatever."""
        machine = platform.machine()
        if machine in ["AMD64", "x86_64"]:
            return "x64"
        else:
            return machine

    ##########################################################################
    # CONFIGURATION VARIABLES
    # May be overridden by the user.
    ##########################################################################

    ##########################################################################
    # Tester
    ##########################################################################

    _tester_binaries_dir_path: Union[str, Path] = __TESTER_ROOT_PATH / "_binaries"
    # The following enables the user to override the value as a string.
    @property
    def tester_binaries_dir_path(self) -> Path:
        """The base directory of encoder binaries."""
        return Path(self._tester_binaries_dir_path).resolve()
    @tester_binaries_dir_path.setter
    def tester_binaries_dir_path(self, value: Union[str, Path]):
        self._tester_binaries_dir_path = value

    _tester_sources_dir_path: Union[str, Path] = __TESTER_ROOT_PATH / "_sources"
    @property
    def tester_sources_dir_path(self) -> Path:
        """The base directory of encoder sources."""
        return Path(self._tester_sources_dir_path).resolve()
    @tester_sources_dir_path.setter
    def tester_sources_dir_path(self, value: Union[str, Path]):
        self._tester_sources_dir_path = value

    _tester_output_dir_path: Union[str, Path] = __TESTER_ROOT_PATH / "_output"
    @property
    def tester_output_dir_path(self) -> Path:
        """The base directory of encoding output."""
        return Path(self._tester_output_dir_path).resolve()
    @tester_output_dir_path.setter
    def tester_output_dir_path(self, value: Union[str, Path]):
        self._tester_output_dir_path = value

    _tester_input_dir_path: Union[str, Path] = Path.cwd()
    @property
    def tester_sequences_dir_path(self) -> Path:
        """The base directory of input sequences. Sequence paths are relative to this directory."""
        return Path(self._tester_input_dir_path).resolve()
    @tester_sequences_dir_path.setter
    def tester_sequences_dir_path(self, value: Union[str, Path]):
        self._tester_input_dir_path = value

    """How many characters of the commit hash are included in file names."""
    tester_commit_hash_len: int = 10

    """How many characters of the define hash are included in file names."""
    tester_define_hash_len: int = 6

    ##########################################################################
    # CSV
    ##########################################################################

    """The field delimiter to be used in the CSV."""
    csv_field_delimiter: str = ";"

    """The decimal point to be used in the CSV."""
    csv_decimal_point: str = "."

    """List of enabled CSV fields from left to right."""
    csv_enabled_fields: list = [
        csv.CsvField.SEQUENCE_NAME,
        csv.CsvField.SEQUENCE_CLASS,
        csv.CsvField.SEQUENCE_FRAMECOUNT,
        csv.CsvField.ENCODER_NAME,
        csv.CsvField.ENCODER_REVISION,
        csv.CsvField.ENCODER_DEFINES,
        csv.CsvField.ENCODER_CMDLINE,
        csv.CsvField.QUALITY_PARAM_NAME,
        csv.CsvField.QUALITY_PARAM_VALUE,
        csv.CsvField.CONFIG_NAME,
        csv.CsvField.TIME_SECONDS,
        csv.CsvField.TIME_STDEV,
        csv.CsvField.BITRATE,
        csv.CsvField.BITRATE_STDEV,
        csv.CsvField.PSNR_AVG,
        csv.CsvField.PSNR_STDEV,
        csv.CsvField.SSIM_AVG,
        csv.CsvField.SSIM_STDEV,
        csv.CsvField.VMAF_AVG,
        csv.CsvField.VMAF_STDEV,
        csv.CsvField.ANCHOR_NAME,
        csv.CsvField.SPEEDUP,
        csv.CsvField.BDBR_PSNR,
        csv.CsvField.BDBR_SSIM,
    ]

    """Key = CSV field ID, value = CSV field name."""
    csv_field_names: dict = {
        csv.CsvField.SEQUENCE_NAME: "Sequence name",
        csv.CsvField.SEQUENCE_CLASS: "Sequence class",
        csv.CsvField.SEQUENCE_FRAMECOUNT: "Frames",
        csv.CsvField.ENCODER_NAME: "Encoder",
        csv.CsvField.ENCODER_REVISION: "Revision",
        csv.CsvField.ENCODER_DEFINES: "Defines",
        csv.CsvField.ENCODER_CMDLINE: "Command",
        csv.CsvField.QUALITY_PARAM_NAME: "Quality parameter",
        csv.CsvField.QUALITY_PARAM_VALUE: "Quality parameter value",
        csv.CsvField.CONFIG_NAME: "Configuration name",
        csv.CsvField.ANCHOR_NAME: "Anchor name",
        csv.CsvField.TIME_SECONDS: "Encoding time (s)",
        csv.CsvField.TIME_STDEV: "Encoding time (stdev)",
        csv.CsvField.BITRATE: "Bitrate",
        csv.CsvField.BITRATE_STDEV: "Bitrate (stdev)",
        csv.CsvField.SPEEDUP: "Speedup",
        csv.CsvField.PSNR_AVG: "PSNR (avg)",
        csv.CsvField.PSNR_STDEV: "PSNR (stdev)",
        csv.CsvField.SSIM_AVG: "SSIM (avg)",
        csv.CsvField.SSIM_STDEV: "SSIM (stdev)",
        csv.CsvField.VMAF_AVG: "VMAF (avg)",
        csv.CsvField.VMAF_STDEV: "VMAF (stdev)",
        csv.CsvField.BDBR_PSNR: "BD-BR (PSNR)",
        csv.CsvField.BDBR_SSIM: "BD-BR (SSIM)",
    }

    """The accuracy with which floats are rounded when generating the output CSV."""
    csv_float_rounding_accuracy: int = 6

    ##########################################################################
    # HM
    ##########################################################################

    """The remote from which HM will be cloned."""
    hm_remote_url: str = "https://vcgit.hhi.fraunhofer.de/jct-vc/HM.git"

    """The path of the HM configuration file. Must be set by the user."""
    _hm_cfg_file_path: Union[str, Path] = None
    @property
    def hm_cfg_file_path(self):
        return Path(self._hm_cfg_file_path).resolve()
    @hm_cfg_file_path.setter
    def hm_cfg_file_path(self, value: Union[str, Path]):
        self._hm_cfg_file_path = value

    ##########################################################################
    # Kvazaar
    ##########################################################################

    """The remote from which Kvazaar will be cloned."""
    kvazaar_remote_url: str = "git@gitlab.tut.fi:TIE/ultravideo/kvazaar.git"

    ##########################################################################
    # Visual Studio
    ##########################################################################

    """The Visual Studio base installation directory."""
    _vs_install_path: Union[str, Path] = Path("C:/") / "Program Files (x86)" / "Microsoft Visual Studio"
    @property
    def vs_install_path(self) -> Path:
        """The Visual Studio base installation directory."""
        return Path(self._vs_install_path).resolve()
    @vs_install_path.setter
    def vs_install_path(self, value: Union[str, Path]):
        self._vs_install_path = value

    """The release year of the Visual Studio version in use (for example 2019 for VS 2019).
    Must be set by the user."""
    vs_year_version: str = None

    """The version of Visual Studio in use (for example VS 2019 is version 16).
    Must be set by the user."""
    vs_major_version: str = None

    """The edition of Visual Studio in use (Community/Professional/Enterprise).
    Must be set by the user."""
    vs_edition: str = None

    """The version of MSVC in use (for example 19.26). Can be checked with 'cl /version' on the
    command line. Must be set by the user."""
    vs_msvc_version: str = None

    """The /p:PlatformToolset parameter to be passed to MSBuild."""
    vs_msbuild_platformtoolset: str = None

    ##########################################################################
    # VMAF
    ##########################################################################

    _vmaf_repo_path: Union[str, Path] = None
    @property
    def vmaf_repo_path(self) -> Path:
        """The path of the VMAF repository. Must be set by the user."""
        return Path(self._vmaf_repo_path).resolve()
    @vmaf_repo_path.setter
    def vmaf_repo_path(self, value: Union[str, Path]):
        self._vmaf_repo_path = value

    ##########################################################################
    # VTM
    ##########################################################################

    vtm_remote_url: str = "https://vcgit.hhi.fraunhofer.de/jvet/VVCSoftware_VTM.git"


    """The path of the VTM configuration file. Must be set by the user."""
    _vtm_cfg_file_path: Union[str, Path] = None
    @property
    def vtm_cfg_file_path(self):
        return Path(self._vtm_cfg_file_path).resolve()
    @vtm_cfg_file_path.setter
    def vtm_cfg_file_path(self, value: Union[str, Path]):
        self._vtm_cfg_file_path = value
