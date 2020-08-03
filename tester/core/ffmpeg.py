"""This module defines functionality related to ffmpeg."""

from tester.core.log import *
from tester.core.video import *
from tester.core.test import *

import os
import re
import shutil
import subprocess
from pathlib import Path

# Compile Regex patterns only once for better performance.
_PSNR_PATTERN: re.Pattern = re.compile(r".*psnr_avg:([0-9]+.[0-9]+).*", re.DOTALL)
_SSIM_PATTERN: re.Pattern = re.compile(r".*All:([0-9]+.[0-9]+).*", re.DOTALL)
_VMAF_PATTERN: re.Pattern = re.compile(r".*\"VMAF score\":([0-9]+.[0-9]+).*", re.DOTALL)


def compute_metrics(encoding_run: EncodingRun,
                    psnr: bool,
                    ssim: bool,
                    vmaf: bool) -> (float, float, float):

    if not psnr and not ssim and not vmaf:
        return None, None, None

    # Absolute paths were causing trouble, so use relative paths.
    psnr_log_name = encoding_run.psnr_log_path.name
    ssim_log_name = encoding_run.ssim_log_path.name
    vmaf_log_name = encoding_run.vmaf_log_path.name

    # Copy the VMAF model into the working directory to enable using a relative path.
    vmaf_model_src_path1 = Cfg().vmaf_repo_path / "model" / "vmaf_v0.6.1.pkl"
    vmaf_model_src_path2 = Cfg().vmaf_repo_path / "model" / "vmaf_v0.6.1.pkl.model"
    vmaf_model_dest_path1 = encoding_run.output_file.get_filepath().parent / "vmaf_v0.6.1.pkl"
    vmaf_model_dest_path2 = encoding_run.output_file.get_filepath().parent / "vmaf_v0.6.1.pkl.model"
    shutil.copy(str(vmaf_model_src_path1), str(vmaf_model_dest_path1))
    shutil.copy(str(vmaf_model_src_path2), str(vmaf_model_dest_path2))

    # Build the filter based on which metrics are to be computed.

    no_of_metrics = sum(int(boolean) for boolean in (psnr, ssim, vmaf))

    split1 = f"[0:v]split={no_of_metrics}"
    split2 = f"[1:v]split={no_of_metrics}"
    filters = []

    if psnr:
        split1 += "[yuv_psnr]"
        split2 += "[hevc_psnr]"
        filters.append(f"[hevc_psnr][yuv_psnr]"
                       f"psnr=stats_file={psnr_log_name}")
    if ssim:
        split1 += "[yuv_ssim]"
        split2 += "[hevc_ssim]"
        filters.append(f"[hevc_ssim][yuv_ssim]"
                       f"ssim=stats_file={ssim_log_name}")
    if vmaf:
        split1 += "[yuv_vmaf]"
        split2 += "[hevc_vmaf]"
        filters.append(f"[hevc_vmaf][yuv_vmaf]"
                       f"libvmaf=model_path={vmaf_model_dest_path1.name}:"
                       f"log_path={vmaf_log_name}:"
                       f"log_fmt=json")

    ffmpeg_filter = f"{split1}; "\
                    f"{split2}; "\
                    f"{'; '.join(filters)}"

    # The path of the HEVC file as well as the log files will contain spaces,
    # so the easiest solution is to change the working directory and
    # use relative filepaths.

    ffmpeg_command = (
        # Change working directory to make relative paths work.
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
              "-filter_complex", ffmpeg_filter,
              "-f", "null", "-",
    )

    try:
        console_log.debug(f"ffmpeg: Computing metrics")
        console_log.debug(f"ffmpeg: Input 1: '{encoding_run.input_sequence.get_filepath().name}'")
        console_log.debug(f"ffmpeg: Input 2: '{encoding_run.output_file.get_filepath().name}'")
        if psnr:
            console_log.debug(f"ffmpeg: PSNR log: '{psnr_log_name}'")
        if ssim:
            console_log.debug(f"ffmpeg: SSIM log: '{ssim_log_name}'")
        if vmaf:
            console_log.debug(f"ffmpeg: VMAF log: '{vmaf_log_name}'")

        subprocess.check_output(
            subprocess.list2cmdline(ffmpeg_command),
            stderr=subprocess.STDOUT,
            shell=True
        )

        # Remove the temporary VMAF model file.
        os.remove(vmaf_model_dest_path1)
        os.remove(vmaf_model_dest_path2)

        # Ugly but simple.

        psnr_avg = None
        if psnr:
            frame_psnrs = []
            with encoding_run.psnr_log_path.open("r") as psnr_log:
                lines = psnr_log.readlines()
                for line in lines:
                    for item in _PSNR_PATTERN.fullmatch(line).groups():
                        frame_psnrs.append(float(item))
                psnr_avg = sum(frame_psnrs) / len(lines)

        ssim_avg = None
        if ssim:
            frame_ssims = []
            with encoding_run.ssim_log_path.open("r") as ssim_log:
                lines = ssim_log.readlines()
                for line in lines:
                    for item in _SSIM_PATTERN.fullmatch(line).groups():
                        frame_ssims.append(float(item))
                ssim_avg = sum(frame_ssims) / len(lines)

        vmaf_avg = None
        if vmaf:
            with encoding_run.vmaf_log_path.open("r") as vmaf_log:
                for line in vmaf_log.readlines():
                    match = _VMAF_PATTERN.fullmatch(line)
                    if match:
                        vmaf_avg = float(match.groups()[0])
                        break

        return psnr_avg, ssim_avg, vmaf_avg

    except Exception as exception:
        console_log.error(f"ffmpeg: Failed to compute metrics")
        if isinstance(exception, subprocess.CalledProcessError):
            console_log.error(exception.output.decode())
        raise
