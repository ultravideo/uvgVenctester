#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module defines functionality related to creating a CSV file.
"""

from .cfg import *
import os

class CsvFile():
    """Represents a single CSV file."""

    def __init__(self, filepath: str, field_names: list):
        """Creates a new CSV file and initializes it with the names of the fields.
        If the file doesn't exist yet, it is created. If it already exists, the old file is
        discarded and a new file is created. Field names are separated automatically.
        @param filepath The absolute path of the CSV file.
        @param field_names A list of the field names (i.e. the header), from left to right.
        Must only contain strings."""
        self.directory = os.path.dirname(filepath)
        self.filepath = filepath
        self.field_names = field_names

        # Create the new CSV file.
        if self.directory and not os.path.exists(self.directory):
            os.makedirs(self.directory)
        with open(self.filepath, "w") as file:
            file.write(f"{Cfg().csv_field_separator.join(self.field_names)}\n")

    def new_row(self, field_values: list):
        """Adds a new row with the given values for each field. Values are separated automatically.
        @param field_values: The values for each field, from left to right. The values can be any
        objects that can be converted to strings."""
        assert len(field_values) == len(self.field_names)
        field_values = [str(field) for field in field_values]
        with open(self.filepath, "a") as file:
            file.write(f"{Cfg().csv_field_separator.join(field_values)}\n")
