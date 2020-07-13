from core.log import console_logger
from .encodingparamsetbase import *
from .metrics import *
from .videosequence import *
from encoders import kvazaar

from enum import Enum
import hashlib

class EncoderId(Enum):
    NONE: int = 0
    KVAZAAR: int = 1



class SubTestConfig:
    def __init__(self,
                 parent_config_name: str,
                 encoder_instance: EncoderInstanceBase,
                 param_set: EncodingParamSetBase):
        self.name = f"{parent_config_name}/"\
                    f"{param_set.get_quality_param_name().lower()}"\
                    f"{param_set.get_quality_param_value()}"
        self.encoder_instance = encoder_instance
        self.param_set = param_set

    def __eq__(self, other):
        return self.name == other.get_name()\
               and self.encoder_instance == other.encoder_instance()\
               and self.param_set == other.get_param_set()

    def __hash__(self):
        return int(hashlib.md5(self.encoder_instance).hexdigest(), 16)\
               + int(hashlib.md5(self.param_set).hexdigest(), 16)

    def get_name(self):
        return self.name

    def get_encoder_instance(self):
        return self.encoder_instance

    def get_param_set(self):
        return self.param_set

    def get_sequence_metrics(self, sequence: VideoSequence):
        return SubMetrics(self.get_encoder_instance(), self.get_param_set(), sequence)



class TestConfig:
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
        self.encoder: kvazaar.EncoderInstance = None
        self.anchor_names: list = anchor_names

        self.subconfigs: list = []
        if encoder_id == EncoderId.KVAZAAR:
            self.encoder = kvazaar.EncoderInstance(encoder_revision, encoder_defines)
            for quality_param_value in quality_param_list:
                param_set = kvazaar.EncodingParamSet(quality_param_type, quality_param_value, cl_args)
                subconfig = SubTestConfig(self.name, self.encoder, param_set)
                self.subconfigs.append(subconfig)
        else:
            console_logger.error(f"TestConfig: '{self.name}': Unknown encoder '{self.encoder}'")
            raise RuntimeError

    def __eq__(self, other):
        return self.name == other.get_name()\
               and self.encoder == other.get_encoder()\
               and self.anchor_names == other.get_anchor_names()\
               and self.subconfigs == other.get_subconfigs()

    def __hash__(self):
        return int(hashlib.md5(self.name.encode()).hexdigest(), 16)

    def get_name(self):
        return self.name

    def get_subconfigs(self):
        return self.subconfigs

    def get_encoder(self):
        return self.encoder

    def get_anchor_names(self):
        return self.anchor_names

    def get_sequence_metrics(self, sequence: VideoSequence):
        return Metrics(
            self.encoder,
            [subconfig.get_param_set() for subconfig in self.subconfigs],
            sequence
        )
