import ast

from deadcode.data_types import Args, FileContent, AbstractSyntaxTree
from deadcode.utils.print_safely import print_safely


def parse_abstract_syntax_tree_or_none(file_content: FileContent, filename: str) -> AbstractSyntaxTree | None:
    """Parse `file_content` and return the tree, or None when parsing fails."""
    try:
        return ast.parse(file_content, filename=filename, type_comments=True)
    except:  # noqa: E722
        return None


def report_parse_failure(args: Args, filename: str) -> None:
    """Print the parse failure message unless the run is quiet or count-only."""
    if not args.count and not args.quiet:
        print_safely(f'Error: Failed to parse {filename} file, ignoring it.')


def parse_abstract_syntax_tree(  # noqa: DC02
    file_content: FileContent, args: Args, filename: str
) -> AbstractSyntaxTree:
    """Did my code coverage just increased? Answer is no: a doc string was ignored :tada:"""
    tree = parse_abstract_syntax_tree_or_none(file_content, filename)
    if tree is not None:
        return tree
    report_parse_failure(args, filename)
    return ast.Module(body=[], type_ignores=[])
