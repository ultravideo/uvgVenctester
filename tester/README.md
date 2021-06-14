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
2. Implement a new subclass of `tester.encoders.base.EncoderBase.ParamSet`
    - This class represents a set of command line parameters to be passed to the encoder when encoding
    - This class should be named `<ParamSet>`
    - This class should be placed in `tester/encoders/<encoder_name>.py`
    - This class should be inside the `<EnocderName>` class


`tester/encoders/kvazaar.py` and `tester/core/test.py` together provide a full example.

## Adding new metrics and metric calculation

The commit `c41a1aa104d219ff783d846b142da80d635bb9bf` is a great example on how to both add a new metric and the calculation

- If the metric is an absolute metric the call to the calculation should be added to the 
  `_calculate_metrics_for_one_run` function in `tester.py::Tester`
- For comparative metrics the calculation should be added under the `SequenceMetrics` class in
  `metrics.py` and the call should be added into the `values_by_field` in `CsvField.add_entry` or the equivalent in
  `table.py` if the metric should be included in tables
- The enums in `csv.py`, `table.py`, and `graph.py` need to be updated to include the metric for each output type that
  should include the metric.
- Also suggested adding default values to the corresponding `Cfg()` structures.
