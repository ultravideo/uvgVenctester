from tester.core.log import *

import re
import subprocess
from pathlib import Path


def compute_psnr_and_ssim(yuv_filepath: Path,
                          hevc_filepath: Path,
                          sequence_width: int,
                          sequence_height: int,
                          seek: int,
                          frames: int) -> (float, float):

    # The path of the HEVC file as well as the log files will contain spaces,
    # so the easiest solution is to change the working directory and
    # use relative filepaths.

    psnr_log_filepath = hevc_filepath.with_name(hevc_filepath.stem + "_psnr_log").with_suffix(".txt")
    ssim_log_filepath = hevc_filepath.with_name(hevc_filepath.stem + "_ssim_log").with_suffix(".txt")

    ffmpeg_command = (
        "cd", str(hevc_filepath.parent),
        "&&", "ffmpeg",
              "-pix_fmt", "yuv420p",
              "-s:v", f"{sequence_width}x{sequence_height}",
              "-f", "rawvideo",
              "-r", "1", # set FPS to 1 to...
              "-ss", f"{seek}", # ...seek the starting frame
              "-t", f"{frames}",
              "-i", str(yuv_filepath),
              "-r", "1",
              "-t", f"{frames}",
              "-i", hevc_filepath.name,
              "-c:v", "rawvideo",
              "-filter_complex", f"[0:v]split=2[in1_1][in1_2];"
                                 f"[1:v]split=2[in2_1][in2_2];"
                                 f"[in2_1][in1_1]ssim=stats_file={ssim_log_filepath.name};"
                                 f"[in2_2][in1_2]psnr=stats_file={psnr_log_filepath.name}",
              "-f", "null", "-",
    )

    try:
        console_logger.debug(f"ffmpeg: Computing metrics")
        console_logger.debug(f"ffmpeg: Input: '{yuv_filepath.name}'")
        console_logger.debug(f"ffmpeg: Output: '{hevc_filepath.name}'")
        console_logger.debug(f"ffmpeg: PSNR log: '{psnr_log_filepath.name}'")
        console_logger.debug(f"ffmpeg: SSIM log: '{ssim_log_filepath.name}'")

        if not psnr_log_filepath.exists() and not ssim_log_filepath.exists():
            subprocess.check_output(ffmpeg_command, stderr=subprocess.STDOUT, shell=True)
        else:
            console_logger.debug(f"ffmpeg: Files '{psnr_log_filepath.name}' "
                                 f"and '{ssim_log_filepath.name}' already exist")

        # Ugly but simple.

        psnr_avg = 0.0
        with psnr_log_filepath.open("r") as psnr_log:
            pattern = re.compile(r".*psnr_avg:([0-9]+.[0-9]+).*", re.DOTALL)
            lines = psnr_log.readlines()
            for line in lines:
                for item in pattern.fullmatch(line).groups():
                    psnr_avg += float(item)
            psnr_avg /= len(lines)

        ssim_avg = 0.0
        with ssim_log_filepath.open("r") as ssim_log:
            pattern = re.compile(r".*All:([0-9]+.[0-9]+).*", re.DOTALL)
            lines = ssim_log.readlines()
            for line in lines:
                for item in pattern.fullmatch(line).groups():
                    ssim_avg += float(item)
            ssim_avg /= len(lines)

        return psnr_avg, ssim_avg

    except Exception as exception:
        console_logger.error(f"ffmpeg: Failed to compute metrics")
        if isinstance(exception, subprocess.CalledProcessError):
            console_logger.error(exception.output.decode())
        raise
