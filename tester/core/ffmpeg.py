from tester.core.log import *
from tester.core.video import *

import re
import subprocess
from pathlib import Path


def compute_psnr_and_ssim(input_sequence: RawVideoSequence,
                          output_sequence: HevcVideoFile) -> (float, float):

    # The path of the HEVC file as well as the log files will contain spaces,
    # so the easiest solution is to change the working directory and
    # use relative filepaths.

    ffmpeg_command = (
        "cd", str(output_sequence.get_filepath().parent),
        "&&", "ffmpeg",
              "-pix_fmt", "yuv420p",
              "-s:v", f"{input_sequence.get_width()}x{input_sequence.get_height()}",
              "-f", "rawvideo",
              "-r", "1", # set FPS to 1 to...
              "-ss", f"{input_sequence.get_seek()}", # ...seek the starting frame
              "-t", f"{input_sequence.get_framecount()}",
              "-i", str(input_sequence.get_filepath()),
              "-r", "1",
              "-t", f"{output_sequence.get_framecount()}",
              "-i", output_sequence.get_filepath().name,
              "-c:v", "rawvideo",
              "-filter_complex", f"[0:v]split=2[in1_1][in1_2];"
                                 f"[1:v]split=2[in2_1][in2_2];"
                                 # Absolute paths cause problems in these:
                                 f"[in2_1][in1_1]ssim=stats_file={output_sequence.get_ssim_log_path().name};"
                                 f"[in2_2][in1_2]psnr=stats_file={output_sequence.get_psnr_log_path().name}",
              "-f", "null", "-",
    )

    try:
        console_logger.debug(f"ffmpeg: Computing metrics")
        console_logger.debug(f"ffmpeg: Input: '{input_sequence.get_filepath().name}'")
        console_logger.debug(f"ffmpeg: Output: '{output_sequence.get_filepath().name}'")
        console_logger.debug(f"ffmpeg: PSNR log: '{output_sequence.get_ssim_log_path().name}'")
        console_logger.debug(f"ffmpeg: SSIM log: '{output_sequence.get_ssim_log_path().name}'")

        if not output_sequence.get_psnr_log_path().exists() \
                and not output_sequence.get_ssim_log_path().exists():
            subprocess.check_output(ffmpeg_command, stderr=subprocess.STDOUT, shell=True)
        else:
            console_logger.debug(f"ffmpeg: Files '{output_sequence.get_psnr_log_path().name}' "
                                 f"and '{output_sequence.get_ssim_log_path().name}' already exist")

        # Ugly but simple.

        psnr_avg = 0.0
        with output_sequence.get_psnr_log_path().open("r") as psnr_log:
            pattern = re.compile(r".*psnr_avg:([0-9]+.[0-9]+).*", re.DOTALL)
            lines = psnr_log.readlines()
            for line in lines:
                for item in pattern.fullmatch(line).groups():
                    psnr_avg += float(item)
            psnr_avg /= len(lines)

        ssim_avg = 0.0
        with output_sequence.get_ssim_log_path().open("r") as ssim_log:
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
