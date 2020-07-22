#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""This module defines generic functionality related to encoders."""

from __future__ import annotations

import tester.core.videosequence
from tester.core.cfg import *
from tester.core.git import *
from tester.core.log import *

import hashlib
import shutil
from enum import Enum
from pathlib import Path


class EncoderId(Enum):
    """An enumeration to identify different encoders."""

    NONE: int = 0
    KVAZAAR: int = 1

    def __str__(self):
        """Returns the name of the encoder."""
        if self == EncoderId.KVAZAAR:
            return "Kvazaar"
        else:
            raise RuntimeError


class QualityParamType(Enum):
    """An enumeration to identify all the different quality parameter types."""

    NONE: int = 0
    QP: int = 1
    BITRATE: int = 2

    def __str__(self):
        """Returns the name of the quality parameter."""
        if self == QualityParamType.QP:
            return "QP"
        elif self == QualityParamType.BITRATE:
            return "bitrate"
        else:
            raise RuntimeError

    def is_valid(self) -> bool:
        VALID_LIST: list = [
            self.QP,
            self.BITRATE
        ]
        return self in VALID_LIST


class ParamSetBase():
    """An interface representing a set of parameters to be passed to an encoder when encoding.
    The purpose of the class is to provide an interface through which the parameter sets
    of different encoders can be used in a generic manner. Each encoder must implement an
    encoder-specific subclass."""

    def __init__(self,
                 quality_param_type: QualityParamType,
                 quality_param_value: int,
                 seek: int,
                 frames: int,
                 cl_args: str):

        if not quality_param_type.is_valid():
            console_logger.error(f"ParamSetBase: Invalid quality_param_type "
                                 f"'{str(quality_param_type)}'")
            raise RuntimeError

        self._quality_param_type: QualityParamType = quality_param_type
        self._quality_param_value: int = quality_param_value
        self._seek = seek
        self._frames = frames
        self._cl_args: str = cl_args

    def __eq__(self,
               other: ParamSetBase):
        return type(self) == type(other)\
               and self.to_cmdline_str() == other.to_cmdline_str()

    def __hash__(self):
        return hashlib.md5(self._quality_param_type)\
               + hashlib.md5(self._quality_param_value)\
               + hashlib.md5(self._cl_args.encode())

    def get_quality_param_type(self) -> QualityParamType:
        return self._quality_param_type

    def get_quality_param_name(self) -> str:
        return str(self._quality_param_type)

    def get_quality_param_value(self) -> int:
        return self._quality_param_value

    def get_seek(self) -> int:
        return self._seek

    def get_frames(self) -> int:
        return self._frames

    def to_cmdline_tuple(self,
                         include_quality_param: bool = True) -> tuple:
        """Returns the command line arguments as a tuple.
        @param include_quality_param If False, the quality parameter argument is omitted."""
        raise NotImplementedError

    def to_cmdline_str(self,
                       include_quality_param: bool = True) -> str:
        """Returns the command line arguments as a string.
        @param include_quality_param If False, the quality parameter argument is omitted."""
        return " ".join(self.to_cmdline_tuple(include_quality_param))


