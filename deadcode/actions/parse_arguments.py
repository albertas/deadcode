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
    parser.add_argument("paths", help="Paths where to search for python files", nargs="+")
    parser.add_argument(
        "--exclude",
        help="PATHS to files not to analyse at all (comma separated values)",
        nargs="*",
        action="append",
        default=[],
        type=str,
    )
    parser.add_argument(
        "--ignore-names",
        help="NAMES not to report (comma separated values)",
        nargs="*",
        action="append",
        default=[],
        type=str,
    )
    parser.add_argument(
        "--ignore-names-in-files",
        help="PATHS to files not to report NAMES from (comma separated values)",
        nargs="*",
        action="append",
        default=[],
        type=str,
    )
    parser.add_argument(
        "--no-color",
        help="Turn off colors in the output",
        action="store_true",
        default=False,
    )

    parsed_args = parser.parse_args(args).__dict__

    for field_name in ["exclude", "ignore_names", "ignore_names_in_files"]:
        parsed_args[field_name] = flatten_lists_of_comma_separated_values(parsed_args.get(field_name))

    # Extend the Args with the values provided in the pyproject.toml
    for key, item in parse_pyproject_toml().items():
        if key in parsed_args:
            parsed_args[key].extend(item)

    return Args(**parsed_args)


def parse_pyproject_toml() -> Dict[str, Any]:
    """Parse a pyproject toml file, pulling out relevant parts for Black.

    If parsing fails, will raise a tomllib.TOMLDecodeError.
    Copied from: https://github.com/psf/black/blob/01b8d3d4095ebdb91d0d39012a517931625c63cb/src/black/files.py#LL113C15-L113C15
    """
    pyproject_toml_filename = "pyproject.toml"
    if not os.path.isfile(pyproject_toml_filename):
        return {}

    with open(pyproject_toml_filename, "rb") as f:
        pyproject_toml = tomllib.load(f)
    config: Dict[str, Any] = pyproject_toml.get("tool", {}).get("deadcode", {})
    config = {k.replace("--", "").replace("-", "_"): v for k, v in config.items()}
    return config
