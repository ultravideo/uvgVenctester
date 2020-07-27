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
        return self._encoder == other._encoder and self._param_set == other._param_set

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

        # Order quality parameters in ascending order by resulting bitrate,
        # since that is the order in which the results have to be when BD-BR is computed.
        if quality_param_type == QualityParamType.QP:
            quality_param_list = sorted(quality_param_list, reverse=True)
        elif quality_param_type == QualityParamType.BITRATE:
            quality_param_list = sorted(quality_param_list)

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

    def clone(self,
              name: str = None,
              encoder_id: EncoderId = None,
              encoder_revision: str = None,
              encoder_defines: list = None,
              anchor_names: list = None,
              quality_param_type: QualityParamType = None,
              quality_param_list: list = None,
              cl_args: str = None,
              seek: int = None,
              frames: int = None
              ) -> Test:

        if name is None:
            name = self._name
        if encoder_id is None:
            encoder_id = self._encoder.get_id()
        if encoder_revision is None:
            encoder_revision = self._encoder.get_user_given_revision()
        if encoder_defines is None:
            encoder_defines = self._encoder.get_defines()
        if anchor_names is None:
            anchor_names = self._anchor_names
        if quality_param_type is None:
            quality_param_type = self._subtests[0].get_param_set().get_quality_param_type()
        if quality_param_list is None:
            quality_param_list = [subtest.get_param_set().get_quality_param_value() for subtest in self._subtests]
        if cl_args is None:
            cl_args = self._subtests[0].get_param_set().get_cl_args()
        if seek is None:
            seek = self._subtests[0].get_param_set().get_seek()
        if frames is None:
            frames = self._subtests[0].get_param_set().get_frames()

        return Test(
            name,
            encoder_id,
            encoder_revision,
            encoder_defines,
            anchor_names,
            quality_param_type,
            quality_param_list,
            cl_args,
            seek,
            frames
        )

    def get_subtests(self) -> list:
        return self._subtests

    def get_name(self) -> str:
        return self._name

    def get_encoder(self) -> EncoderBase:
        return self._encoder

    def get_anchor_names(self) -> list:
        return self._anchor_names

    def get_metrics(self,
                    input_sequence: RawVideoSequence) -> TestMetrics:
        return TestMetrics(
            [subtest.get_metrics(input_sequence) for subtest in self._subtests],
            input_sequence
        )
