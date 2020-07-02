import os

class CsvFile():
    def __init__(self, filepath: str):
        self.directory = os.path.dirname(filepath)
        self.filepath = filepath
        self.header_names = []

        if self.directory and not os.path.exists(self.directory):
            os.makedirs(self.directory)

        with open(self.filepath, "w") as file:
            pass

    def set_header_names(self, header_names: list):
        self.header_names = header_names
        with open(self.filepath, "w") as file:
            file.write(f"{';'.join(self.header_names)}\n")

    def add_entry(self, fields: list):
        assert(len(fields) == len(self.header_names))
        fields = [str(field) for field in fields]
        with open(self.filepath, "a") as file:
            file.write(f"{';'.join(fields)}\n")
