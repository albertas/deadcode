import ast

from dataclasses import dataclass
from typing import Iterable, NamedTuple


AbstractSyntaxTree = ast.Module  # Should be module instead of ast
FileContent = bytes
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

    line_start: int
    line_end: int
    col_start: int
    col_end: int