class EncoderBase:
    """An interface representing an encoder. Each encoder module must implement a class that
    inherits this class. The purpose of the class is to provide an interface through
    which the tester can interact with each encoder in a generic manner."""

    def __init__(self,
                 id: EncoderId,
                 user_given_revision: str,
                 defines: list,
                 git_repo_path: Path,
                 git_repo_ssh_url: str):

        self._id: EncoderId = id
        self._name: str = str(id)
        self._user_given_revision: str = user_given_revision
        self._defines: list = defines
        self._define_hash: str = hashlib.md5(str(defines).encode()).digest().hex()
        self._define_hash_short: str = self._define_hash[:Cfg().short_define_hash_len]
        self._git_local_path: Path = git_repo_path
        self._git_ssh_url: str = git_repo_ssh_url

        self._git_repo: GitRepository = GitRepository(git_repo_path)

        self._exe_name: str = ""
        self._exe_path: Path = Path("")
        self._commit_hash: str = ""
        self._commit_hash_short: str = ""
        self._build_log_name: str = ""
        self._build_log_path: Path = Path("")
        # Initializes the above.
        self.prepare_sources()

        # This must be set in the constructor of derived classes.
        self._exe_src_path: Path = Path("")

        # This is set when build() is called.
        self._build_log: logging.Logger = None

        console_logger.debug(f"{self._name}: Initialized object:")
        for attribute_name in sorted(self.__dict__):
            console_logger.debug(f"{self._name}: {attribute_name} = '{getattr(self, attribute_name)}'")

    def __eq__(self,
               other: EncoderBase) -> bool:
        assert isinstance(other, EncoderBase)
        return self._id == other._id\
               and self._commit_hash == other._commit_hash\
               and self._define_hash == other._define_hash

    def __hash__(self) -> int:
        return hashlib.md5(self._name)\
               + hashlib.md5(self._commit_hash)\
               + hashlib.md5(self._define_hash)

    def get_name(self) -> str:
        return self._name

    def get_exe_path(self) -> Path:
        return self._exe_path

    def get_exe_src_path(self) -> Path:
        return self._exe_src_path

    def get_id(self) -> EncoderId:
        return self._id

    def get_defines(self) -> list:
        return self._defines

    def get_user_given_revision(self) -> str:
        return self._user_given_revision

    def get_revision(self) -> str:
        return self._commit_hash

    def get_short_revision(self) -> str:
        return self._commit_hash_short

    def get_output_base_dir(self) -> Path:
        return Cfg().encoding_output_dir_path / self._exe_name.strip(".exe")

    def get_output_subdir(self,
                          param_set: ParamSetBase) -> Path:
        return self.get_output_base_dir() / param_set.to_cmdline_str(include_quality_param=False)

    def get_output_filename(self,
                            input_sequence: tester.core.videosequence,
                            param_set: ParamSetBase) -> str:
        qp_name = param_set.get_quality_param_name()
        qp_value = param_set.get_quality_param_value()
        base_filename = f"{input_sequence.get_input_filename(include_extension=False)}"
        output_filename = f"{base_filename}_{qp_name.lower()}{qp_value}.hevc"
        return output_filename

    def get_output_filepath(self,
                            input_sequence: tester.core.videosequence,
                            param_set: ParamSetBase) -> Path:
        output_filename = self.get_output_filename(input_sequence, param_set)
        output_filepath = self.get_output_subdir(param_set) / output_filename
        return output_filepath

    def get_encoding_log_filename(self,
                                  input_sequence: tester.core.videosequence,
                                  param_set: ParamSetBase) -> str:
        return self.get_output_filename(input_sequence, param_set).strip(".hevc") + "_encoding_log.txt"

    def get_encoding_log_filepath(self,
                                  input_sequence: tester.core.videosequence,
                                  param_set: ParamSetBase) -> Path:
        return Path(str(self.get_output_filepath(input_sequence, param_set)).strip(".hevc") + "_encoding_log.txt")

    def prepare_sources(self) -> None:
        console_logger.info(f"{self._name}: Preparing sources")
        console_logger.info(f"{self._name}: Repository: '{self._git_repo.local_repo_path}'")
        console_logger.info(f"{self._name}: Revision: '{self._user_given_revision}'")

        # Clone the remote if the local repo doesn't exist yet.
        if not self._git_local_path.exists():
            cmd_str, output, exception = self._git_repo.clone(self._git_ssh_url)
            if not exception:
                pass
            else:
                console_logger.error(cmd_str)
                console_logger.error(exception.output.decode())
                raise exception
        else:
            console_logger.info(f"{self._name}: Repository '{self._git_local_path}' "
                                f"already exists")

        # Convert the user-given revision into the actual full revision.
        cmd, output, exception = self._git_repo.rev_parse(self._user_given_revision)
        if not exception:
            self._commit_hash = output.decode().strip()
        else:
            console_logger.error(f"{self._name}: Invalid revision '{self._user_given_revision}'")
            raise exception

        # These can now be evaluated because the repo exists for certain.
        self._commit_hash_short = self._commit_hash[:Cfg().short_commit_hash_len]
        self._exe_name = f"{self._name.lower()}_{self._commit_hash_short}_{self._define_hash_short}"\
                        f"{'.exe' if Cfg().os_name == 'Windows' else ''}"
        self._exe_path = Cfg().binaries_dir_path / self._exe_name
        self._build_log_name = f"{self._name.lower()}_{self._commit_hash_short}_{self._define_hash_short}_build_log.txt"
        self._build_log_path = Cfg().binaries_dir_path / self._build_log_name

        console_logger.info(f"{self._name}: Revision '{self._user_given_revision}' "
                            f"maps to commit hash '{self._commit_hash}'")

    def build(self) -> None:
        """Builds the executable."""
        raise NotImplementedError

    def build_start(self) -> bool:
        """Meant to be called as the first thing from the build() method of derived classes."""
        assert Cfg().binaries_dir_path.exists()

        console_logger.info(f"{self._name}: Building executable '{self._exe_name}'")
        console_logger.info(f"{self._name}: Log: '{self._build_log_name}'")

        if (self._exe_path.exists()):
            console_logger.info(f"{self._name}: Executable '{self._exe_name}' already exists")
            # Don't build unnecessarily.
            return False

        self._build_log = setup_build_log(self._build_log_path)

        # Checkout to the desired version.
        cmd_str, output, exception = self._git_repo.checkout(self._commit_hash)
        if not exception:
            self._build_log.info(cmd_str)
            self._build_log.info(output.decode())
        else:
            self._build_log.info(cmd_str)
            self._build_log.info(exception.output.decode())
            console_logger.error(exception.output.decode())
            raise exception

        # Do build.
        return True

    def build_finish(self,
                     build_cmd: tuple) -> None:
        """Meant to be called as the last thing from the build() method of derived classes."""

        assert self._exe_src_path

        # Build the executable.
        self._build_log.info(subprocess.list2cmdline(build_cmd))
        try:
            output = subprocess.check_output(
                build_cmd,
                shell=True,
                stderr=subprocess.STDOUT
            )
            if Cfg().os_name == "Windows":
                # "cp1252" is the encoding the Windows shell uses.
                self._build_log.info(output.decode(encoding="cp1252"))
            else:
                self._build_log.info(output.decode())
        except subprocess.CalledProcessError as exception:
            console_logger.error(exception.output.decode())
            self._build_log.error(exception.output.decode())
            raise

        # Copy the executable to its destination.
        assert self._exe_src_path.exists()
        self._build_log.debug(f"{self._name}: Copying file '{self._exe_src_path}' "
                              f"to '{self._exe_path}'")
        try:
            shutil.copy(str(self._exe_src_path), str(self._exe_path))

        except FileNotFoundError as exception:
            console_logger.error(str(exception))
            self._build_log.error(str(exception))
            raise

    def clean(self) -> None:
        """Runs make clean or similar."""
        raise NotImplementedError

    def clean_start(self) -> None:
        """Meant to be called as the first thing from the clean() method of derived classes."""
        console_logger.info(f"{self._name}: Cleaning build artifacts")

    def clean_finish(self, clean_cmd: tuple) -> None:
        """Meant to be called as the last thing from the clean() method of derived classes."""
        try:
            subprocess.check_output(
                subprocess.list2cmdline(clean_cmd),
                shell=True,
                stderr=subprocess.STDOUT
            )
        except subprocess.CalledProcessError as exception:
            console_logger.error(exception.output.decode())
            raise

    def dummy_run(self,
                  param_set: ParamSetBase) -> bool:
        """Performs a dummy run to validate the set of parameters before any actual encoding runs."""
        raise NotImplementedError

    def dummy_run_start(self,
                        param_set: ParamSetBase) -> bool:
        """Meant to be called as the first thing from the dummy_run() method of derived classes."""
        console_logger.debug(f"{self._name}: Validating arguments: '{param_set.to_cmdline_str()}'")
        return True

    def dummy_run_finish(self,
                         dummy_cmd: tuple,
                         param_set: ParamSetBase) -> bool:
        """Meant to be called as the last thing from the dummy_run() method of derived classes."""
        try:
            subprocess.check_output(
                dummy_cmd,
                stderr=subprocess.STDOUT
            )
        except subprocess.CalledProcessError as exception:
            console_logger.error(f"{self._name}: Invalid arguments: "
                                 f"'{param_set.to_cmdline_str()}'")
            console_logger.error(exception.output.decode().strip())
            return False
        return True

    def encode(self,
               input_sequence: tester.core.videosequence,
               param_set: ParamSetBase) -> None:
        """Encodes the given sequence with the given set of parameters."""
        raise NotImplementedError

    def encode_start(self,
                     input_sequence: tester.core.videosequence,
                     param_set: ParamSetBase) -> (str, str):
        """Meant to be called as the first thing from the encode() method of derived classes."""

        console_logger.debug(f"{self._name}: Encoding file '{input_sequence.get_input_filename()}'")

        output_filepath = self.get_output_filepath(input_sequence, param_set)
        output_filename = self.get_output_filename(input_sequence, param_set)
        output_dir = Path(output_filepath.parent)

        console_logger.debug(f"{self._name}: Output: '{output_filename}'")
        console_logger.debug(f"{self._name}: Arguments: '{param_set.to_cmdline_str()}'")

        encoding_log_filepath = self.get_encoding_log_filepath(input_sequence, param_set)
        encoding_log_filename = self.get_encoding_log_filename(input_sequence, param_set)
        console_logger.debug(f"{self._name}: Log: '{encoding_log_filename}'")

        if output_filepath.exists():
            console_logger.info(f"{self._name}: File '{output_filename}' already exists")
            return None, None

        if not output_dir.exists():
            output_dir.mkdir(parents=True)

        return output_filepath, encoding_log_filepath

    def encode_finish(self,
                      encode_cmd: tuple,
                      input_sequence: tester.core.videosequence,
                      param_set: ParamSetBase) -> None:
        """Meant to be called as the last thing from the encode() method of derived classes."""
        try:
            output = subprocess.check_output(
                encode_cmd,
                stderr=subprocess.STDOUT
            )
            with self.get_encoding_log_filepath(input_sequence, param_set).open("w") as encoding_log:
                encoding_log.write(output.decode())
        except subprocess.CalledProcessError as exception:
            console_logger.error(f"{self._name}: Encoding failed "
                                 f"(input: '{input_sequence.input_filepath()}', "
                                 f"output: '{self.get_output_filepath(input_sequence, param_set)}')")
            console_logger.error(exception.output.decode().strip())
            raise
