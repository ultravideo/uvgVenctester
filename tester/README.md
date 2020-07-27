# Venctester 3 codebase

## Directory structure

The codebase consists of the following directories:

- `encoders` (all encoder-specific code)
- `core` (all generic code)

Only the `encoders` directory needs to be touched if support for a new encoder is to be added.

## Adding support for a new encoder

To add support for a new encoder, the following things need to be done:

1. Implement a new subclass of `tester.encoders.base.EncoderBase`
    - This class represents an encoder binary
    - This class should be named `<EncoderName>`
    - This class should be placed in `tester/encoders/<encoder_name>.py`
2. Implement a new subclass of `tester.encoders.base.ParamSetBase`
    - This class represents a set of command line parameters to be passed to the encoder when encoding
    - This class should be named `<EncoderNameParamSet>`
    - This class should be placed in `tester/encoders/<encoder_name>.py`
3. Add a new value to `tester.encoders.base.EncoderId`
    - This enum identifies the encoders
    - The new value should be named `<ENCODER_NAME>`
4. Make the relevant changes to `tester.core.test.Test.__init__`
    - Instantiation of `_encoder` based on `encoder_id`
    - Instantiation of `param_sets` and therefore `_subtests` based on `encoder_id`

`tester/encoders/kvazaar.py` and `tester/core/test.py` together provide a full example.
