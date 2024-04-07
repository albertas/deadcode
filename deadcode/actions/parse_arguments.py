import argparse
from typing import Any, Dict, List, Optional
import sys
import os

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from deadcode.data_types import Args
from deadcode.utils.flatten_lists import flatten_lists_of_comma_separated_values


def parse_arguments(args: Optional[List[str]]) -> Args:
    """Parses arguments (execution options) for deadcode tool.

    Arguments for DeadCode can be provided via:
    - via command line
    - via pyproject.toml
    - via function arguments
    """

    if not args:
        args = sys.argv[1:]

    # Docs: https://docs.python.org/3/library/argparse.html
    parser = argparse.ArgumentParser()
    parser.add_argument('paths', help='Paths where to search for python files', nargs='+')
    parser.add_argument(
        '--fix',
        help='Automatically remove detected unused code expressions from the code base.',
        action='store_true',
        default=False,
    )
    parser.add_argument(
        '--dry',
        help='Show changes which would be made in files with --fix option.',
        nargs='*',
        action='append',
        default=[['__all_files__']],
        type=str,
    )
    parser.add_argument(
        '--exclude',
        help='Filenames (or path expressions), which will be completely skipped without being analysed.',
        nargs='*',
        action='append',
        default=[],
        type=str,
    )
    parser.add_argument(
        '--ignore-names',
        help=(
            'Removes provided list of names from the output. '
            'Regexp expressions to match multiple names can also be provided.'
        ),
        nargs='*',
        action='append',
        default=[],
        type=str,
    )
    parser.add_argument(
        '--ignore-bodies-of',
        help='Ignores body of an expression if its name matches any of the provided names.',
        nargs='*',
        action='append',
        default=[],
        type=str,
    )
    parser.add_argument(
        '--ignore-bodies-if-decorated-with',
        help='Ignores body of an expression if its decorated with one of the provided decorator names.',
        nargs='*',
        action='append',
        default=[],
        type=str,
    )
    parser.add_argument(
        '--ignore-bodies-if-inherits-from',
        help='Ignores body of a class if it inherits from any of the provided class names.',
        nargs='*',
        action='append',
        default=[],
        type=str,
    )
    parser.add_argument(
        '--ignore-definitions',
        help=(
            'Ignores definition (including name and body) if a '
            'name of an expression matches any of the provided ones.'
        ),
        nargs='*',
        action='append',
        default=[],
        type=str,
    )
    parser.add_argument(
        '--ignore-definitions-if-inherits-from',
        help=(
            'Ignores definition (including name and body) of a class if '
            'it inherits from any of the provided class names.'
        ),
        nargs='*',
        action='append',
        default=[],
        type=str,
    )
    parser.add_argument(
        '--ignore-definitions-if-decorated-with',
        help=(
            'Ignores definition (including name and body) of an expression, '
            'which is decorated with any of the provided decorator names.'
        ),
        nargs='*',
        action='append',
        default=[],
        type=str,
    )

    parser.add_argument(
        '--ignore-if-decorated-with',
        help='Ignores both the name and its definition if its decorated with one of the provided decorator names.',
        nargs='*',
        action='append',
        default=[],
        type=str,
    )
    parser.add_argument(
        '--ignore-if-inherits-from',
        help='Ignores both the name and its definition if the class inerits from the provided class name.',
        nargs='*',
        action='append',
        default=[],
        type=str,
    )

    parser.add_argument(
        '--ignore-names-if-inherits-from',
        help='Ignores names of classes, which inherit from provided class names.',
        nargs='*',
        action='append',
        default=[],
        type=str,
    )
    parser.add_argument(
        '--ignore-names-if-decorated-with',
        help='Ignores names of an expression, which is decorated with one of the provided decorator names.',
        nargs='*',
        action='append',
        default=[],
        type=str,
    )

    parser.add_argument(
        '--ignore-names-in-files',
        help='Ignores unused names in files, which filenames match provided path expressions.',
        nargs='*',
        action='append',
        default=[],
        type=str,
    )

    parser.add_argument(
        '--no-color',
        help='Turn off colors in the output',
        action='store_true',
        default=False,
    )

    parser.add_argument(
        '--quiet',
        help='Does not output anything. Makefile still fails with exit code 1 if unused names are found.',
        action='store_true',
        default=False,
    )

    parser.add_argument(
        '--count',
        help='Provides the count of the detected unused names instead of printing them all out.',
        action='store_true',
        default=False,
    )
    parser.add_argument(
        '-v',
        '--verbose',
        help='Shows logs useful for debuging',
        action='store_true',
        default=False,
    )

    parsed_args = parser.parse_args(args).__dict__

    for arg_name, arg_value in parsed_args.items():
        if isinstance(arg_value, list) and arg_name != 'paths':
            parsed_args[arg_name] = flatten_lists_of_comma_separated_values(parsed_args.get(arg_name))

    # Extend the Args with the values provided in the pyproject.toml
    for key, item in parse_pyproject_toml().items():
        if key in parsed_args:
            parsed_args[key].extend(item)

    # Show changes for only provided files instead of all
    if len(parsed_args['dry']) > 1 or '--dry' not in args:
        parsed_args['dry'].remove('__all_files__')

    # Do not fix if dry option is provided:
    if parsed_args['dry']:
        parsed_args['fix'] = False

    return Args(**parsed_args)


def parse_pyproject_toml() -> Dict[str, Any]:
    """Parse a pyproject toml file, pulling out relevant parts for Black.

    If parsing fails, will raise a tomllib.TOMLDecodeError.
    Copied from: https://github.com/psf/black/blob/01b8d3d4095ebdb91d0d39012a517931625c63cb/src/black/files.py#LL113C15-L113C15
    """
    pyproject_toml_filename = 'pyproject.toml'
    if not os.path.isfile(pyproject_toml_filename):
        return {}

    with open(pyproject_toml_filename, 'rb') as f:
        pyproject_toml = tomllib.load(f)

    config: Dict[str, Any] = pyproject_toml.get('tool', {}).get('deadcode', {})
    config = {k.replace('--', '').replace('-', '_'): v for k, v in config.items()}
    return config
