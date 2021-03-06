"""This module defines functionality related to test configurations."""

from __future__ import annotations

import os
from hashlib import md5
from math import sqrt
from pathlib import Path
from typing import Iterable

import tester.encoders as encoders
import tester.core.metrics as met
import tester.core.cfg as cfg
from tester.core.video import RawVideoSequence, EncodedVideoFile
from tester.encoders.base import QualityParam


class EncodingRun:

    def __init__(self,
                 parent: SubTest = None,
                 name: str = None,
                 round_number: int = None,
                 encoder: encoders.EncoderBase = None,
                 param_set: encoders.EncoderBase.ParamSet = None,
                 input_sequence: RawVideoSequence = None,):

        self.env = parent.parent.new_env
        self.parent: SubTest = parent
        self.name: str = name
        self.round_number: int = round_number
        self.encoder: encoders.EncoderBase = encoder
        self.param_set: encoders.EncoderBase.ParamSet = param_set
        self.input_sequence: RawVideoSequence = input_sequence
        self.frames = param_set.get_frames() or input_sequence.get_framecount(seek=param_set.get_seek())

        self.qp_name = param_set.get_quality_param_type()
        self.qp_value = param_set.get_quality_param_value()
        if self.qp_name == QualityParam.BPP:
            self.qp_value = self.qp_value * self.input_sequence._pixels_per_frame * self.input_sequence.get_framerate()
        elif self.qp_name == QualityParam.RES_SCALED_BITRATE:
            self.qp_value *= self.input_sequence.get_height() * self.input_sequence.get_width() / (1920 * 1080)
        elif self.qp_name == QualityParam.RES_ROOT_SCALED_BITRATE:
            self.qp_value *= sqrt(self.input_sequence.get_height() * self.input_sequence.get_width() / (1920 * 1080))

        qp_name = self.qp_name.short_name

        self.base_filename = f"{input_sequence.get_constructed_name()}_" \
                             f"{qp_name}{self.param_set.get_quality_param_value()}_{round_number}"
        self.output_dir_path = encoder.get_output_dir(param_set, parent.parent.env)

        self.metrics_path: Path = self.output_dir_path / f"{self.base_filename}_metrics.json"

        output_file_path: Path = self.output_dir_path / f"{self.base_filename}.{encoder.file_suffix}"
        self.output_file = EncodedVideoFile(
            filepath=output_file_path,
            width=input_sequence.get_width(),
            height=input_sequence.get_height(),
            framerate=input_sequence.get_framerate(),
            frames=self.frames,
            duration_seconds=input_sequence.get_duration_seconds()
        )

        if not output_file_path.parent.exists():
            output_file_path.parent.mkdir(parents=True)

        self.metrics = met.EncodingRunMetrics(self.metrics_path)

        self.decoded_output_file_path: [Path, None] = None
        if encoder.file_suffix == "vvc":
            self.decoded_output_file_path: Path = self.output_dir_path / f"{self.base_filename}_decoded.yuv"

    @property
    def needs_encoding(self):
        if cfg.Cfg().overwrite_encoding == cfg.ReEncoding.FORCE:
            return True
        elif cfg.Cfg().overwrite_encoding == cfg.ReEncoding.SOFT:
            return not self.output_file.get_filepath().exists() or "encoding_time" not in self.metrics
        elif cfg.Cfg().overwrite_encoding == cfg.ReEncoding.OFF:
            return (not self.output_file.get_filepath().exists() and not self.metrics.has_calculated_metrics) \
                   or "encoding_time" not in self.metrics

    def get_log_path(self, type_: str):
        return self.output_dir_path / f"{self.base_filename}_{type_}_log.txt"

    def __eq__(self,
               other: EncodingRun):
        return str(self.input_sequence.get_filepath()) == str(other.input_sequence.get_filepath()) \
               and str(self.output_file.get_filepath()) == str(other.output_file.get_filepath())

    def __hash__(self):
        return hash(self.input_sequence.get_filepath().name) + hash(self.output_file.get_filepath().name)

    def __str__(self):
        return f"{self.encoder.get_name()} {self.input_sequence} {self.param_set.get_cl_args()} {self.round_number}"


class SubTest:

    def __init__(self,
                 parent: Test,
                 name: str,
                 encoder: encoders.EncoderBase,
                 param_set: encoders.EncoderBase.ParamSet):
        self.parent: Test = parent
        self.name: str = name
        self.encoder: encoders.EncoderBase = encoder
        self.param_set: encoders.EncoderBase.ParamSet = param_set

    def __eq__(self,
               other: SubTest):
        return self.encoder == other.encoder and self.param_set == other.param_set

    def __hash__(self):
        return hash(self.encoder) + hash(self.param_set)


class Test:

    def __init__(self,
                 name: str,
                 encoder_type,
                 encoder_revision: str,
                 anchor_names: Iterable,
                 cl_args: str,
                 encoder_defines: Iterable = (),
                 quality_param_type: QualityParam = QualityParam.QP,
                 quality_param_list: Iterable = (22, 27, 32, 37),
                 seek: int = 0,
                 frames: int = None,
                 rounds: int = 1,
                 use_prebuilt=False,
                 env=None,
                 **kwargs):
        # Kwargs are ignored, they are here just to enable easy cloning.

        # Copy every parameter to make cloning easier.
        self.name: str = name
        self.encoder_type = encoder_type
        self.encoder: encoders.EncoderBase = self.encoder_type(encoder_revision, encoder_defines, use_prebuilt)
        self.encoder_revision: str = encoder_revision
        self.encoder_defines: Iterable = encoder_defines
        self.anchor_names: Iterable = anchor_names
        self.quality_param_type: QualityParam = quality_param_type
        self.quality_param_list: Iterable = quality_param_list
        self.cl_args: str = cl_args
        self.seek: int = seek or 0
        self.frames: int = frames
        self.rounds: int = rounds
        self.use_prebuilt = use_prebuilt
        if env is None:
            self.new_env = None
            self.env = None
        else:
            temp = dict(os.environ)
            temp.update(env)
            self.new_env = temp
            self.env = env.copy()

        self.subtests: list = []

        param_sets = [
            self.encoder.ParamSet(quality_param_type,
                                  quality_param_value,
                                  seek,
                                  frames,
                                  cl_args)
            for quality_param_value in quality_param_list
        ]

        for param_set in param_sets:
            subtest = SubTest(
                self,
                f"{name}/{quality_param_type.short_name}{param_set.get_quality_param_value()}",
                self.encoder,
                param_set
            )
            self.subtests.append(subtest)

    def clone(self,
              name: str,
              **kwargs) -> Test:
        """Clones a Test object. Kwargs may contain parameter overrides for the constructor call."""

        defaults = {
            attribute_name: getattr(self, attribute_name) for attribute_name in self.__dict__
        }

        defaults["name"] = name
        for attribute_name, attribute_value in kwargs.items():
            defaults[attribute_name] = attribute_value

        return Test(**defaults)

    def __eq__(self,
               other: Test):
        for own, other_ in zip(self.subtests, other.subtests):
            if other_ != own:
                return False
        return self.encoder == other.encoder and self.env == other.env

    def __hash__(self):
        return sum(hash(subtest) for subtest in self.subtests)
