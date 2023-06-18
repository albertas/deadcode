import ast
from typing import Dict

from deadcode.data_types import FileContent, Filename, AbstractSyntaxTree


def parse_abstract_syntax_trees(files: Dict[Filename, FileContent]) -> Dict[Filename, AbstractSyntaxTree]:
    """Did my code coverage just increased? Answer is no: a doc string was ignored :tada:"""
    abstract_syntax_trees_for_files = {}
    for filename, file_content in files.items():
        try:
            abstract_syntax_trees_for_files[filename] = ast.dump(ast.parse(file_content))  # Note: indent=1 for debug
        except:  # noqa: E722
            print(f"Error: Failed to parse {filename} file, ignoring it.")
            abstract_syntax_trees_for_files[filename] = ""
    return abstract_syntax_trees_for_files
