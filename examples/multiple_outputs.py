from pathlib import Path

import my_cfg
import tester.core.csv as csv
import tester.core.table as table
import tester.core.graphs as graph
from tester import Tester, Test, QualityParam, Cfg, ResultTypes
from tester.encoders import Kvazaar, X265

"""
An example of comparing Kvazaar to x265 on all HEVC-CTC sequences
with all output types and how to customize them
"""

#  CSV
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


# TABLE

Cfg().table_enabled_columns = [
    table.TableColumns.VIDEO,
    table.TableColumns.PSNR_BDBR,
    table.TableColumns.SPEEDUP,
]

# How the table data will be formatted, this for example will capitalize the video names
Cfg().table_column_formats[table.TableColumns.VIDEO] = lambda x: x.upper()

# Similart to csv_field_names
Cfg().table_column_headers[table.TableColumns.VIDEO] = "Sequence"


# GRAPH

Cfg().graph_enabled_metrics = [
    graph.GraphMetrics.PSNR
]

# The colors used in the graphs, the order of colors will be the same as in which
# order the tests are passed for the create_context()
# In this example Kvazaar's lines would be in red and x265 in blue
Cfg().graph_colors = [
    "xkcd:red",
    "xkcd:blue",
]

# Bitrate targets are anyways disabled with QP encoding but just explicitly showing this setting
Cfg().graph_include_bitrate_targets = False


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
    Tester.compute_metrics(context,
                           parallel_calculations=1,
                           result_types=(ResultTypes.CSV, ResultTypes.GRAPH, ResultTypes.TABLE))
    Tester.generate_csv(context, "example.csv")
    Tester.create_tables(context, "example.html")
    Tester.generate_rd_graphs(context, Path("example_graphs"))


if __name__ == '__main__':
    main()
