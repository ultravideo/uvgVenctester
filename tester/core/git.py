"""This module defines functionality related to Git."""

import subprocess
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Union

from tester.core.log import console_log


def git_validate_config():
    try:
        subprocess.check_output(["git", "--version"],)
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
            ls_remote_cmd,
        )
        return True
    except subprocess.CalledProcessError:
        return False


class GitRepository(object):
    """Represents a Git repository."""
    has_fetched = defaultdict(lambda: False)

    def __init__(self,
                 local_repo_path: Path,
                 remote: Union[str, None] = None):
        self._local_repo_path: Path = local_repo_path
        self._git_dir_path: Path = local_repo_path / ".git"
        self._remote_url = remote
        if remote is not None and not self.exists():
            self._clone()
        else:
            self.check_remote_url()

    def exists(self) -> bool:
        return self._local_repo_path.exists() and self._git_dir_path.exists()

    def check_remote_url(self):
        if self._remote_url is None:
            return
        cmd = [
            "git",
            "--work-tree", str(self._local_repo_path),
            "--git-dir", str(self._git_dir_path),
            "remote",
            "get-url",
            "origin"
        ]
        try:
            output = subprocess.check_output(cmd).decode()
            if output.strip() == self._remote_url:
                return
            else:
                subprocess.check_output(
                    [
                        "git",
                        "--work-tree", str(self._local_repo_path),
                        "--git-dir", str(self._git_dir_path),
                        "remote",
                        "set-url",
                        "origin",
                        self._remote_url
                    ]
                )
        except subprocess.CalledProcessError as e:
            console_log.error(f"[git] Failed to get or set remote url for {self._git_dir_path}")
            raise e

    def _clone(self) -> (str, bytes, subprocess.CalledProcessError):
        if self._git_dir_path.exists():
            return
        clone_cmd: tuple = (
            "git",
            "clone", self._remote_url, str(self._local_repo_path),
        )
        cmd_as_str: str = subprocess.list2cmdline(clone_cmd)
        output: bytes = subprocess.check_output(
            clone_cmd,
            stderr=subprocess.STDOUT
        )
        console_log.debug(f"[git] succesfully cloned {self._remote_url} with {output.decode()}")

    def checkout(self,
                 revision: str) -> (str, bytes):
        checkout_cmd: tuple = (
            "git",
            "--work-tree", str(self._local_repo_path),
            "--git-dir", str(self._git_dir_path),
            "checkout", revision,
        )
        cmd_as_str: str = subprocess.list2cmdline(checkout_cmd)

        output: bytes = subprocess.check_output(
            checkout_cmd,
            stderr=subprocess.STDOUT
        )
        return cmd_as_str, output

    def pull(self, remote: str = "origin", branch: str = "master") -> (str, bytes):
        pull_cmd: tuple = (
            "git",
            "--work-tree", str(self._local_repo_path),
            "--git-dir", str(self._git_dir_path),
            "pull", remote, branch
        )
        cmd_as_str: str = subprocess.list2cmdline(pull_cmd)
        output: bytes = subprocess.check_output(
            pull_cmd,
            stderr=subprocess.STDOUT
        )
        return cmd_as_str, output

    def fetch_all(self) -> (bytes):
        if self.has_fetched[self._remote_url]:
            return b""
        fetch_cmd: tuple = (
            "git",
            "--work-tree", str(self._local_repo_path),
            "--git-dir", str(self._git_dir_path),
            "fetch", "--all",
        )
        output: bytes = subprocess.check_output(
            fetch_cmd
        )
        self.has_fetched[self._remote_url] = True
        return output

    def rev_parse(self,
                  revision: str) -> (str, bool):
        rev_parse_cmd: tuple = (
            "git",
            "--work-tree", str(self._local_repo_path),
            "--git-dir", str(self._git_dir_path),
            "rev-parse", revision,
        )

        output = subprocess.check_output(
            rev_parse_cmd,
            shell=True,
            stderr=subprocess.STDOUT
        ).decode().strip()

        return output, output.startswith(revision)

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
            out = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode()
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
            output = subprocess.check_output(cmd,
                                             stderr=subprocess.STDOUT).decode().split("\n")
            data["Date"] = datetime.fromisoformat(output[0])
            data["Author"] = output[1]
            data["commit"] = output[2]
            data["Message"] = "\n".join(output[3:])
            return data

        except subprocess.CalledProcessError:
            return {}
