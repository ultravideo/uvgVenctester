"""This module defines functionality related to test configurations."""

from __future__ import annotations

from tester.core.metrics import *
from tester.encoders.kvazaar import *


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

        qp_name = param_set.get_quality_param_type().short_name
        qp_value = param_set.get_quality_param_value()
        base_filename = f"{input_sequence.get_filepath().with_suffix('').name}_" \
                        f"{qp_name}{qp_value}_{round_number}"
        output_dir_path = Cfg().encoding_output_dir_path \
                          / f"{encoder.get_name()}_{encoder.get_short_revision()}_" \
                            f"{encoder.get_short_define_hash()}" \
                          / param_set.to_cmdline_str(include_quality_param=False)

        self.encoding_log_path: Path = output_dir_path / f"{base_filename}_encoding_log.txt"
        self.metrics_path: Path = output_dir_path / f"{base_filename}_metrics.json"
        self.psnr_log_path: Path = output_dir_path / f"{base_filename}_psnr_log.txt"
        self.ssim_log_path: Path = output_dir_path / f"{base_filename}_ssim_log.txt"
        self.vmaf_log_path: Path = output_dir_path / f"{base_filename}_vmaf_log.txt"

        self.output_file = HevcVideoFile(
            filepath=output_dir_path / f"{base_filename}.hevc",
            width=input_sequence.get_width(),
            height=input_sequence.get_height(),
            framerate=input_sequence.get_framerate(),
            framecount=input_sequence.get_framecount(),
            duration_seconds=input_sequence.get_duration_seconds()
        )

    def __eq__(self,
               other: EncodingRun):
        return str(self.input_sequence.get_filepath()) == str(other.input_sequence.get_filepath()) \
               and str(self.output_file.get_filepath()) == str(other.output_file.get_filepath())

    def __hash__(self):
        return hash(self.input_sequence.get_filepath().name) + hash(self.output_file.get_filepath().name)


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
                 encoder_defines: list,
                 anchor_names: list,
                 quality_param_type: QualityParam,
                 quality_param_list: list,
                 cl_args: str,
                 input_sequences: list,
                 seek: int = 0,
                 frames: int = 0,
                 rounds: int = 1,
                 **kwargs):
        # Kwargs are ignored, they are here just to enable easy cloning.

        # Copy every parameter to make cloning easier.
        self.name: str = name
        self.encoder_id: Encoder = encoder_id
        self.encoder_revision: str = encoder_revision
        self.encoder_defines: list = encoder_defines
        self.anchor_names: list = anchor_names
        self.quality_param_type: QualityParam = quality_param_type
        self.quality_param_list: list = quality_param_list
        self.cl_args: str = cl_args
        self.input_sequences: list = input_sequences
        self.seek: int = seek
        self.frames: int = frames
        self.rounds: int = rounds

        self.sequences: list = None
        self.encoder: EncoderBase = None
        self.subtests: list = None
        self.metrics: TestMetrics = TestMetrics(self)

        # Expand sequence globs.
        self.sequences = []
        for glob in input_sequences:
            for filepath in Cfg().sequences_dir_path.glob(glob):
                self.sequences.append(
                    RawVideoSequence(
                        filepath,
                        seek=seek,
                        frames=frames
                    )
                )

        # Order quality parameters in ascending order by resulting bitrate,
        # since that is the order in which the results have to be when BD-BR is computed.
        if quality_param_type == QualityParam.QP:
            quality_param_list = sorted(quality_param_list, reverse=True)
        elif quality_param_type == QualityParam.BITRATE:
            quality_param_list = sorted(quality_param_list)

        param_sets = []
        if encoder_id == Encoder.KVAZAAR:
            self.encoder = Kvazaar(encoder_revision, encoder_defines)
            param_sets = [
                KvazaarParamSet(
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
