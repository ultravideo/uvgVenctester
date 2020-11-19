# Venctester3 - A HEVC video encoder testing framework

## General

**Venctester3** (to be renamed) is a HEVC video encoder testing framework. The framework provides an easy way to compare the efficiency and output quality of different encoders with a generic, simple API.

## Supported encoders

- [HM](https://vcgit.hhi.fraunhofer.de/jct-vc/HM)
- [Kvazaar](https://github.com/ultravideo/kvazaar)
- [VTM](https://vcgit.hhi.fraunhofer.de/jvet/VVCSoftware_VTM)

## Dependencies

- Windows 10 or Linux
- [Ffmpeg](https://ffmpeg.org/)
  - Must be in `PATH` and able to be used as `ffmpeg`
- [CMake](https://cmake.org)
  - Must be in `PATH` and able to be used as `cmake`
- [Python interpreter (3.8+)](https://python.org/)
- Python libraries
  - [colorama](https://github.com/tartley/colorama)
  - [vmaf](https://github.com/Netflix/vmaf)
    1. Clone the repository
    2. Go to vmaf/python
    3. Run `python setup.py install`

Windows 10 only:
- [Visual Studio 2019](https://visualstudio.microsoft.com/)

Linux only:
- [Make](https://gnu.org/software/make/)
  - Must be in `PATH` and able to be used as `make`
- [GCC](https://gcc.gnu.org/)
  - Must be in `PATH` and able to be used as `gcc`

## Installation

Clone this repository and install the dependencies.

## Setup

### 1. SSH

The tester clones source code from gitlab.tut.fi using SSH. Make sure you have an SSH key set up.

### 2. Tester configuration

Check that the configuration variables (see the Customization section below) match your system and override them if needed. In particular, check the following:

Windows/Linux:
- `csv_decimal_point`
- `csv_field_delimiter`
- `vmaf_repo_path`
- `hm_cfg_file_path` (if HM is being used)
- `vtm_cfg_file_path` (if VTM is being used)

Windows only:
- `vs_install_path`
- `vs_year_version`
- `vs_major_version`
- `vs_edition`
- `vs_msvc_version`
- `vs_msbuild_platformtoolset`

## Example usage

### 1. Set the required configuration variables.

- This example is on Windows

`userconfig.py`:
```python
from tester.core.cfg import *

Cfg().vmaf_repo_path = "vmaf"
Cfg().hm_cfg_file_path = "encoder_randomaccess_main.cfg"
Cfg().vtm_cfg_file_path = "encoder_randomaccess_vtm.cfg"
Cfg().vs_install_path = r"C:\Microsoft Visual Studio"
Cfg().vs_year_version = "2019"
Cfg().vs_major_version = "16"
Cfg().vs_edition = "Enterprise"
Cfg().vs_msvc_version = "19.26"
Cfg().vs_msbuild_platformtoolset = "v142"
```

### 2. Import your configuration file and the tester library.

`main.py`:
```python
import userconfig
from tester import Tester, Test, QualityParam
from tester.core import csv
from tester.encoders import Kvazaar
```

### 3. Specify the video sequences you want to have encoded.

- The file paths are relative to `tester_input_dir_path` (default: current working directory)
- Wildcards can be used
- The file names must contain the resolution, and may contain the framerate and frame count (`<name>_<width>x<height>_<framerate>_<frame count>.yuv`)
    - If the name doesn't contain the framerate, it is assumed to be 25 FPS
    - If the name doesn't contain the frame count, it is computed automatically from the size of the file, with the assumption that chroma is 420 and 8 bits are used for each pixel

`main.py`:
```python
input_sequence_globs = [
    "hevc-A/*.yuv",
    "hevc-B/*.yuv",
]
```

### 4. Specify the encoder configurations you want to test.

`main.py`:
```python
test1 = Test(
    name="test1",
    quality_param_type=QualityParam.QP,
    quality_param_list=[22, 27, 32, 37],
    cl_args="--gop=8 --preset ultrafast --no-wpp --owf 5",
    encoder_type=Kvazaar,
    encoder_revision="d1abf85229",
    encoder_defines=["NDEBUG"],
    anchor_names=["test1"],
    rounds=3,
    use_prebuilt=False,
)

test2 = Test(
    name="test2",
    quality_param_type=QualityParam.BITRATE,
    quality_param_list=[100000, 250000, 500000, 750000,],
    cl_args="--gop=8 --preset ultrafast --owf 5",
    encoder_id=Encoder.KVAZAAR,
    encoder_revision="master",
    encoder_defines=["NDEBUG"],
    anchor_names=["test1"],
    use_prebuilt=False,
)

test3 = test2.clone(
    name="test3",
    cl_args="--gop=8 --preset ultrafast --no-wpp --owf 5",
    anchor_names=["test1", "test2"],
    rounds=5
)

configs = [
    test1,
    test2,
    test3,
]
```

Required parameters for `Test()`:
- `name` The name of the test configuration
    - Arbitrary, but must be unique
- `cl_args` Additional encoder-specific command line arguments
    - Must not contain arguments conflicting with those generated from the other parameters to this function (e.g. `quality_param_type`)
- `encoder_type` The encoder class to be used
- `encoder_revision` The Git revision of the encoder to be used
    - Anything that can be used with `git checkout` is valid
    - If `use_prebuilt` is defined then this will be concatenated to the encoder name, i.e., `"kvazaar_" + encoder_revision`
- `anchor_names` A list containing the names of the configurations the configuration is compared to, if any

Optional parameters for `Test()`:
- `quality_param_type` The quality parameter to be used (QP or bitrate)
    - Default: QualityParam.QP
    - The type of quality parameter may vary between test configurations
- `quality_param_list` A list containing the quality parameter values with which the test will be run
    - Default: [22, 27, 32, 37]
    - All configurations must have a list of equal length
- `encoder_defines` A list containing the predefined preprocessor symbols to be used when compiling, if any
    - Default: []
- `use_prebuilt` Whether a prebuilt encoder is used or build from the source
    - Default: False
    - The prebuilt encoder should be placed in the directory spesified by `Cfg().tester_binaries_dir_path` in format "<encoder_name>_<version>(.exe)" .exe only in Windows
- `seek` An integer specifying how many frames at the start of each input file will be skipped
    - Default: 0
    - Applies to every sequence
    - All configurations must have the same `seek`
- `frames` An integer specifying how many frames are encoded
    - Default: All
    - Applies to every sequence
    - All configurations must have the same `frames`
- `rounds` An integer specifying how many times a test is repeated
    - Default: 1

`Test.clone()` accepts the same parameters as `Test()`.

### 5. Initialize the tester and create a testing context.

`main.py`:
```python
tester = Tester()
context = tester.create_context(configs, input_sequence_globs)
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

Any public property/attribute of `tester.core.cfg.Cfg` can be overridden by the user.

#### Example: Specifying Visual Studio and related tools

`userconfig.py`:
```python
from tester.core.cfg import *

Cfg().vs_install_path = r"C:\Microsoft Visual Studio"
Cfg().vs_year_version = "2019"
Cfg().vs_major_version = "16"
Cfg().vs_edition = "Enterprise"
Cfg().vs_msvc_version = "19.26"
Cfg().vs_msbuild_platformtoolset = "v142"
```

#### Example: Customizing CSV output

`userconfig.py`:
```python
from tester.core.cfg import *
from tester.core.csv import *

# You might want to set path for your test sequences.
Cfg().tester_sequences_dir_path = r"C:\User\test_sequences"

# You might have to set these depending on your system language settings.
Cfg().csv_decimal_point = ","
Cfg().csv_field_delimiter = ";"

# Enabled fields from left to right. Any field not included in this list will be omitted from the CSV.
# The list of all possible values can be found in tester.core.csv.
Cfg().csv_enabled_fields = [
    CsvField.SEQUENCE_NAME,
    CsvField.CONFIG_NAME,
    CsvField.ENCODER_CMDLINE,
    CsvField.TIME_SECONDS,
]

# Must include all the fields listed in CSV_ENABLED_FIELDS.
Cfg().csv_field_names = {
    CsvField.SEQUENCE_NAME: "Input sequence",
    CsvField.CONFIG_NAME: "Config",
    CsvField.ENCODER_CMDLINE: "Command line arguments",
    CsvField.TIME_SECONDS: "Encoding time (seconds)",
}
```

## Contacting the author

The most reliable way to contact me is by sending me an e-mail at anton.ihonen@gmail.com. Please feel free to do so at any time if you have any questions.
