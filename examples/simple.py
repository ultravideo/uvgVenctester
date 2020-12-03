import my_cfg
from tester import Tester, Test, QualityParam
from tester.encoders import Kvazaar, X265

"""
A very simple example of comparing Kvazaar to x265 on all HEVC-CTC sequences
and generating a csv out of the results
"""

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
