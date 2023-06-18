import os

from deadcode.data_types import Args
from deadcode.utils.path_matching import does_path_match_patterns


def find_python_filenames(args: Args):
    """Recursively searches for Python filenames in provided paths."""
    python_filenames = []
    for path in args.paths:
        if does_path_match_patterns(path, args.exclude):
            continue

        if os.path.isfile(path):
            filename = path
            if os.path.splitext(filename)[1] == ".py":
                python_filenames.append(filename)
        else:
            for path, _, filenames in os.walk(path):
                if does_path_match_patterns(path, args.exclude):
                    continue

                for f in filenames:
                    filename = os.path.join(path, f)
                    if os.path.splitext(filename)[1] == ".py" and not does_path_match_patterns(filename, args.exclude):
                        python_filenames.append(filename)

    return python_filenames
