from typing import List, Iterable

from deadcode.data_types import Args, Filename
from deadcode.visitor.code_item import CodeItem
from deadcode.visitor.dead_code_visitor import DeadCodeVisitor


def find_unused_names(
    filenames: List[Filename],
    args: Args,
) -> Iterable[CodeItem]:
    dead_code_visitor = DeadCodeVisitor(filenames, args)
    dead_code_visitor.visit_abstract_syntax_trees()
    unused_code_items = dead_code_visitor.get_unused_code_items()
    return unused_code_items
