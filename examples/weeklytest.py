import my_cfg

import os

from datetime import datetime, timedelta
import tester.core.git as git
from tester import QualityParam, Test, Tester, Cfg
from tester.core.log import console_log
from tester.encoders import Kvazaar, X265
from tester.tools import reservation_handler as rh

"""
An example configuration for checking the change over time in Kvazaar versus x265
Intended to be run using cronjob once a week
"""


def main():
    reservation_handler = rh.ReservationHandler("10.21.25.26", "30001", "Weeklytester")
    try:
        reservation_handler.reserve_server(time_h=120, time_m=0)
    except rh.ReservationHandler:
        return
    globs = [
        "hevc-B/*.yuv",
        "xiph-fullhd/*.yuv"
    ]
    kvz_repo = git.GitRepository(Cfg().tester_sources_dir_path / "kvazaar", )
    if not kvz_repo._local_repo_path.exists():
        kvz_repo.clone(Cfg().kvazaar_remote_url)

    kvz_repo.fetch_all()
    current = kvz_repo.rev_parse("origin/master")[1].decode().strip()
    temp = current
    weeks = 0
    while not temp or temp == current:
        weeks += 1
        temp = kvz_repo.get_latest_commit_between(
            datetime.now() - timedelta(weeks=weeks + 1),
            datetime.now() - timedelta(weeks=weeks),
        )
    temp = "eeb284050592408ee162cb64e58032a65c543184"

    uf_head = Test(
        name="Kvazaar_uf_master",
        encoder_type=Kvazaar,
        encoder_revision=current,
        cl_args="--preset=ultrafast --period=256 --rd=1 --pu-depth-intra=2-3,2-3,3-3,3-3,3-3 "
                "--pu-depth-inter=1-2,1-2,2-2,2-2,2-2 --signhide --me-early-termination=off "
                "--max-merge=2 --rc-algorithm=lambda --vaq 5 --threads 12",
        anchor_names=[f"Kvazaar_uf_since_{weeks}_weeks", "x265_uf"],
        quality_param_type=QualityParam.RES_ROOT_SCALED_BITRATE,
        quality_param_list=[5e5, 1e6, 2e6, 4e6, 6e6, 8e6, 10e6, 12e6],
        rounds=5
    )
    uf_since = uf_head.clone(
        encoder_revision=temp,
        name=f"Kvazaar_uf_since_{weeks}_weeks",
        anchor_names=[],
        rounds=5
    )

    uf_x265 = uf_since.clone(
        name="x265_uf",
        encoder_type=X265,
        encoder_revision="3.0",
        cl_args='--preset ultrafast --tune ssim --me 1 --ref 2 --limit-refs 3 --signhide --b-intra --pools 12'
    )

    vs_head = uf_head.clone(
        name="Kvazaar_vs_master",
        cl_args="--preset=veryslow --period=256 --rc-algorithm=oba --owf=0 --vaq 5 --threads 12",
        anchor_names=[f"Kvazaar_vs_since_{weeks}_weeks", "x265_vs"],
        rounds=1
    )

    vs_since = vs_head.clone(
        encoder_revision=temp,
        name=f"Kvazaar_vs_since_{weeks}_weeks",
        anchor_names=[],
        rounds=1
    )

    vs_x265 = vs_since.clone(
        name="x265_vs",
        encoder_type=X265,
        encoder_revision="3.0",
        cl_args='--preset veryslow --tune ssim --limit-refs 1 --limit-modes --max-merge 4 --aq-mode 1 --limit-tu 4 --pools 12'
    )

    table = f"/home/weeklytester/weekly_plots/weekly_plots/weekly_table_{datetime.now().strftime('%Y-%m-%d')}.pdf"

    context = Tester.create_context((uf_head, uf_since, uf_x265, vs_head, vs_since, vs_x265), globs)
    Tester.run_tests(context, parallel_runs=4)
    Tester.create_tables(context,
                         table,
                         parallel_calculations=4)

    latest_weekly_table_pdf = "/home/weeklytester/weekly_plots/weekly_plots/latest-weekly-table.pdf"
    try:
        os.unlink(latest_weekly_table_pdf)
    except:
        pass

    try:
        os.symlink(table, latest_weekly_table_pdf)
    except OSError as e:
        console_log.error(e)
    reservation_handler.free_server()


if __name__ == '__main__':
    main()
