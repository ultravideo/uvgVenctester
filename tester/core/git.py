#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module defines functionality related to Git.
"""

from core import *
import subprocess
import os

class GitRepo(object):
    def __init__(self, local_repo_path: str):
        self.local_repo_path: str = local_repo_path
        self.git_dir: str = os.path.join(local_repo_path, '.git')

    def clone(self, remote_url: str) -> (str, bytes, subprocess.CalledProcessError):
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

    def checkout(self, revision: str) -> (str, bytes, subprocess.CalledProcessError):
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

    def rev_parse(self, revision: str) -> (str, bytes, subprocess.CalledProcessError):
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
