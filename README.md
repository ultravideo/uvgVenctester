# Venctester3 - Minimum viable product

## General

**Venctester3** (to be renamed) is a HEVC video encoder testing framework. The framework provides an easy way to compare the efficiency and output quality of different encoders with a generic, simple API.

## Supported encoders

- [Kvazaar](https://github.com/ultravideo/kvazaar)

## Dependencies

- Windows 10 or Linux
- [Ffmpeg](https://ffmpeg.org/)
  - Must be in `PATH` and able to be used as `ffmpeg`
- [Visual Studio 2019](https://visualstudio.microsoft.com/) (Windows)
- [GCC](https://gcc.gnu.org/) (Linux)
  - Must be in `PATH` and able to be used as `gcc`
- [Python interpreter (3.8+)](https://www.python.org/)
- Python libraries
  - [colorama](https://github.com/tartley/colorama)
  - [vmaf](https://github.com/Netflix/vmaf)

## Installation

Clone this repository and install the dependencies.

## Setup

### 1. SSH

The tester clones source code from gitlab.tut.fi using SSH. Make sure you have an SSH key set up.

### 2. Tester configuration

Check that the configuration variables (see the Customization section below) match your system and override them if needed. In particular, check the following:

Windows/Linux:

- `CSV_DECIMAL_POINT`
- `CSV_FIELD_SEPARATOR`

Windows only:

- `KVZ_MSBUILD_PLATFORMTOOLSET`
- `KVZ_MSBUILD_WINDOWSTARGETPLATFORMVERSION`
- `KVZ_VS_SOLUTION_NAME`
- `VS_EDITION`
- `VS_INSTALL_PATH`
- `VS_VERSION`

## Example usage

### 1. Import the tester API.
`main.py`:
```python
from tester.core.tester import *
```

### 2. Initialize the tester.
- NOTE: This has to be done at this point - otherwise the tester may not work correctly (`userconfig.py` is read when the tester is initialized)!

`main.py`:
```python
tester = Tester()
```

### 3. Specify the video sequences you want to have encoded.

- The file paths are relative to `SEQUENCES_DIR_PATH` (default: current working directory)
- Wildcards can be used
- The file names must contain the resolution, and may contain the framerate and frame count (`<name>_<width>x<height>_<framerate>_<frame count>.yuv`)
    - If the name doesn't contain the framerate, it is assumed to be 25 FPS
    - If the name doesn't contain the frame count, it is computed automatically from the size of the file, assuming that chroma is 420 and 8 bits are used for each pixel

`main.py`:
```python
input_sequence_globs = [
    "hevc-A/*.yuv",
    "hevc-B/*.yuv
]
```

### 4. Specify the encoder configurations you want to test.
`main.py`:
```python
tests = [
        Test(
            name="example1",
            quality_param_type=QualityParamType.QP,
            quality_param_list=[22, 27, 32, 37,],
            cl_args="--preset ultrafast --gop=8 -n256 --owf 5 --no-wpp",
            encoder_id=EncoderId.KVAZAAR,
            encoder_revision="master",
            encoder_defines=["NDEBUG", "MY_SYMBOL"],
            anchor_names=[]
        ),
        Test(
            name="example2",
            quality_param_type=QualityParamType.BITRATE,
            quality_param_list=[100000, 250000, 500000, 750000,],
            cl_args="--preset ultrafast",
            encoder_id=EncoderId.KVAZAAR,
            encoder_revision="d1abf85229",
            encoder_defines=["NDEBUG"],
            anchor_names=["example1"]
        ),
]
```
Explanations for the parameters:
- `name` The name of the test configuration - arbitrary, but must be unique
- `quality_param_type` The quality parameter to be used (QP or bitrate)
- `quality_param_list` A list containing the quality parameter values with which the test will be run
    - All configurations must have a list of equal length
    - The values must be in ascending/descending order ()
- `cl_args` Additional encoder-specific command line arguments - must not contain the quality parameter (it is automatically added by the tester)
- `encoder_id` The encoder to be used
- `encoder_revision` The Git revision of the encoder to be used - anything that can be used with `git checkout` is valid
- `encoder_defines` A list containing the predefined preprocessor symbols to be used when compiling, if any
- `anchor_names` A list containing the names of the configurations the configuration is compared to, if any

Additional parameters:
- `seek`, `frames` May be used to encode only a part of each input sequence
    - These apply to every sequence
    - Each test configuration should have identical values for these parameters

### 5. Create a new testing context.
`main.py`:
```python
context = tester.create_context(tests, input_sequence_globs)
```

### 6. Run the tests.
`main.py`:
```python
tester.run_tests(context)
```

### 7. Calculate the results.
`main.py`:
```python
tester.compute_metrics(context)
```

### 8. Output the results to a CSV file.
- If the file already exists, it will be overwritten!

`main.py`:
```python
tester.generate_csv(context, "mycsv.csv")
```

## Customization

Any configuration variable (named with capital letters, **not** prefixed with underscores) in `tester.core.cfg` can be overridden in `userconfig.py`.

#### Example: Setting Visual Studio installation path

`userconfig.py`:
```python
# This makes the tester search for Visual Studio command line tools under
# "C:\Program Files (x86)\Microsoft Visual Studio\2019\Community".
VS_INSTALL_PATH = r"C:\Program Files (x86)\Microsoft Visual Studio"
VS_VERSION = "2019"
VS_EDITION = "Community"
```

#### Example: Customizing CSV output

`userconfig.py`:
```python
from tester.core.csv import *

# You might have to set these depending on your system language settings.
CSV_DECIMAL_POINT = ","
CSV_FIELD_SEPARATOR = ";"

# Enabled fields from left to right. Any field not included in this list will be omitted from the CSV.
# The list of all possible values can be found in tester.core.csv.
CSV_ENABLED_FIELDS = [
    CsvFieldId.SEQUENCE_NAME,
    CsvFieldId.CONFIG_NAME,
    CsvFieldId.ENCODER_CMDLINE,
    CsvFieldId.TIME_SECONDS,
]

# Must include all the fields listed in CSV_ENABLED_FIELDS.
CSV_FIELD_NAMES = {
    CsvFieldId.SEQUENCE_NAME = "Input sequence",
    CsvFieldId.CONFIG_NAME = "Config",
    CsvFieldId.ENCODER_CMDLINE = "Command line arguments",
    CsvFieldId.TIME_SECONDS = "Encoding time (seconds)",
}
```

## Contacting the author

The most reliable way to contact me is by sending me an e-mail at anton.ihonen@gmail.com. Please feel free to do so at any time if you have any questions.
