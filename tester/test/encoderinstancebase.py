#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .encodingparamsetbase import *

class EncoderInstanceBase:
    def __init__(self):
        pass

    def __eq__(self, other):
        raise NotImplementedError

    def __hash__(self):
        raise NotImplementedError

    def get_exe_path(self) -> str:
        raise NotImplementedError

    def get_encoder_name(self) -> str:
        raise NotImplementedError

    def get_defines(self) -> list:
        raise NotImplementedError

    def get_user_revision(self) -> str:
        raise NotImplementedError

    def get_revision(self) -> str:
        raise NotImplementedError

    def get_short_revision(self) -> str:
        raise NotImplementedError

    def get_output_base_dir(self) -> str:
        raise NotImplementedError

    def get_output_subdir(self, param_set: EncodingParamSetBase) -> str:
        raise NotImplementedError

    def build(self):
        raise NotImplementedError

    def dummy_run(self, params: EncodingParamSetBase) -> bool:
        raise NotImplementedError
