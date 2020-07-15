from .log import *

import os
import re
import subprocess


def compute_psnr_and_ssim(yuv_filepath: str,
                          hevc_filepath: str,
                          sequence_width: int,
                          sequence_height: int) -> (float, float):

    # The path of the HEVC file as well as the log files will contain spaces,
    # so the easiest solution is to change the working directory and
    # use relative filepaths.
    work_dir = os.path.dirname(hevc_filepath)
    yuv_filename = os.path.basename(yuv_filepath)
    hevc_filename = os.path.basename(hevc_filepath)
    psnr_log_filename = os.path.splitext(hevc_filename)[0] + "_psnr_log.txt"
    ssim_log_filename = os.path.splitext(hevc_filename)[0] + "_ssim_log.txt"
    psnr_log_filepath = os.path.join(work_dir, psnr_log_filename)
    ssim_log_filepath = os.path.join(work_dir, ssim_log_filename)

    ffmpeg_command: tuple = (
        "(", "cd", work_dir,
        "&&", "ffmpeg",
        "-pix_fmt", "yuv420p",
        "-r", "25",
        "-s:v", f"{sequence_width}x{sequence_height}",
        "-i", yuv_filepath,
        "-r", "25",
        "-i", hevc_filename,
        "-c:v", "rawvideo",

        "-filter_complex", f"[0:v]split=2[in1_1][in1_2];"
                           f"[1:v]split=2[in2_1][in2_2];"
                           f"[in2_1][in1_1]ssim=stats_file={ssim_log_filename};"
                           f"[in2_2][in1_2]psnr=stats_file={psnr_log_filename}",
        "-f", "null", "-",
        "&&", "exit", "0"
                      ")", "||", "exit", "1"
    )

    try:
        console_logger.debug(f"ffmpeg: Computing PSNR and SSIM from input '{yuv_filename}'"
                             f" and output '{hevc_filename}'")
        subprocess.check_output(ffmpeg_command, stderr=subprocess.STDOUT, shell=True)

        # Ugly but simple.

        psnr_avg = 0.0
        with open(psnr_log_filepath, "r") as psnr_log_file:
            line_count = 0
            pattern = re.compile(r".*psnr_avg:([0-9]+.[0-9]+).*", re.DOTALL)
            for line in psnr_log_file.readlines():
                line_count += 1
                for item in pattern.fullmatch(line).groups():
                    psnr_avg += float(item)
            psnr_avg /= line_count

        ssim_avg = 0.0
        with open(ssim_log_filepath, "r") as ssim_log_file:
            line_count = 0
            pattern = re.compile(r".*All:([0-9]+.[0-9]+).*", re.DOTALL)
            for line in ssim_log_file.readlines():
                line_count += 1
                for item in pattern.fullmatch(line).groups():
                    ssim_avg += float(item)
            ssim_avg /= line_count

        return psnr_avg, ssim_avg

    except Exception as exception:
        console_logger.error(f"ffmpeg: Failed to compute PSNR and SSIM from input '{yuv_filename}'"
                             f" and output '{hevc_filename}'")
        if isinstance(exception, subprocess.CalledProcessError):
            console_logger.error(exception.output.decode())
        raise
