#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""This module defines functionality related to test configurations. A test configuration is
essentially a combination of encoder version and encoding parameters."""

from .log import console_logger
from .encodingparamsetbase import *
from .metrics import *
from .videosequence import *
from encoders import kvazaar

from enum import Enum
import hashlib

class EncoderId(Enum):
    """An enumeration to identify different encoders."""
    NONE: int = 0
    KVAZAAR: int = 1


class TestConfig:
    """Represents a test configuration. A test configuration is the combination of
    an encoder binary and sets of encoding parameters (one set for each value of the quality
    parameter in use)."""
    def __init__(self,
                 name: str,
                 quality_param_type: QualityParamType,
                 quality_param_list: list,
                 cl_args: str,
                 encoder_id: EncoderId,
                 encoder_revision: str,
                 encoder_defines: list,
                 anchor_names: list):
        self.name = name
        self.encoder: EncoderInstanceBase = None
        self.anchor_names: list = anchor_names
        self.param_sets: list = []

        if encoder_id == EncoderId.KVAZAAR:
            self.encoder = kvazaar.EncoderInstance(encoder_revision, encoder_defines)
            self.param_sets = [
                kvazaar.EncodingParamSet(quality_param_type, quality_param_value, cl_args)
                    for quality_param_value in quality_param_list
            ]
        else:
            console_logger.error(f"TestConfig: '{self.name}': Unknown encoder '{self.encoder}'")
            raise RuntimeError

    def __eq__(self, other):
        return self.name == other.get_short_name() \
               and self.encoder == other.get_encoder() \
               and self.anchor_names == other.get_anchor_names() \
               and self.param_sets == other.param_sets

    def __hash__(self):
        return int(hashlib.md5(self.name.encode()).hexdigest(), 16)

    def get_short_name(self):
        return self.name

    def get_long_name(self, param_set: EncodingParamSetBase):
        return f"{self.name}\\{param_set.get_quality_param_name()}{param_set.get_quality_param_value()}"

    def get_encoder(self):
        return self.encoder

    def get_anchor_names(self):
        return self.anchor_names

    def get_param_sets(self):
        return self.param_sets

    def get_metrics(self, sequence: VideoSequence):
        return Metrics(
            self.encoder,
            self.param_sets,
            sequence
        )
