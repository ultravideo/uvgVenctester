import test
from core.log import console_logger

class EncodingParamSet(test.EncodingParamSetBase):

    POSITIONAL_ARGS = ("--preset", "--gop")

    def __init__(self,
                 quality_param_type: test.QualityParamType,
                 quality_param_value: int,
                 cl_args: str):
        super().__init__(quality_param_type, quality_param_value, cl_args)

        if not self.quality_param_type in (test.QualityParamType.QP, test.QualityParamType.BITRATE):
            console_logger.error(f"Kvazaar: Invalid quality_param_type '{str(self.quality_param_type)}'")
            raise RuntimeError

        # Check integrity. TODO: Refactor to state intent.
        self.to_cmdline_str()

    def __eq__(self, other: test.EncodingParamSetBase):
        return self.quality_param_type == other.quality_param_type\
               and self.quality_param_value == other.quality_param_value\
               and self.cl_args == other.cl_args

    def to_cmdline_str(self, include_quality_param: bool = True) -> str:
        """Reorders command line arguments such that --preset is first, --gop second and all the rest last.
        Also checks that the args are syntactically valid. Returns the arguments as a string."""

        def is_long_option(candidate: str):
            return candidate.startswith("--")

        def is_short_option(candidate: str):
            return not is_long_option(candidate) and candidate.startswith("-")

        def is_option(candidate: str):
            return is_long_option(candidate) or is_short_option(candidate)

        def is_value(candidate: str):
            return not is_option(candidate)

        cl_args = self.cl_args

        if include_quality_param:
            if self.quality_param_type == test.encodingparamsetbase.QualityParamType.QP:
                cl_args += f" --qp {self.quality_param_value}"
            elif self.quality_param_type == test.encodingparamsetbase.QualityParamType.BITRATE:
                cl_args += f" --bitrate {self.quality_param_value}"

        split_args: list = []

        # Split the arguments such that each option and its value, if any, are separated.
        for item in cl_args.split():
            if is_short_option(item):
                # A short option is of the form -<short form><value> or -<short form> <value>,
                # so split after the second character.
                option_name: str = item[:2]
                option_value: str = item[2:].strip()
                split_args.append(option_name)
                if option_value:
                    split_args.append(option_value)
            else:
                for item in item.split("="):
                    split_args.append(item)

        # Put the options and their values into this dict. Value None indicates that the option
        # is a boolean with no explicit value.
        option_values: dict = {}
        i: int = 0
        i_max: int = len(split_args)
        while i < i_max:
            option_name = split_args[i]
            if is_option(option_name) and i + 1 < i_max and is_value(split_args[i + 1]):
                option_value = split_args[i + 1]
                i += 2
            else:
                option_value = None
                i += 1

            if option_name in option_values:
                raise RuntimeError(f"Kvazaar: Duplicate option {option_name}")

            option_values[option_name] = option_value

        # Check that no option is specified as both no-<option> and <option>.
        for option_name in option_values.keys():
            option_name = option_name.strip("--")
            if f"--no-{option_name}" in option_values.keys():
                raise RuntimeError(f"Kvazaar: Conflicting options '--{option_name}' and '--no-{option_name}'")

        # Reorder the options. --preset and --gop must be the first, in this order. The order
        # of the rest doesn't matter.

        # Handle --preset and --gop.
        reordered_cl_args: list = []
        for option_name in self.POSITIONAL_ARGS:
            if option_name in option_values:
                option_value = option_values[option_name]
                reordered_cl_args.append(option_name)
                if option_value:
                    reordered_cl_args.append(option_value)
                del option_values[option_name]

        # Handle option flags with implicit boolean values (for example --no-wpp).
        for option_name in sorted(option_values.keys()):
            option_value = option_values[option_name]
            if option_value is None:
                reordered_cl_args.append(option_name)
                del option_values[option_name]

        # Handle long options with explicit values (for example --frames 256)
        for option_name in sorted(option_values.keys()):
            option_value = option_values[option_name]
            if is_long_option(option_name):
                reordered_cl_args.append(option_name)
                reordered_cl_args.append(option_value)

        # Handle short options with explicit values (for example -n 256).
        for option_name in sorted(option_values.keys()):
            option_value = option_values[option_name]
            if is_short_option(option_name):
                reordered_cl_args.append(option_name)
                reordered_cl_args.append(option_value)

        return " ".join(reordered_cl_args)
