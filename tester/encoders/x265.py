"""This module defines all functionality specific to x265."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import tester
import tester.core.test as test
from . import EncoderBase


class X265(EncoderBase):
    """Represents a x265 executable."""
    
    def __init__(self):
        raise NotImplementedError

    def build(self) -> None:
        raise NotImplementedError

    def clean(self) -> None:
        raise NotImplementedError

    def dummy_run(self,
                  param_set: EncoderBase.ParamSet) -> bool:
        raise NotImplementedError

    def encode(self,
               encoding_run: test.EncodingRun) -> None:
        raise NotImplementedError

    class ParamSet(EncoderBase.ParamSet):
        """Represents the commandline parameters passed to x265 when encoding."""
        
        @staticmethod
        def _get_arg_order() -> list:
            return []

        def _to_unordered_args_list(self,
                                    include_quality_param: bool = True,
                                    include_seek: bool = True,
                                    include_frames: bool = True,
                                    inode_safe: bool = False) -> list:
            raise NotImplementedError