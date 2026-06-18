import ast

from dataclasses import dataclass
from typing import Iterable, NamedTuple


AbstractSyntaxTree = ast.Module  # Should be module instead of ast
FileContent = str
Filename = str  # Contains full path to existing file
Pathname = str  # Can contain wildewards


@dataclass
class Args:
    fix: bool = False
    verbose: bool = False
    dry: Iterable[Pathname] = ()
    paths: Iterable[Pathname] = ()
    exclude: Iterable[Pathname] = ()
    ignore_definitions: Iterable[Pathname] = ()
    ignore_definitions_if_decorated_with: Iterable[Pathname] = ()
    ignore_definitions_if_inherits_from: Iterable[Pathname] = ()
    ignore_bodies_of: Iterable[Pathname] = ()
    ignore_bodies_if_decorated_with: Iterable[Pathname] = ()
    ignore_bodies_if_inherits_from: Iterable[Pathname] = ()
    ignore_if_decorated_with: Iterable[Pathname] = ()
    ignore_if_inherits_from: Iterable[Pathname] = ()
    ignore_names: Iterable[Pathname] = ()
    ignore_names_if_decorated_with: Iterable[Pathname] = ()
    ignore_names_if_inherits_from: Iterable[Pathname] = ()
    ignore_names_in_files: Iterable[Pathname] = ()
    no_color: bool = False
    quiet: bool = False
    count: bool = False


class Part(NamedTuple):
    """Code file part"""
    # Code fragment to remove.
    line_start: int
    line_end: int
    col_start: int
    col_end: int

    # Optionally code to insert in place of removed fragment.
    insert_code: str | None = None

    # Inserts `insert_code` if character at [line, col] is not removed.
    insert_code_if_character_is_not_removed: tuple[int, int] | None = None
