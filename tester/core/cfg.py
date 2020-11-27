"""This module defines functionality to enable customization of the tester functionality."""
import logging
import platform
from pathlib import Path
from typing import Union
from enum import Enum

import tester.core.csv as csv
import tester.core.table as table
import tester.core.graphs as graphs
from .log import console_log
from .singleton import Singleton


class ReEncoding(Enum):
    OFF = 0
    SOFT = 1
    FORCE = 2


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

    def __init__(self):
        self.logging_level = self._logging_level

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
    # Logging
    ##########################################################################

    _logging_level = logging.INFO

    @property
    def logging_level(self) -> int:
        return self._logging_level

    @logging_level.setter
    def logging_level(self, value: int):
        assert value in logging._levelToName
        console_log.setLevel(value)

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
        return Path(Path(self._tester_input_dir_path).resolve())

    @tester_sequences_dir_path.setter
    def tester_sequences_dir_path(self, value: Union[str, Path]):
        self._tester_input_dir_path = value

    tester_commit_hash_len: int = 10
    """How many characters of the commit hash are included in file names."""

    tester_define_hash_len: int = 6
    """How many characters of the define hash are included in file names."""

    ##########################################################################
    # CSV
    ##########################################################################

    csv_field_delimiter: str = ";"
    """The field delimiter to be used in the CSV."""

    csv_decimal_point: str = "."
    """The decimal point to be used in the CSV."""

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
    """List of enabled CSV fields from left to right."""

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
        csv.CsvField.BDBR_VMAF: "BD-BR (VMAF)",
        csv.CsvField.BITRATE_ERROR: "Bitrate error",
        csv.CsvField.CONFORMANCE: "Conforming bitstream",
        csv.CsvField.PSNR_CURVE_CROSSINGS: "PSNR curves cross",
        csv.CsvField.SSIM_CURVE_CROSSINGS: "SSIM curves cross",
        csv.CsvField.VMAF_CURVE_CROSSINGS: "VMAF curves cross",
        csv.CsvField.RATE_OVERLAP: "Rate overlap",
        csv.CsvField.PSNR_OVERLAP: "PSNR overlap",
        csv.CsvField.SSIM_OVERLAP: "SSIM overlap",
        csv.CsvField.VMAF_OVERLAP: "VMAF overlap",
    }
    """Key = CSV field ID, value = CSV field name."""

    csv_float_rounding_accuracy: int = 6
    """The accuracy with which floats are rounded when generating the output CSV."""

    ##########################################################################
    # Table
    ##########################################################################

    table_enabled_columns: list = [
        table.TableColumns.VIDEO,
        table.TableColumns.PSNR_BDBR,
        table.TableColumns.SSIM_BDBR,
        table.TableColumns.VMAF_BDBR,
        table.TableColumns.SPEEDUP,
    ]
    """List of enabled columns from left to right"""

    table_column_headers: dict = {
        table.TableColumns.VIDEO: "Video",
        table.TableColumns.PSNR_BDBR: "BD-BR (PSNR)",
        table.TableColumns.SSIM_BDBR: "BD-BR (SSIM)",
        table.TableColumns.VMAF_BDBR: "BD-BR (VMAF)",
        table.TableColumns.SPEEDUP: "Speedup",
    }
    """Header values for the table columns"""

    table_column_formats = {
        table.TableColumns.VIDEO: lambda x: x,
        table.TableColumns.PSNR_BDBR: lambda x: f"{x * 100:.1f}%",
        table.TableColumns.SSIM_BDBR: lambda x: f"{x * 100:.1f}%",
        table.TableColumns.VMAF_BDBR: lambda x: f"{x * 100:.1f}%",
        table.TableColumns.SPEEDUP: lambda x: f"{x:.2f}×",
    }
    """How the column values should be formatted"""

    _wkhtmltopdf_path = None

    @property
    def wkhtmltopdf(self) -> Path:
        """Path to the the wkhtmltopdf executable"""
        return Path(self._wkhtmltopdf_path or "wkhtmltopdf")

    @wkhtmltopdf.setter
    def wkhtmltopdf(self, value):
        self._wkhtmltopdf_path = value

    ##########################################################################
    # RD Plots
    ##########################################################################

    colors = [
        "xkcd:black",
        "xkcd:red",
        "xkcd:blue",
        "xkcd:green",
        "xkcd:cyan",
        "xkcd:magenta",
        "xkcd:yellow",
        "xkcd:pink",
        "xkcd:brown",
        "xkcd:bright purple",
        "xkcd:indigo",
        "xkcd:dark teal",
        "xkcd:crimson",
        "xkcd:apple green",
        "xkcd:bluish green",
    ]
    """List of colors used for the curves in the RD plots.
     Order is same as for the order where Tests are passed to create context"""

    include_bitrate_targets = True
    """When bitrate or derivative is used as quality_param whether they are depicted in the figures"""

    graph_enabled_metrics = [
        graphs.GraphMetrics.PSNR,
        graphs.GraphMetrics.SSIM,
        graphs.GraphMetrics.VMAF,
    ]
    """Which subfigures are included"""

    ##########################################################################
    # General
    ##########################################################################

    frame_step_size: int = 1
    """Determines that only every nth frame is encoded.
    In case the encoder has built in feature for this the tester will assert that the value here is the same as
    what the encoder set value is."""

    overwrite_encoding: ReEncoding = ReEncoding.OFF
    """
    Whether re-encode encodings that are not necessary to encode:
    OFF: Encode sequences only if results do not exist.
    SOFT: Encode if the encoding is missing regardless of whether results exists. 
        This should be used if the previous encoding didn't include all necessary metrics.
    FORCE: Always re-encode 
    """

    remove_encodings_after_metric_calculation: bool = False
    """
    Should the encoded videos be removed after calculating metrics.
    Heavily recommended to call `Tester.calculate_metrics()` explicitly if this is True
    """

    ##########################################################################
    # HEVC
    ##########################################################################

    _hevc_reference_decoder = ""

    @property
    def hevc_reference_decoder(self) -> Path:
        return Path(self._hevc_reference_decoder)

    @hevc_reference_decoder.setter
    def hevc_reference_decoder(self, value):
        self._hevc_reference_decoder = value

    ##########################################################################
    # HM
    ##########################################################################

    hm_remote_url: str = "https://vcgit.hhi.fraunhofer.de/jct-vc/HM.git"
    """The remote from which HM will be cloned."""

    ##########################################################################
    # Kvazaar
    ##########################################################################

    kvazaar_remote_url: str = "git@gitlab.tut.fi:TIE/ultravideo/kvazaar.git"
    """The remote from which Kvazaar will be cloned."""

    ##########################################################################
    # x265
    ##########################################################################

    x265_remote_url: str = "https://bitbucket.org/multicoreware/x265_git.git"
    """The remote from which x265 will be cloned."""
    x265_build_folder: str = "vc15-x86_64"
    """The windows build folder for x265"""
    _nasm_path: str = ""

    @property
    def nasm_path(self):
        """Path to the nasm executable, should be set for Windows since it's unlikely to be auto detected"""
        return self._nasm_path or "nasm"

    @nasm_path.setter
    def nasm_path(self, value):
        self._nasm_path = value

    ##########################################################################
    # Visual Studio
    ##########################################################################

    _vs_install_path: Union[str, Path] = Path("C:/") / "Program Files (x86)" / "Microsoft Visual Studio"
    """The Visual Studio base installation directory."""

    @property
    def vs_install_path(self) -> Path:
        """The Visual Studio base installation directory."""
        return Path(self._vs_install_path).resolve()

    @vs_install_path.setter
    def vs_install_path(self, value: Union[str, Path]):
        self._vs_install_path = value

    vs_year_version: str = None
    """The release year of the Visual Studio version in use (for example 2019 for VS 2019).
    Must be set by the user."""

    vs_major_version: str = None
    """The version of Visual Studio in use (for example VS 2019 is version 16).
    Must be set by the user."""

    vs_edition: str = None
    """The edition of Visual Studio in use (Community/Professional/Enterprise).
    Must be set by the user."""

    vs_msvc_version: str = None
    """The version of MSVC in use (for example 19.26). Can be checked with 'cl /version' on the
    command line. Must be set by the user."""

    vs_msbuild_platformtoolset: str = None
    """The /p:PlatformToolset parameter to be passed to MSBuild."""

    vs_msbuild_windowstargetplatformversion: str = "10.0"
    """The /p:WindowsTargetPlatformVersion parameter to be passed to MSBuild.
    In older visual studios (2017 etc.) need to specify the exact version i.e. 10.0.xxxxx.x"""

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

    _vtm_cfg_file_path: Union[str, Path] = None
    """The path of the VTM configuration file. Must be set by the user."""
