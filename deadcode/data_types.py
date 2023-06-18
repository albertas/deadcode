from dataclasses import dataclass
from typing import List


AbstractSyntaxTree = str
FileContent = str
Filename = str  # Contains full path to existing file
FilenameWithPosition = str  # filename:line:column:
Pathname = str  # Can contain wildewards
VariableName = str


@dataclass
class Args:
    paths: List[Pathname]
    exclude: List[Pathname]
    ignore_names: List[Pathname]
    ignore_names_in_files: List[Pathname]
    no_color: bool
