from logging import getLogger
from pathlib import Path

from deadcode.data_types import Args
from deadcode.utils.normalize_path import normalize_path
from deadcode.visitor.ignore import _match

logger = getLogger()


def find_python_filenames(args: Args) -> list[str]:
    filenames = []
    paths: list[str] = list(args.paths)
    while paths:
        path = Path(paths.pop())

        if _match(path, args.exclude):
            if args.verbose:
                logger.info(f'Ignoring: {normalize_path(path)}')
            continue

        if path.is_file() and path.suffix == '.py':
            filenames.append(normalize_path(path))
        elif path.is_dir():
            paths += list([normalize_path(p) for p in path.glob('*')])
        elif not path.exists():
            # TODO: unify error logging and reporting
            # Maybe a cli flag could be added to stop on error
            logger.error(f'Error: {path} could not be found.')

    if args.verbose:
        sep = '\n  - '
        logger.info(f'Files to be checked for dead code: {sep.join(filenames)}')
    return filenames
