from enum import Enum


class QualityParamType(Enum):
    NONE: int = 0
    QP: int = 1
    BITRATE: int = 2


class EncodingParamSetBase():
    def __init__(self,
                 quality_param_type: QualityParamType,
                 quality_param_value: int,
                 cl_args: str):
        self.quality_param_type: QualityParamType = quality_param_type
        self.quality_param_value: int = quality_param_value
        self.cl_args: str = cl_args

    def get_quality_param_type(self):
        return self.quality_param_type

    def get_quality_param_name(self):
        if self.quality_param_type == QualityParamType.NONE:
            return ""
        elif self.quality_param_type == QualityParamType.QP:
            return "QP"
        elif self.quality_param_type == QualityParamType.BITRATE:
            return "bitrate"

    def get_quality_param_value(self):
        return self.quality_param_value

    def to_cmdline_tuple(self) -> tuple:
        # TODO: This will fail miserably if there are e.g. filepaths that contain whitespace.
        return tuple(self.to_cmdline_str().split())

    def to_cmdline_str(self, include_quality_param: bool = True) -> str:
        raise NotImplementedError
