from fnmatch import fnmatch
from typing import List

from deadcode.data_types import Pathname


def does_path_match_patterns(path: Pathname, patterns: List[Pathname]) -> bool:
    if path != ".":
        for pattern in patterns:
            if (
                fnmatch(path, pattern)
                or fnmatch(path, f"{pattern}*")
                or fnmatch(path, f"./{pattern}")
                or fnmatch(path, f"./{pattern}*")
            ):
                return True
    return False
