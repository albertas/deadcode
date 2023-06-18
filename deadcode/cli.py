from typing import List, Optional

from deadcode.actions.find_python_filenames import find_python_filenames
from deadcode.actions.find_unused_names import find_unused_names
from deadcode.actions.parse_arguments import parse_arguments
from deadcode.actions.parse_global_names import parse_global_names
from deadcode.actions.read_files import read_files

from deadcode.actions.parse_abstract_syntax_trees import parse_abstract_syntax_trees
from deadcode.actions.get_unused_names_error_message import (
    get_unused_names_error_message,
)


def main(
    command_line_args: Optional[List[str]] = None,
) -> Optional[str]:
    args = parse_arguments(command_line_args)

    python_filenames = find_python_filenames(args=args)
    files = read_files(python_filenames)

    global_names = parse_global_names(files, args=args)
    abstract_syntax_trees_of_files = parse_abstract_syntax_trees(files)
    unused_names = find_unused_names(abstract_syntax_trees_of_files, global_names, args=args)

    if error_message := get_unused_names_error_message(unused_names, args=args):
        return error_message

    print("\033[1mWell done!\033[0m ✨ 🚀 ✨")
    return None


if __name__ == "__main__":
    main()
