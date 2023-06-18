import re
from typing import Dict

from deadcode.utils.path_matching import does_path_match_patterns
from deadcode.data_types import (
    Args,
    FileContent,
    Filename,
    VariableName,
    FilenameWithPosition,
)


def parse_global_names(files: Dict[Filename, FileContent], args: Args) -> Dict[VariableName, FilenameWithPosition]:
    patterns = [
        re.compile(r"^(\w+)\s*="),
        re.compile(r"^def\s+(\w+)\s*\(?"),
        re.compile(r"^class\s+(\w+)\s*\(?:?"),
    ]

    global_variable_names = {}
    for filename, file_content in files.items():
        if does_path_match_patterns(filename, args.ignore_names_in_files):
            continue

        for pattern in patterns:
            for line_nr, line in enumerate(file_content.split("\n"), 1):
                if global_variable_name_match := re.search(pattern, line):
                    variable_name = global_variable_name_match.groups()[0]
                    column_nr = global_variable_name_match.regs[-1][0]
                    global_variable_names[variable_name] = f"{filename}:{line_nr}:{column_nr}:"

    return global_variable_names
