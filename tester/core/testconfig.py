#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""This module defines functionality related to test configurations. A test configuration is
essentially a combination of encoder version and encoding parameters."""

from tester.core.videosequence import *
from tester.core.metrics import *
import tester.encoders.kvazaar

import hashlib


class TestConfig:
    """Represents a test configuration. A test configuration is the combination of
    an encoder binary and sets of encoding parameters (one set for each value of the quality
    parameter in use)."""

    def __init__(self,
                 name: str,
                 encoder_id: EncoderId,
                 encoder_revision: str,
                 encoder_defines: list,
                 anchor_names: list,
                 quality_param_type: QualityParamType,
                 quality_param_list: list,
                 cl_args: str,
                 seek: int = 0,
                 frames: int = 0):
        self._name = name
        self._encoder: EncoderBase = None
        self._anchor_names: list = anchor_names
        self._param_sets: list = []

        if encoder_id == EncoderId.KVAZAAR:
            self._encoder = tester.encoders.kvazaar.Kvazaar(encoder_revision, encoder_defines)
            self._param_sets = [
                tester.encoders.kvazaar.KvazaarParamSet(
                    quality_param_type,
                    quality_param_value,
                    seek,
                    frames,
                    cl_args
                ) for quality_param_value in quality_param_list
            ]
        else:
            console_logger.error(f"TestConfig: '{self._name}': Unknown encoder '{self._encoder}'")
            raise RuntimeError

    def __eq__(self,
               other) -> bool:
        return self._name == other.get_short_name() \
               and self._encoder == other.get_encoder() \
               and self._anchor_names == other.get_anchor_names() \
               and self._param_sets == other.param_sets

    def __hash__(self) -> int:
        return int(hashlib.md5(self._name.encode()).hexdigest(), 16)

    def get_short_name(self) -> str:
        return self._name

    def get_long_name(self,
                      param_set: ParamSetBase) -> str:
        return f"{self._name}\\{param_set.get_quality_param_name()}{param_set.get_quality_param_value()}"

    def get_encoder(self) -> EncoderBase:
        return self._encoder

    def get_anchor_names(self) -> list:
        return self._anchor_names

    def get_param_sets(self) -> list:
        return self._param_sets

    def get_metrics(self,
                    sequence: VideoSequence) -> Metrics:
        return Metrics(
            self._encoder,
            self._param_sets,
            sequence
        )
