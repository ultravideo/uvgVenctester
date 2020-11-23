"""This module defines functionality related to test configurations."""

from __future__ import annotations

from hashlib import md5
from math import sqrt
from pathlib import Path
from typing import Iterable

import tester.encoders as encoders
import tester.core.metrics as met
from tester.core.video import RawVideoSequence, EncodedVideoFile
from tester.encoders.base import QualityParam


class EncodingRun:

    def __init__(self,
                 parent: SubTest = None,
                 name: str = None,
                 round_number: int = None,
                 encoder: encoders.EncoderBase = None,
                 param_set: encoders.EncoderBase.ParamSet = None,
                 input_sequence: RawVideoSequence = None):

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

        base_filename = f"{input_sequence.get_filepath().with_suffix('').name}_" \
                        f"{qp_name}{self.param_set.get_quality_param_value()}_{round_number}"
        output_dir_path = encoder.get_output_dir(param_set)

        self.encoding_log_path: Path = output_dir_path / f"{base_filename}_encoding_log.txt"
        self.metrics_path: Path = output_dir_path / f"{base_filename}_metrics.json"
        self.psnr_log_path: Path = output_dir_path / f"{base_filename}_psnr_log.txt"
        self.ssim_log_path: Path = output_dir_path / f"{base_filename}_ssim_log.txt"
        self.vmaf_log_path: Path = output_dir_path / f"{base_filename}_vmaf_log.txt"

        output_file_path: Path = output_dir_path / f"{base_filename}.{encoder.file_suffix}"
        self.output_file = EncodedVideoFile(
            filepath=output_file_path,
            width=input_sequence.get_width(),
            height=input_sequence.get_height(),
            framerate=input_sequence.get_framerate(),
            frames=self.frames,
            duration_seconds=input_sequence.get_duration_seconds()
        )

        self.metrics = met.EncodingRunMetrics(self.metrics_path)

        self.decoded_output_file_path: Path = None
        if type(encoder) == encoders.Vtm:
            self.decoded_output_file_path: Path = output_dir_path / f"{base_filename}_decoded.yuv"

    @property
    def needs_encoding(self):
        return not self.output_file.get_filepath().exists() and "encoding_time"  not in self.metrics

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

        self.subtests: list = None

        # HM and VTM only encode every nth frame if --TemporalSubsampleRatio is specified
        # (in the config file).

        # Order quality parameters in ascending order by resulting bitrate,
        # since that is the order in which the results have to be when BD-BR is computed.
        if quality_param_type in [QualityParam.QP, QualityParam.CRF]:
            quality_param_list = sorted(quality_param_list, reverse=True)
        elif quality_param_type in [QualityParam.RES_ROOT_SCALED_BITRATE, QualityParam.RES_SCALED_BITRATE,
                                    QualityParam.BPP, QualityParam.BITRATE]:
            quality_param_list = sorted(quality_param_list)

        param_sets = [
            self.encoder.ParamSet(quality_param_type,
                             quality_param_value,
                             seek,
                             frames,
                             cl_args)
            for quality_param_value in quality_param_list
        ]

        self.subtests = []
        for param_set in param_sets:
            subtest = SubTest(
                self,
                f"{name}/{quality_param_type.short_name}{param_set.get_quality_param_value()}",
                self.encoder,
                param_set
            )
            self.subtests.append(subtest)

    def clone(self,
              **kwargs) -> Test:
        """Clones a Test object. Kwargs may contain parameter overrides for the constructor call."""

        defaults = {
            attribute_name: getattr(self, attribute_name) for attribute_name in self.__dict__
        }

        for attribute_name, attribute_value in kwargs.items():
            defaults[attribute_name] = attribute_value

        return Test(**defaults)

    def __eq__(self,
               other: Test):
        for i, subtest in enumerate(self.subtests):
            if other.subtests[i] != subtest:
                return False
        return self.encoder == other.encoder

    def __hash__(self):
        return sum(hash(subtest) for subtest in self.subtests)
