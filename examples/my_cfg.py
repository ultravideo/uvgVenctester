from tester.core.cfg import Cfg

"""
An example of configuration file
If you define all of these the tester should work as expected

Rest of the variables are probably better defined in the individual test files
as it is likely that you want different things with different test runs.
"""


Cfg().tester_sequences_dir_path = r"C:\users\venctester\sequences"

if Cfg().system_os_name == "Windows":
    Cfg().vs_install_path = r"C:\Program Files (x86)\Microsoft Visual Studio"
    Cfg().vs_year_version = "2019"
    Cfg().vs_major_version = "16"
    Cfg().vs_edition = "Enterprise"
    Cfg().vs_msvc_version = "19.26"
    Cfg().vs_msbuild_platformtoolset = "v142"

    # These are optional but required for full functionality, in linux they are
    # likely in PATH and don't have to be explicitly defined.
    Cfg().wkhtmltopdf = r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"
    Cfg().nasm_path = r"C:\Program Files\NASM\nasm.exe"

# Needed for checking the conformance of HEVC bitstreams otherwise optional
Cfg().hevc_reference_decoder = r"C:\Users\venctester\bin\TAppDecoder.exe"

# Again only needed if calculating VMAF results
Cfg().vmaf_repo_path = r"C:\Users\venctester\vmaf"
