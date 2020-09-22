"""This module defines functionality related to test configurations."""

from __future__ import annotations

from math import sqrt
from pathlib import Path
from typing import Iterable

import tester.encoders.hm as hm
import tester.encoders.kvazaar as kvazaar
import tester.encoders.vtm as vtm
from tester.core import metrics
from tester.core.cfg import Cfg
from tester.core.video import RawVideoSequence, EncodedVideoFile
from tester.encoders import EncoderBase, ParamSetBase, Encoder
from tester.encoders.base import QualityParam


class EncodingRun:

    def __init__(self,
                 parent: SubTest = None,
                 name: str = None,
                 round_number: int = None,
                 encoder: EncoderBase = None,
                 param_set: ParamSetBase = None,
                 input_sequence: RawVideoSequence = None):

        self.parent: SubTest = parent
        self.name: str = name
        self.round_number: int = round_number
        self.encoder: EncoderBase = encoder
        self.param_set: ParamSetBase = param_set
        self.input_sequence: RawVideoSequence = input_sequence
        self.frames = param_set.get_frames() or input_sequence.get_framecount()

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
                        f"{qp_name}{self.qp_value}_{round_number}"
        if not encoder._use_prebuilt:
            output_dir_path = Cfg().tester_output_dir_path \
                              / f"{encoder.get_name().lower()}_{encoder.get_short_revision()}_" \
                                f"{encoder.get_short_define_hash()}" \
                              / param_set.to_cmdline_str(include_quality_param=False, inode_safe=True)
        else:
            output_dir_path = Cfg().tester_output_dir_path \
                              / f"{encoder.get_name().lower()}_{encoder.get_revision()}" \
                              / param_set.to_cmdline_str(include_quality_param=False, inode_safe=True)

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
            frames=input_sequence.get_framecount(),
            duration_seconds=input_sequence.get_duration_seconds()
        )

        self.decoded_output_file_path: Path = None
        if encoder.get_id() == Encoder.VTM:
            self.decoded_output_file_path: Path = output_dir_path / f"{base_filename}_decoded.yuv"

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
                 encoder: EncoderBase,
                 param_set: ParamSetBase,
                 input_sequences: list,
                 rounds: int):

        self.parent: Test = parent
        self.name: str = name
        self.encoder: EncoderBase = encoder
        self.param_set: ParamSetBase = param_set
        self.sequences: list = input_sequences
        # Key: RawVideoSequence, value: EncodingRun
        self.encoding_runs: dict = {}

        for sequence in input_sequences:
            for round_number in range(1, rounds + 1):
                run = EncodingRun(
                    self,
                    f"{name}/{sequence.get_filepath().name} ({round_number}/{rounds})",
                    round_number,
                    encoder,
                    param_set,
                    sequence
                )
                if not sequence in self.encoding_runs.keys():
                    self.encoding_runs[sequence] = []
                self.encoding_runs[sequence].append(run)

    def __eq__(self,
               other: SubTest):
        return self.encoder == other.encoder and self.param_set == other.param_set

    def __hash__(self):
        return hash(self.encoder) + hash(self.param_set)


class Test:

    def __init__(self,
                 name: str,
                 encoder_id: Encoder,
                 encoder_revision: str,
                 anchor_names: Iterable,
                 cl_args: str,
                 input_sequences: Iterable,
                 encoder_defines: Iterable = (),
                 quality_param_type: QualityParam = QualityParam.QP,
                 quality_param_list: Iterable = (22, 27, 32, 37),
                 seek: int = None,
                 frames: int = None,
                 rounds: int = 1,
                 use_prebuilt=False,
                 **kwargs):
        # Kwargs are ignored, they are here just to enable easy cloning.

        # Copy every parameter to make cloning easier.
        self.name: str = name
        self.encoder_id: Encoder = encoder_id
        self.encoder_revision: str = encoder_revision
        self.encoder_defines: Iterable = encoder_defines
        self.anchor_names: Iterable = anchor_names
        self.quality_param_type: QualityParam = quality_param_type
        self.quality_param_list: Iterable = quality_param_list
        self.cl_args: str = cl_args
        self.input_sequences: Iterable = input_sequences
        self.seek: int = seek
        self.frames: int = frames
        self.rounds: int = rounds

        self.sequences: list = None
        self.encoder: EncoderBase = None
        self.subtests: list = None

        # Expand sequence globs.
        self.sequences = []

        # HM and VTM only encode every nth frame if --TemporalSubsampleRatio is specified
        # (in the config file).
        step = None
        if encoder_id == Encoder.HM:
            step = hm.hm_get_temporal_subsample_ratio()
        elif encoder_id == Encoder.VTM:
            step = vtm.vtm_get_temporal_subsample_ratio()

        for glob in input_sequences:
            for filepath in Cfg().tester_sequences_dir_path.glob(glob):
                self.sequences.append(
                    RawVideoSequence(
                        filepath,
                        seek=seek,
                        frames=frames,
                        step=step or 1
                    )
                )

        # Order quality parameters in ascending order by resulting bitrate,
        # since that is the order in which the results have to be when BD-BR is computed.
        if quality_param_type == QualityParam.QP:
            quality_param_list = sorted(quality_param_list, reverse=True)
        elif quality_param_type in [QualityParam.RES_ROOT_SCALED_BITRATE, QualityParam.RES_SCALED_BITRATE,
                                    QualityParam.BPP, QualityParam.BITRATE]:
            quality_param_list = sorted(quality_param_list)

        param_sets = []
        if encoder_id == Encoder.KVAZAAR:
            self.encoder = kvazaar.Kvazaar(encoder_revision, encoder_defines, use_prebuilt)
            param_sets = [
                kvazaar.KvazaarParamSet(
                    quality_param_type,
                    quality_param_value,
                    seek,
                    frames,
                    cl_args
                ) for quality_param_value in quality_param_list
            ]
        elif encoder_id == Encoder.HM:
            self.encoder = hm.Hm(encoder_revision, encoder_defines, use_prebuilt)
            param_sets = [
                hm.HmParamSet(
                    quality_param_type,
                    quality_param_value,
                    seek,
                    frames,
                    cl_args
                ) for quality_param_value in quality_param_list
            ]
        elif encoder_id == Encoder.VTM:
            self.encoder = vtm.Vtm(encoder_revision, encoder_defines, use_prebuilt)
            param_sets = [
                vtm.VtmParamSet(
                    quality_param_type,
                    quality_param_value,
                    seek,
                    frames,
                    cl_args
                ) for quality_param_value in quality_param_list
            ]
        else:
            raise RuntimeError

        self.subtests = []
        for param_set in param_sets:
            subtest = SubTest(
                self,
                f"{name}/{quality_param_type.short_name}{param_set.get_quality_param_value()}",
                self.encoder,
                param_set,
                self.sequences,
                rounds
            )
            self.subtests.append(subtest)

        self.metrics: metrics.TestMetrics = metrics.TestMetrics(self)

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
