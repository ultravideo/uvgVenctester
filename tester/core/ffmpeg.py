"""This module defines functionality related to ffmpeg."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import tester.core.csv as csv
import tester.core.test as test
import tester.core.cfg as cfg
from tester.core.log import console_log

# Compile Regex patterns only once for better performance.
_PSNR_PATTERN: re.Pattern = re.compile(r".*psnr_avg:([0-9]+.[0-9]+).*", re.DOTALL)
_SSIM_PATTERN: re.Pattern = re.compile(r".*All:([0-9]+.[0-9]+).*", re.DOTALL)
_VMAF_PATTERN: re.Pattern = re.compile(r".*\"VMAF score\":([0-9]+.[0-9]+).*", re.DOTALL)


def ffmpeg_validate_config():
    try:
        output = subprocess.check_output("ffmpeg -version", shell=True)
        if csv.CsvField.VMAF_AVG in cfg.Cfg().csv_enabled_fields \
                or csv.CsvField.VMAF_STDEV in cfg.Cfg().csv_enabled_fields:
            for line in output.decode().split("\n"):
                if str(line).startswith("configuration") and not "--enable-libvmaf" in line:
                    console_log.error("Ffmpeg: VMAF field enabled in CSV but ffmpeg is not "
                                      "configured with --enable-libvmaf")
                    raise RuntimeError

    except FileNotFoundError:
        console_log.error(f"Ffmpeg: Executable 'ffmpeg' does not exist")
        raise RuntimeError


def compute_metrics(encoding_run: test.EncodingRun,
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
    if vmaf:
        vmaf_model_src_path1 = cfg.Cfg().vmaf_repo_path / "model" / "vmaf_v0.6.1.pkl"
        vmaf_model_src_path2 = cfg.Cfg().vmaf_repo_path / "model" / "vmaf_v0.6.1.pkl.model"
        vmaf_model_dest_path1 = encoding_run.output_file.get_filepath().parent / "vmaf_v0.6.1.pkl"
        vmaf_model_dest_path2 = encoding_run.output_file.get_filepath().parent / "vmaf_v0.6.1.pkl.model"
        shutil.copy(str(vmaf_model_src_path1), str(vmaf_model_dest_path1))
        shutil.copy(str(vmaf_model_src_path2), str(vmaf_model_dest_path2))

    # Build the filter based on which metrics are to be computed:

    no_of_metrics = sum(int(boolean) for boolean in (psnr, ssim, vmaf))

    # Adjust for frame step (it could be that only every <step>th frame of the input sequence was encoded).
    split1 = f"[0:v]select=not(mod(n\\,{cfg.Cfg().frame_step_size}))[select1_out]; " \
             f"[select1_out]split={no_of_metrics}"
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

    # VTM output is in YUV format, so use different command.
    if encoding_run.decoded_output_file_path:
        encoding_run.encoder._decode(encoding_run)
        ffmpeg_command = (
            # Change working directory to make relative paths work.
            "cd", f"{encoding_run.output_file.get_filepath().parent}",
            "&&", "ffmpeg",

                  # YUV input
                  "-s:v", f"{encoding_run.input_sequence.get_width()}x{encoding_run.input_sequence.get_height()}",
                  "-pix_fmt", f"{encoding_run.input_sequence.get_pixel_format()}",
                  "-f", "rawvideo",
                  "-r", f"{cfg.Cfg().frame_step_size}",  # multiply framerate by step
                  "-ss", f"{encoding_run.param_set.get_seek()}",
                  "-t", f"{encoding_run.frames * cfg.Cfg().frame_step_size}",
                  "-i", f"{encoding_run.input_sequence.get_filepath()}",

                  # YUV output decoded from VVC output
                  "-s:v", f"{encoding_run.output_file.get_width()}x{encoding_run.output_file.get_height()}",
                  "-pix_fmt", f"{encoding_run.input_sequence.get_pixel_format()}",
                  "-f", "rawvideo",
                  "-r", "1",
                  "-t", f"{encoding_run.frames}",
                  "-i", f"{encoding_run.decoded_output_file_path.name}",

                  "-c:v", "rawvideo",
                  "-filter_complex", ffmpeg_filter,
                  "-f", "null", "-",
        )

    else:

        ffmpeg_command = (
            "cd", f"{encoding_run.output_file.get_filepath().parent}",
            "&&", "ffmpeg",

                  # YUV input
                  "-s:v", f"{encoding_run.input_sequence.get_width()}x{encoding_run.input_sequence.get_height()}",
                  "-pix_fmt", f"{encoding_run.input_sequence.get_pixel_format()}",
                  "-f", "rawvideo",
                  "-r", f"{cfg.Cfg().frame_step_size}",
                  "-ss", f"{encoding_run.param_set.get_seek()}",
                  "-t", f"{encoding_run.frames * cfg.Cfg().frame_step_size}",
                  "-i", f"{encoding_run.input_sequence.get_filepath()}",

                  # HEVC output
                  "-r", "1",
                  "-t", f"{encoding_run.frames}",
                  "-i", f"{encoding_run.output_file.get_filepath().name}",

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

        if vmaf:
            # Remove the temporary VMAF model file.
            os.remove(vmaf_model_dest_path1)
            os.remove(vmaf_model_dest_path2)

        if encoding_run.decoded_output_file_path:
            os.remove(encoding_run.decoded_output_file_path)

        # Ugly but simple:

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


def generate_dummy_sequence() -> Path:

    dummy_sequence_path = cfg.Cfg().tester_sequences_dir_path / '_dummy.yuv'

    console_log.debug(f"ffmpeg: Dummy sequence '{dummy_sequence_path}' already exists")

    if dummy_sequence_path.exists():
        console_log.debug(f"ffmpeg: Generating dummy sequence '{dummy_sequence_path}'")
        return dummy_sequence_path

    ffmpeg_cmd = (
        "ffmpeg",
        "-f", "lavfi",
        "-i", "mandelbrot=size=16x16",
        "-vframes", "60",
        "-pix_fmt", "yuv420p",
        "-f", "yuv4mpegpipe", str(dummy_sequence_path),
    )

    try:
        subprocess.check_output(subprocess.list2cmdline(ffmpeg_cmd),
                                shell=True,
                                stderr=subprocess.STDOUT)
    except Exception as exception:
        console_log.error(f"ffmpeg: Failed to generate dummy sequence '{dummy_sequence_path}'")
        if isinstance(exception, subprocess.CalledProcessError):
            console_log.error(exception.output.decode())
        raise

    return dummy_sequence_path
