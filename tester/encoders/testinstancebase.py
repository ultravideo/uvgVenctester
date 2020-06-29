#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module defines the abstract TestInstanceBase class that each encoder TestInstance
should inherit. TestInstanceBase defines the interface through which the tester core interacts
with the encoders.
"""

class TestInstanceBase:
    def __init__(self):
        pass

    def __eq__(self, other):
        raise NotImplementedError

    def get_encoder_name(self):
        raise NotImplementedError

    def get_name(self):
        raise NotImplementedError

    def get_defines(self):
        raise NotImplementedError

    def get_revision(self):
        raise NotImplementedError

    def get_cl_args(self):
        raise NotImplementedError

    def build(self):
        raise NotImplementedError

    def cl_args_are_valid(self):
        raise NotImplementedError
