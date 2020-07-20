#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module defines functionality related to Git.
"""

import subprocess
import os

class GitRepository(object):
    """Represents a Git repository."""
    def __init__(self,
                 local_repo_path: str):
        """@param local_repo_path The absolute path to the local repository
        (the directory doesn't need to exist)."""
        self.local_repo_path: str = local_repo_path
        self.git_dir: str = os.path.join(local_repo_path, '.git')

    def exists(self) -> bool:
        """Returns True if the local repository exists."""
        return os.path.exists(self.local_repo_path)

    def clone(self,
              remote_url: str) -> (str, bytes, subprocess.CalledProcessError):
        """Clones the given remote. The repository will be placed in self.local_repo_path.
        @param remote_url The SSH URL of the remote repository.
        @return A tuple of three items:
        -The command executed on the command line (for logging etc.).
        -The output of the command as a bytes object. None if an exception was raised.
        -An exception object. None if no exception was raised."""
        clone_cmd: tuple = (
            "git",
            "clone", remote_url, self.local_repo_path,
        )
        cmd_as_str: str = subprocess.list2cmdline(clone_cmd)
        try:
            output: bytes = subprocess.check_output(clone_cmd, stderr=subprocess.STDOUT)
            return cmd_as_str, output, None
        except subprocess.CalledProcessError as exception:
            return cmd_as_str, None, exception

    def checkout(self,
                 revision: str) -> (str, bytes, subprocess.CalledProcessError):
        """Checks out to the given revision.
        @param revision The revision to checkout to. The revision can be any string that is a valid
        parameter to git checkout.
        @return A tuple of three items:
        -The command executed on the command line (for logging etc.).
        -The output of the command as a bytes object. None if an exception was raised.
        -An exception object. None if no exception was raised."""
        checkout_cmd: tuple = (
            "git",
            "--work-tree", self.local_repo_path,
            "--git-dir", self.git_dir,
            "checkout", revision,
        )
        cmd_as_str: str = subprocess.list2cmdline(checkout_cmd)
        try:
            output: bytes = subprocess.check_output(checkout_cmd, stderr=subprocess.STDOUT)
            return cmd_as_str, output, None
        except subprocess.CalledProcessError as exception:
            return cmd_as_str, None, exception

    def pull_origin_master(self) -> (str, bytes, subprocess.CalledProcessError):
        """Pulls the master branch of the 'origin' remote.
        @return A tuple of three items:
        -The command executed on the command line (for logging etc.).
        -The output of the command as a bytes object. None if an exception was raised.
        -An exception object. None if no exception was raised."""
        pull_cmd: tuple = (
            "git",
            "--work-tree", self.local_repo_path,
            "--git-dir", self.git_dir,
            "pull", "origin", "master",
        )
        cmd_as_str: str = subprocess.list2cmdline(pull_cmd)
        try:
            output: bytes = subprocess.check_output(pull_cmd, stderr=subprocess.STDOUT)
            return cmd_as_str, output, None
        except subprocess.CalledProcessError as exception:
            return cmd_as_str, None, exception

    def fetch_all(self) -> (str, bytes, subprocess.CalledProcessError):
        """Fetches all.
        @return A tuple of three items:
        -The command executed on the command line (for logging etc.).
        -The output of the command as a bytes object. None if an exception was raised.
        -An exception object. None if no exception was raised."""
        fetch_cmd: tuple = (
            "git",
            "--work-tree", self.local_repo_path,
            "--git-dir", self.git_dir,
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
        """Executes git rev-parse to convert the user-given revision to a full commit hash.
        @param revision The user-given revision to rev-parse.
        @return A tuple of three items:
        -The command executed on the command line (for logging etc.).
        -The output of the command as a bytes object. None if an exception was raised.
        -An exception object. None if no exception was raised."""
        rev_parse_cmd: tuple = (
            "git",
            "--work-tree", self.local_repo_path,
            "--git-dir", self.git_dir,
            "rev-parse", revision,
        )
        cmd_as_str: str = subprocess.list2cmdline(rev_parse_cmd)
        try:
            output: bytes = subprocess.check_output(rev_parse_cmd, stderr=subprocess.STDOUT)
            return cmd_as_str, output, None
        except subprocess.CalledProcessError as exception:
            return cmd_as_str, None, exception
