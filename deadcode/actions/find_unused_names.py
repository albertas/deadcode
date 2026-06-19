from collections.abc import Iterable

from deadcode.data_types import Args, Filename
from deadcode.visitor.code_item import CodeItem
from deadcode.visitor.find_unused_code_visitor import FindUnusedCodeVisitor
from deadcode.visitor.fix_unused_code_visitor import FixUnusedCodeVisitor


def find_unused_names(
    filenames: list[Filename],
    args: Args,
) -> tuple[Iterable[CodeItem], list[tuple[int, int, int, int]]]:

    find_unused_code_visitor = FindUnusedCodeVisitor(filenames, args)
    find_unused_code_visitor.visit_abstract_syntax_trees()
    unused_code_items = find_unused_code_visitor.get_unused_code_items()

    # TODO: Additional code part to remove could be assosiated to unused_code_items,
    # Or separate code item could be created without a name.

    fix_unused_code_visitor = FixUnusedCodeVisitor(find_unused_code_visitor=find_unused_code_visitor)
    additional_code_parts_to_remove = fix_unused_code_visitor.visit_abstract_syntax_trees()

    return unused_code_items, additional_code_parts_to_remove
