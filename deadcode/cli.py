from typing import List, Optional
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from deadcode import __version__
from deadcode.actions.find_python_filenames import find_python_filenames
from deadcode.actions.find_unused_names import find_unused_names
from deadcode.actions.fix_or_show_unused_code import fix_or_show_unused_code
from deadcode.actions.parse_arguments import parse_arguments
from deadcode.actions.get_unused_names_error_message import (
    get_unused_names_error_message,
)


def main(
    command_line_args: Optional[List[str]] = None,
) -> Optional[str]:

    if command_line_args and '--version' in command_line_args or '--version' in sys.argv:
        return __version__

    args = parse_arguments(command_line_args)

    filenames = find_python_filenames(args=args)

    # TODO: rename unused_names to unused_code_items
    unused_names = find_unused_names(filenames=filenames, args=args)

    file_diff = None
    if (args.fix or args.dry) and unused_names:
        file_diff = fix_or_show_unused_code(unused_names, args=args)

    if (error_message := get_unused_names_error_message(unused_names, args=args)) is not None:
        return error_message + ('\n\n' + file_diff if file_diff else '')

    if not args.count and not args.quiet:
        print('\033[1mWell done!\033[0m ✨ 🚀 ✨')
    return None


def print_main() -> None:
    if result := main():
        print(result)


if __name__ == '__main__':
    print_main()
