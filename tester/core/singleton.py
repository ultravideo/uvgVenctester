#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module defines the Singleton class that classes meant to be singletons
should inherit.
Don't ask how it works, it just works.
"""

class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]
