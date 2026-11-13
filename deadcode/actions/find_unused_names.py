from collections.abc import Iterable

from deadcode.data_types import Args, Filename
from deadcode.visitor.code_item import CodeItem
from deadcode.visitor.dead_code_visitor import DeadCodeVisitor


def find_unused_names(
    filenames: list[Filename],
    args: Args,
) -> Iterable[CodeItem]:
    dead_code_visitor = DeadCodeVisitor(filenames, args)
    dead_code_visitor.visit_abstract_syntax_trees()
    unused_code_items = dead_code_visitor.get_unused_code_items()
    ignored_codes = {code.upper() for code in args.ignore}
    if not ignored_codes:
        return unused_code_items
    return [item for item in unused_code_items if item.error_code.upper() not in ignored_codes]
