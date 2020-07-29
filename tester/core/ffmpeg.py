"""This module defines functionality related to ffmpeg."""

from tester.core.log import *
from tester.core.video import *
from tester.core.test import *

import re
import subprocess
from pathlib import Path


def compute_psnr_and_ssim(encoding_run: EncodingRun) -> (float, float):

    # The path of the HEVC file as well as the log files will contain spaces,
    # so the easiest solution is to change the working directory and
    # use relative filepaths.

    ffmpeg_command = (
        "cd", str(encoding_run.output_file.get_filepath().parent),
        "&&", "ffmpeg",
              "-pix_fmt", f"{encoding_run.input_sequence.get_pixel_format()}",
              "-s:v", f"{encoding_run.input_sequence.get_width()}x{encoding_run.input_sequence.get_height()}",
              "-f", "rawvideo",
              "-r", "1", # set FPS to 1 to...
              "-ss", f"{encoding_run.input_sequence.get_seek()}", # ...seek the starting frame
              "-t", f"{encoding_run.input_sequence.get_framecount()}",
              "-i", str(encoding_run.input_sequence.get_filepath()),
              "-r", "1",
              "-t", f"{encoding_run.input_sequence.get_framecount()}",
              "-i", encoding_run.output_file.get_filepath().name,
              "-c:v", "rawvideo",
              "-filter_complex", f"[0:v]split=2[in1_1][in1_2];"
                                 f"[1:v]split=2[in2_1][in2_2];"
                                 # Absolute paths cause problems in these:
                                 f"[in2_1][in1_1]ssim=stats_file={encoding_run.ssim_log_path.name};"
                                 f"[in2_2][in1_2]psnr=stats_file={encoding_run.psnr_log_path.name}",
              "-f", "null", "-",
    )

    try:
        console_log.debug(f"ffmpeg: Computing metrics")
        console_log.debug(f"ffmpeg: Input: '{encoding_run.input_sequence.get_filepath().name}'")
        console_log.debug(f"ffmpeg: Output: '{encoding_run.output_file.get_filepath().name}'")
        console_log.debug(f"ffmpeg: PSNR log: '{encoding_run.psnr_log_path.name}'")
        console_log.debug(f"ffmpeg: SSIM log: '{encoding_run.ssim_log_path.name}'")

        if not encoding_run.psnr_log_path.exists() \
                and not encoding_run.ssim_log_path.exists():
            subprocess.check_output(ffmpeg_command, stderr=subprocess.STDOUT, shell=True)
        else:
            console_log.debug(f"ffmpeg: Files '{encoding_run.psnr_log_path.name}' "
                              f"and '{encoding_run.output_file.ssim_log_path.name}' already exist")

        # Ugly but simple.

        psnrs = []
        psnr_avg = 0.0
        with encoding_run.psnr_log_path.open("r") as psnr_log:
            pattern = re.compile(r".*psnr_avg:([0-9]+.[0-9]+).*", re.DOTALL)
            lines = psnr_log.readlines()
            for line in lines:
                for item in pattern.fullmatch(line).groups():
                    psnrs.append(float(item))
            psnr_avg = sum(psnrs) / len(lines)

        ssims = []
        ssim_avg = 0.0
        with encoding_run.ssim_log_path.open("r") as ssim_log:
            pattern = re.compile(r".*All:([0-9]+.[0-9]+).*", re.DOTALL)
            lines = ssim_log.readlines()
            for line in lines:
                for item in pattern.fullmatch(line).groups():
                    ssims.append(float(item))
            ssim_avg = sum(ssims) / len(lines)

        return psnr_avg, ssim_avg

    except Exception as exception:
        console_log.error(f"ffmpeg: Failed to compute metrics")
        if isinstance(exception, subprocess.CalledProcessError):
            console_log.error(exception.output.decode())
        raise
