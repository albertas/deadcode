from logging import getLogger
from typing import List
from pathlib import Path

from deadcode.data_types import Args
from deadcode.visitor.ignore import _match

logger = getLogger()


def find_python_filenames(args: Args) -> List[str]:
    filenames = []
    paths: List[str] = list(args.paths)
    while paths:
        path = Path(paths.pop())

        if _match(path, args.exclude):
            if args.verbose:
                logger.info(f'Ignoring: {path}')
            continue

        if path.is_file() and path.suffix == '.py':
            filenames.append(str(path))
        elif path.is_dir():
            paths += list([str(p) for p in path.glob('*')])
        elif not path.exists():
            # TODO: unify error logging and reporting
            # Maybe a cli flag could be added to stop on error
            logger.error(f'Error: {path} could not be found.')

    if args.verbose:
        sep = '\n  - '
        logger.info(f'Files to be checked for dead code: {sep.join(filenames)}')
    return filenames


# Should show errors, if files do not exist.
# Could mock directories: os.path.isfile os.walk -> replace this one with rglob

# Should use list dir myself.

# TODO: Whats the solution for mocking the file system checking?
# Every single provided file is assumed to exist.


# # TODO: investigate what can be reused from this module
#     Loop over all given paths, abort if any ends with .pyc, add the other given
#     files (even those not ending with .py) and collect all .py files under the
#     given directories.
