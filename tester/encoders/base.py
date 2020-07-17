#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""This module defines generic functionality related to encoders."""

from enum import Enum


class EncoderId(Enum):
    """An enumeration to identify different encoders."""
    NONE: int = 0
    KVAZAAR: int = 1


class QualityParamType(Enum):
    """An enumeration to identify all the different quality parameter types."""
    NONE: int = 0
    QP: int = 1
    BITRATE: int = 2

    def __str__(self):
        """Returns the name of the quality parameter."""
        if self == QualityParamType.NONE:
            return ""
        elif self == QualityParamType.QP:
            return "QP"
        elif self == QualityParamType.BITRATE:
            return "bitrate"
        else:
            raise RuntimeError


class ParamSetBase():
    """An interface representing a set of parameters to be passed to an encoder when encoding.
    The purpose of the class is to provide an interface through which the parameter sets
    of different encoders can be used in a generic manner. Each encoder must implement an
    encoder-specific subclass."""

    def __init__(self,
                 quality_param_type: QualityParamType,
                 quality_param_value: int,
                 cl_args: str):
        self.quality_param_type: QualityParamType = quality_param_type
        self.quality_param_value: int = quality_param_value
        self.cl_args: str = cl_args

    def __eq__(self, other):
        return self.quality_param_type == other.get_quality_param_type()\
               and self.quality_param_value == other.get_quality_param_value()\
               and self.cl_args == other.get_cl_args()

    def get_quality_param_type(self) -> QualityParamType:
        """Returns the type of the quality parameter."""
        return self.quality_param_type

    def get_quality_param_name(self) -> str:
        """Returns the name of the quality parameter."""
        return str(self.quality_param_type)

    def get_quality_param_value(self) -> int:
        """Returns the value of the quality parameter."""
        return self.quality_param_value

    def get_cl_args(self) -> str:
        """Returns the command line arguments as a list."""
        return self.cl_args

    def to_cmdline_tuple(self) -> tuple:
        """Returns the command line arguments as a tuple."""
        # TODO: This will fail miserably if there are e.g. filepaths that contain whitespace.
        return tuple(self.to_cmdline_str().split())

    def to_cmdline_str(self, include_quality_param: bool = True) -> str:
        """Returns the command line arguments as a string.
        @param include_quality_param If False, the quality parameter argument is omitted."""
        raise NotImplementedError


class EncoderBase:
    """An interface representing an encoder. Each encoder module must implement a class that
    inherits this class. The purpose of the class is to provide an interface through
    which the tester can interact with each encoder in a generic manner."""

    def __init__(self):
        pass

    def __eq__(self, other):
        raise NotImplementedError

    def __hash__(self):
        raise NotImplementedError

    def get_exe_path(self) -> str:
        """Returns the absolute path in which the executable will be located once it has
        been built."""
        raise NotImplementedError

    def get_encoder_name(self) -> str:
        """Returns the name of the encoder. The form of the name is arbitrary, but preferably
        a single word."""
        raise NotImplementedError

    def get_defines(self) -> list:
        """Returns a list of the predefined preprocessor symbols to be used when
        compiling the encoder. The list must only contain strings."""
        raise NotImplementedError

    def get_user_given_revision(self) -> str:
        """Returns the (Git) revision as given by the user.
        Example: 'master' or 'a700f46'."""
        raise NotImplementedError

    def get_revision(self) -> str:
        """Returns the actual, full (Git) revision.
        Example: 'a700f469b968bbd670150a3cc74e54cbafab9650'."""
        raise NotImplementedError

    def get_short_revision(self) -> str:
        """Returns a shortened version of the full (Git) revision. The length is determined by
        a configuration variable.
        Example: 'a700f469b968bbd6'."""
        raise NotImplementedError

    def get_output_base_dir(self) -> str:
        """Returns the absolute path of the base directory in which encoded video files will
        be placed."""
        raise NotImplementedError

    def get_output_subdir(self, param_set: ParamSetBase) -> str:
        """Returns the subdirectory (within the base directory) in which video files encoded with
        the given parameter set will be placed.
        @param param_set The set of parameters to be used in the encoding."""
        raise NotImplementedError

    def build(self):
        """Builds the executable."""
        raise NotImplementedError

    def dummy_run(self, param_set: ParamSetBase) -> bool:
        """Executes a dummy run to validate command line arguments before any actual encoding runs.
        @param param_set The set of parameters to be used in the encoding."""
        raise NotImplementedError

    # Input_sequence should be of type VideoSequence, but there was a circular import issue.
    def encode(self, input_sequence, param_set: ParamSetBase):
        """Encodes the given sequence with the given parameter set.
        @param input_sequence The sequence to encode.
        @param param_set The set of parameters to be used in the encoding."""
        raise NotImplementedError
