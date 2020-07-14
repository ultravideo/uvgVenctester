#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""This module defines the EncoderInstanceBase class meant to be an interface through which the
tester interacts with each encoder."""

from .encodingparamsetbase import *

class EncoderInstanceBase:
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

    def get_user_revision(self) -> str:
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

    def get_output_subdir(self, param_set: EncodingParamSetBase) -> str:
        """Returns the subdirectory (within the base directory) in which video files encoded with
        the given parameter set will be placed.
        @param param_set The set of parameters to be used in the encoding."""
        raise NotImplementedError

    def build(self):
        """Builds the executable."""
        raise NotImplementedError

    def dummy_run(self, param_set: EncodingParamSetBase) -> bool:
        """Executes a dummy run to validate command line arguments before any actual encoding runs.
        @param param_set The set of parameters to be used in the encoding."""
        raise NotImplementedError

    # Input_sequence should be of type VideoSequence, but there was a circular import issue.
    def encode(self, input_sequence, param_set: EncodingParamSetBase):
        """Encodes the given sequence with the given parameter set.
        @param input_sequence The sequence to encode.
        @param param_set The set of parameters to be used in the encoding."""
        raise NotImplementedError
