from tester.core.log import *

import os
import re
import subprocess


def compute_psnr_and_ssim(yuv_filepath: str,
                          hevc_filepath: str,
                          sequence_width: int,
                          sequence_height: int,
                          seek: int,
                          frames: int) -> (float, float):

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

    ffmpeg_command = (
        "cd", work_dir,
        "&&", "ffmpeg",
              "-pix_fmt", "yuv420p",
              "-s:v", f"{sequence_width}x{sequence_height}",
              "-f", "rawvideo",
              "-r", "1", # set FPS to 1 to...
              "-ss", f"{seek}", # ...seek the starting frame
              "-t", f"{frames}",
              "-i", yuv_filepath,
              "-r", "1",
              "-t", f"{frames}",
              "-i", hevc_filename,
              "-c:v", "rawvideo",
              "-filter_complex", f"[0:v]split=2[in1_1][in1_2];"
                                 f"[1:v]split=2[in2_1][in2_2];"
                                 f"[in2_1][in1_1]ssim=stats_file={ssim_log_filename};"
                                 f"[in2_2][in1_2]psnr=stats_file={psnr_log_filename}",
              "-f", "null", "-",
    )

    try:
        console_logger.debug(f"ffmpeg: Computing metrics")
        console_logger.debug(f"ffmpeg: Input: '{yuv_filename}'")
        console_logger.debug(f"ffmpeg: Output: '{hevc_filename}'")
        console_logger.debug(f"ffmpeg: PSNR log: '{psnr_log_filename}'")
        console_logger.debug(f"ffmpeg: SSIM log: '{ssim_log_filename}'")

        if not os.path.exists(psnr_log_filepath) and not os.path.exists(ssim_log_filepath):
            subprocess.check_output(ffmpeg_command, stderr=subprocess.STDOUT, shell=True)
        else:
            console_logger.debug(f"ffmpeg: Files '{psnr_log_filename}' "
                                 f"and '{ssim_log_filename}' already exist")

        # Ugly but simple.

        psnr_avg = 0.0
        with open(psnr_log_filepath, "r") as psnr_log_file:
            pattern = re.compile(r".*psnr_avg:([0-9]+.[0-9]+).*", re.DOTALL)
            lines = psnr_log_file.readlines()
            for line in lines:
                for item in pattern.fullmatch(line).groups():
                    psnr_avg += float(item)
            psnr_avg /= len(lines)

        ssim_avg = 0.0
        with open(ssim_log_filepath, "r") as ssim_log_file:
            pattern = re.compile(r".*All:([0-9]+.[0-9]+).*", re.DOTALL)
            lines = ssim_log_file.readlines()
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
