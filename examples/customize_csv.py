import my_cfg
import tester.core.csv as csv
from tester import Tester, Test, QualityParam, Cfg
from tester.encoders import Kvazaar, X265

"""
An example of comparing Kvazaar to x265 on all HEVC-CTC sequences
and customizing the output csv
"""


Cfg().csv_enabled_fields = [
    csv.CsvField.CONFIG_NAME,
    csv.CsvField.SEQUENCE_CLASS,
    csv.CsvField.SEQUENCE_NAME,
    csv.CsvField.ENCODER_NAME,
    csv.CsvField.ENCODER_REVISION,
    csv.CsvField.ENCODER_CMDLINE,
    csv.CsvField.ANCHOR_NAME,
    csv.CsvField.QUALITY_PARAM_NAME,
    csv.CsvField.QUALITY_PARAM_VALUE,
    csv.CsvField.TIME_SECONDS,
    csv.CsvField.BITRATE,
    csv.CsvField.SPEEDUP,
    csv.CsvField.BDBR_PSNR,
    csv.CsvField.PSNR_CURVE_CROSSINGS,
    csv.CsvField.PSNR_OVERLAP,
    csv.CsvField.RATE_OVERLAP,
]

Cfg().csv_field_delimiter = ";"
Cfg().csv_decimal_point = "."
Cfg().csv_float_rounding_accuracy = 6

# These are the values that will appear at the header row of the csv
# If you want to rename all of the fields you can replace the whole dict
Cfg().csv_field_names[csv.CsvField.CONFIG_NAME] = "Test_name"


def main():
    sequences = [
        "hevc-A/*.yuv",
        "hevc-B/*.yuv",
        "hevc-C/*.yuv",
        "hevc-D/*.yuv",
        "hevc-E/*.yuv",
        "hevc-F/*.yuv",
    ]

    kvz = Test(
        name="Kvazaar",
        encoder_type=Kvazaar,
        encoder_revision="master",
        cl_args="--preset ultrafast",
        anchor_names=["Kvazaar"],
        quality_param_type=QualityParam.QP,
        quality_param_list=[22, 27, 32, 37],
        seek=0,
        frames=None,
        rounds=1,
        use_prebuilt=False
    )

    x265 = kvz.clone("x265", encoder_type=X265)

    context = Tester.create_context((kvz, x265), sequences)

    Tester.run_tests(context, parallel_runs=1)
    Tester.generate_csv(context, "example.csv", parallel_calculations=1)


if __name__ == '__main__':
    main()
