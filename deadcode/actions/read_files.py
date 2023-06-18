from typing import Dict, List

from deadcode.data_types import FileContent, Filename


def read_files(filenames: List[Filename]) -> Dict[Filename, FileContent]:
    files = {}
    for filename in filenames:
        with open(filename, "r") as f:
            files[filename] = f.read()
    return files
