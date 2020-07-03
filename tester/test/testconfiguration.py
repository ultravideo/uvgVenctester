from core.log import console_logger
from .encodingparamsetbase import *
from encoders import kvazaar

from enum import Enum
import hashlib

class EncoderId(Enum):
    NONE: int = 0
    KVAZAAR: int = 1

class TestConfiguration:
    def __init__(self,
                 name: str,
                 quality_param_type: QualityParamType,
                 quality_param_list: list,
                 cl_args: str,
                 encoder: EncoderId,
                 encoder_revision: str,
                 encoder_defines: list,
                 anchor_names: list):
        self.name = name
        self.encoder: EncoderId = encoder
        self.encoder_instance: kvazaar.EncoderInstance = None
        self.encoding_param_sets: list = []
        self.anchor_names = anchor_names

        if self.encoder == EncoderId.KVAZAAR:
            self.encoder_instance = kvazaar.EncoderInstance(encoder_revision, encoder_defines)
            for value in quality_param_list:
                self.encoding_param_sets.append(kvazaar.EncodingParamSet(quality_param_type, value, cl_args))
        else:
            console_logger.error(f"Test configuration '{self.name}': Unknown encoder '{self.encoder}'")

        hash = hashlib.md5()
        hash.update(name.encode())
        self.hash = int(hash.hexdigest(), 16)

    def __eq__(self, other):
        return self.encoder_instance == other.encoder_instance\
               and self.encoding_param_sets == other.encoding_param_sets

    def __hash__(self):
        return self.hash

    def get_name(self):
        return self.name

    def get_encoding_param_sets(self):
        return self.encoding_param_sets

    def get_encoder_instance(self):
        return self.encoder_instance

    def get_anchor_names(self):
        return self.anchor_names
