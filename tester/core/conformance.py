import subprocess
from tester import console_log
import tester.core.cfg as cfg
import tester.core.test as test
import os


def validate_conformance():
    try:
        subprocess.check_call((str(cfg.Cfg().hevc_reference_decoder), "--help"),
                              stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        console_log.warning(f"CONFORMANCE: Can't find HEVC reference_decoder: {cfg.Cfg().hevc_reference_decoder}")
    except subprocess.CalledProcessError:
        pass


def check_hevc_conformance(encoding_run: test.EncodingRun):
    assert encoding_run.output_file.get_filepath().exists()

    cmd = (
        cfg.Cfg().hevc_reference_decoder,
        "-b", encoding_run.output_file.get_filepath(),
        "-o", os.devnull
    )
    with open(encoding_run.conformance_log_path, "w") as log:
        try:
            handle = subprocess.Popen(
                cmd,
                stderr=subprocess.STDOUT,
                stdout=subprocess.PIPE
            )
            conforming = True
            for line in iter(handle.stdout.readline, ''):
                if not line:
                    break
                line = line.decode()
                log.write(line.strip() + "\n")
                if line.startswith("POC") and "(OK)" not in line:
                    conforming = False
        except subprocess.CalledProcessError:
            return False
        return conforming
