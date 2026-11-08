from typing import NamedTuple
import logging
import sys

from deadcode import __version__
from deadcode.actions.find_python_filenames import find_python_filenames
from deadcode.actions.find_unused_names import find_unused_names
from deadcode.actions.fix_or_show_unused_code import fix_or_show_unused_code
from deadcode.actions.parse_arguments import parse_arguments
from deadcode.actions.get_unused_names_error_message import (
    get_unused_names_error_message,
)
from deadcode.utils.print_safely import print_safely


class RunResult(NamedTuple):
    message: str | None
    exit_status: int


VERSION_OPTIONS = ('--version', '-V')


def run(
    command_line_args: list[str] | None = None,
) -> RunResult:
    version_requested = any(option in sys.argv for option in VERSION_OPTIONS) or (
        command_line_args is not None and any(option in command_line_args for option in VERSION_OPTIONS)
    )
    if version_requested:
        return RunResult(__version__, 0)

    args = parse_arguments(command_line_args)
    if args.verbose:
        logging.basicConfig(level=logging.INFO)

    filenames = find_python_filenames(args=args)

    # TODO: rename unused_names to unused_code_items
    unused_names = find_unused_names(filenames=filenames, args=args)

    file_diff = None
    if (args.fix or args.dry) and unused_names:
        file_diff = fix_or_show_unused_code(unused_names, args=args)

    if (error_message := get_unused_names_error_message(unused_names, args=args)) is not None:
        return RunResult(error_message + ('\n\n' + file_diff if file_diff else ''), 1)

    if not args.count and not args.quiet:
        print_safely('Well done! ✨ 🚀 ✨' if args.no_color else '\033[1mWell done!\033[0m ✨ 🚀 ✨')
    return RunResult(None, 0)


def main(  # noqa: DC02
    command_line_args: list[str] | None = None,
) -> str | None:
    return run(command_line_args).message


def print_main(command_line_args: list[str] | None = None) -> int:
    result = run(command_line_args)
    if result.message:
        print_safely(result.message)
    return result.exit_status


if __name__ == '__main__':
    sys.exit(print_main())
