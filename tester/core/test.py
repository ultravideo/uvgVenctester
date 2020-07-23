"""This module defines functionality related to test configurations."""

from __future__ import annotations

from tester.core.metrics import *
import tester.encoders.kvazaar

import hashlib


class SubTest:
    """Represents a subtest. A single test consists of multiple subtests."""

    def __init__(self,
                 name: str,
                 index: int,
                 encoder: EncoderBase,
                 param_set: ParamSetBase):

        self._name = name
        self._index = index
        self._encoder = encoder
        self._param_set = param_set

    def __eq__(self, other: SubTest):
        return self._encoder == other.get_encoder and self._param_set == other._param_set

    def __hash__(self):
        return hashlib.md5(self._name.encode())

    def get_name(self) -> str:
        return self._name

    def get_index(self) -> int:
        return self._index

    def get_encoder(self) -> EncoderBase:
        return self._encoder

    def get_param_set(self) -> ParamSetBase:
        return self._param_set

    def get_metrics(self,
                    input_sequence: RawVideoSequence) -> SubTestMetrics:
        return SubTestMetrics(
            input_sequence,
            self._encoder.get_output_file(input_sequence, self._param_set)
        )


class Test:
    """Represents a test. A single test consists of as many subtests as there are different
    quality parameter values. (Therefore a subtest is basically a unique set of encoding
    parameters.)"""

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

        param_sets = []

        if encoder_id == EncoderId.KVAZAAR:
            self._encoder = tester.encoders.kvazaar.Kvazaar(encoder_revision, encoder_defines)
            param_sets = [
                tester.encoders.kvazaar.KvazaarParamSet(
                    quality_param_type,
                    quality_param_value,
                    seek,
                    frames,
                    cl_args
                ) for quality_param_value in quality_param_list
            ]

        self._subtests = [
            SubTest(
                f"{name} ({param_set.get_quality_param_name()}: {param_set.get_quality_param_value()})",
                index,
                self._encoder,
                param_set
            ) for index, param_set in enumerate(param_sets)
        ]

    def __eq__(self,
               other: Test):
        for subtest1 in self._subtests:
            for subtest2 in other._subtests:
                if subtest1 != subtest2:
                    return False
        return self._name == other.get_name() \
               and self._encoder == other.get_encoder()

    def __hash__(self):
        return int(hashlib.md5(self._name.encode()).hexdigest(), 16)

    def get_subtests(self) -> list:
        return self._subtests

    def get_name(self) -> str:
        return self._name

    def get_encoder(self) -> EncoderBase:
        return self._encoder

    def get_anchor_names(self) -> list:
        return self._anchor_names

    def get_metrics(self,
                    sequence: RawVideoSequence) -> TestMetrics:
        return TestMetrics(
            [subtest.get_metrics(sequence) for subtest in self._subtests],
            sequence
        )
