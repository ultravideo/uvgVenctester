"""This module defines functionality related to Git."""

import subprocess
from datetime import datetime
from pathlib import Path

from tester.core.log import console_log


def git_validate_config():
    try:
        subprocess.check_output("git --version", shell=True)
    except FileNotFoundError:
        console_log.error("Git: Executable 'git' was not found")
        raise RuntimeError


def git_remote_exists(remote_url: str) -> bool:
    try:
        ls_remote_cmd = (
            "git",
            "ls-remote", remote_url
        )
        subprocess.check_output(
            subprocess.list2cmdline(ls_remote_cmd),
            shell=True
        )
        return True
    except subprocess.CalledProcessError:
        return False


class GitRepository(object):
    """Represents a Git repository."""

    def __init__(self,
                 local_repo_path: Path):
        self._local_repo_path: Path = local_repo_path
        self._git_dir_path: Path = local_repo_path / ".git"

    def exists(self) -> bool:
        return self._local_repo_path.exists() and self._git_dir_path.exists()

    def clone(self,
              remote_url: str) -> (str, bytes, subprocess.CalledProcessError):
        if self._git_dir_path.exists():
            return None, None, None
        clone_cmd: tuple = (
            "git",
            "clone", remote_url, str(self._local_repo_path),
        )
        cmd_as_str: str = subprocess.list2cmdline(clone_cmd)
        try:
            output: bytes = subprocess.check_output(
                subprocess.list2cmdline(clone_cmd),
                shell=True,
                stderr=subprocess.STDOUT
            )
            return cmd_as_str, output, None
        except subprocess.CalledProcessError as exception:
            return cmd_as_str, None, exception

    def checkout(self,
                 revision: str) -> (str, bytes, subprocess.CalledProcessError):
        checkout_cmd: tuple = (
            "git",
            "--work-tree", str(self._local_repo_path),
            "--git-dir", str(self._git_dir_path),
            "checkout", revision,
        )
        cmd_as_str: str = subprocess.list2cmdline(checkout_cmd)
        try:
            output: bytes = subprocess.check_output(
                subprocess.list2cmdline(checkout_cmd),
                shell=True,
                stderr=subprocess.STDOUT
            )
            return cmd_as_str, output, None
        except subprocess.CalledProcessError as exception:
            return cmd_as_str, None, exception

    def pull(self, remote: str = "origin", branch: str = "master") -> (str, bytes, subprocess.CalledProcessError):
        pull_cmd: tuple = (
            "git",
            "--work-tree", str(self._local_repo_path),
            "--git-dir", str(self._git_dir_path),
            "pull", remote, branch
        )
        cmd_as_str: str = subprocess.list2cmdline(pull_cmd)
        try:
            output: bytes = subprocess.check_output(
                subprocess.list2cmdline(pull_cmd),
                shell=True,
                stderr=subprocess.STDOUT
            )
            return cmd_as_str, output, None
        except subprocess.CalledProcessError as exception:
            return cmd_as_str, None, exception

    def fetch_all(self) -> (str, bytes, subprocess.CalledProcessError):
        fetch_cmd: tuple = (
            "git",
            "--work-tree", str(self._local_repo_path),
            "--git-dir", str(self._git_dir_path),
            "fetch", "--all",
        )
        cmd_as_str: str = subprocess.list2cmdline(fetch_cmd)
        try:
            output: bytes = subprocess.check_output(
                subprocess.list2cmdline(fetch_cmd),
                shell=True,
            )
            return cmd_as_str, output, None
        except subprocess.CalledProcessError as exception:
            return cmd_as_str, None, exception

    def rev_parse(self,
                  revision: str) -> (str, bytes, subprocess.CalledProcessError):
        rev_parse_cmd: tuple = (
            "git",
            "--work-tree", str(self._local_repo_path),
            "--git-dir", str(self._git_dir_path),
            "rev-parse", revision,
        )
        cmd_as_str: str = subprocess.list2cmdline(rev_parse_cmd)
        try:
            output: bytes = subprocess.check_output(
                subprocess.list2cmdline(rev_parse_cmd),
                shell=True,
                stderr=subprocess.STDOUT
            )
            return cmd_as_str, output, None
        except subprocess.CalledProcessError as exception:
            return cmd_as_str, None, exception

    def get_latest_commit_between(self, start: datetime, finish: datetime, branch="origin/master"):
        cmd = (
            "git",
            "--work-tree", str(self._local_repo_path),
            "--git-dir", str(self._git_dir_path),
            "log", "-1",
            "--format=%H",
            "--until", finish.strftime("%Y-%m-%d"),
            "--since", start.strftime("%Y-%m-%d"),
            branch
        )
        try:
            out = subprocess.check_output(subprocess.list2cmdline(cmd), shell=True, stderr=subprocess.STDOUT).decode()
            return out.strip()

        except subprocess.CalledProcessError as e:
            raise e

    def get_commit_info(self, commit: str):
        cmd = (
            "git",
            "--work-tree", str(self._local_repo_path),
            "--git-dir", str(self._git_dir_path),
            "log",
            "-1",
            "--format=%aI%n%an%n%H%n%s%n%b",
            commit
        )
        try:
            data = {}
            output = subprocess.check_output(subprocess.list2cmdline(cmd),
                                             shell=True,
                                             stderr=subprocess.STDOUT).decode().split("\n")
            data["Date"] = datetime.fromisoformat(output[0])
            data["Author"] = output[1]
            data["commit"] = output[2]
            data["Message"] = "\n".join(output[3:])
            return data

        except subprocess.CalledProcessError:
            return {}
