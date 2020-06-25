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

    def build(self):
        raise NotImplementedError
