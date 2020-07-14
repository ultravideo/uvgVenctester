#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""This module defines the EncodingParamSetBase class."""

from enum import Enum


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


class EncodingParamSetBase():
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
