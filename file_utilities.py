#Contains utility functions for dealing with files

import os

def create_file_at_path_if_nonexistent(path):
    """Creates an empty file at the specified path if it does not exist"""
    if not os.path.exists(path):
        with open(path, "w") as file:
            pass

def read_bytes_at_path(path):
    with open(path, "rb") as file:
        return file.read()

def write_bytes_at_path(data, path):
    with open(path, "wb") as file:
        file.write(data)