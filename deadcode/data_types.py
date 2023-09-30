import ast

from dataclasses import dataclass
from typing import List, NamedTuple


AbstractSyntaxTree = ast.Module  # Should be module instead of ast
FileContent = str
Filename = str  # Contains full path to existing file
Pathname = str  # Can contain wildewards


@dataclass
class Args:
    fix: bool
    verbose: bool
    paths: List[Pathname]
    exclude: List[Pathname]
    ignore_definitions: List[Pathname]
    ignore_definitions_if_decorated_with: List[Pathname]
    ignore_definitions_if_inherits_from: List[Pathname]
    ignore_names: List[Pathname]
    ignore_names_if_decorated_with: List[Pathname]
    ignore_names_if_inherits_from: List[Pathname]
    ignore_names_in_files: List[Pathname]
    no_color: bool
    quiet: bool
    count: bool


class Part(NamedTuple):
    """Code file part"""

    line_start: int
    line_end: int
    col_start: int
    col_end: int
