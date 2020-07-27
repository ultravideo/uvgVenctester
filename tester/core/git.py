"""This module defines functionality related to Git."""

import subprocess
from pathlib import Path


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
        clone_cmd: tuple = (
            "git",
            "clone", remote_url, self._local_repo_path,
        )
        cmd_as_str: str = subprocess.list2cmdline(clone_cmd)
        try:
            output: bytes = subprocess.check_output(clone_cmd, stderr=subprocess.STDOUT)
            return cmd_as_str, output, None
        except subprocess.CalledProcessError as exception:
            return cmd_as_str, None, exception

    def checkout(self,
                 revision: str) -> (str, bytes, subprocess.CalledProcessError):
        checkout_cmd: tuple = (
            "git",
            "--work-tree", self._local_repo_path,
            "--git-dir", self._git_dir_path,
            "checkout", revision,
        )
        cmd_as_str: str = subprocess.list2cmdline(checkout_cmd)
        try:
            output: bytes = subprocess.check_output(checkout_cmd, stderr=subprocess.STDOUT)
            return cmd_as_str, output, None
        except subprocess.CalledProcessError as exception:
            return cmd_as_str, None, exception

    def pull_origin_master(self) -> (str, bytes, subprocess.CalledProcessError):
        pull_cmd: tuple = (
            "git",
            "--work-tree", self._local_repo_path,
            "--git-dir", self._git_dir_path,
            "pull", "origin", "master",
        )
        cmd_as_str: str = subprocess.list2cmdline(pull_cmd)
        try:
            output: bytes = subprocess.check_output(pull_cmd, stderr=subprocess.STDOUT)
            return cmd_as_str, output, None
        except subprocess.CalledProcessError as exception:
            return cmd_as_str, None, exception

    def fetch_all(self) -> (str, bytes, subprocess.CalledProcessError):
        fetch_cmd: tuple = (
            "git",
            "--work-tree", self._local_repo_path,
            "--git-dir", self._git_dir_path,
            "fetch", "--all",
        )
        cmd_as_str: str = subprocess.list2cmdline(fetch_cmd)
        try:
            output: bytes = subprocess.check_output(fetch_cmd, stderr=subprocess.STDOUT)
            return cmd_as_str, output, None
        except subprocess.CalledProcessError as exception:
            return cmd_as_str, None, exception

    def rev_parse(self,
                  revision: str) -> (str, bytes, subprocess.CalledProcessError):
        rev_parse_cmd: tuple = (
            "git",
            "--work-tree", self._local_repo_path,
            "--git-dir", self._git_dir_path,
            "rev-parse", revision,
        )
        cmd_as_str: str = subprocess.list2cmdline(rev_parse_cmd)
        try:
            output: bytes = subprocess.check_output(rev_parse_cmd, stderr=subprocess.STDOUT)
            return cmd_as_str, output, None
        except subprocess.CalledProcessError as exception:
            return cmd_as_str, None, exception
