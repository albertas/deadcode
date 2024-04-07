import ast

from deadcode.data_types import Args, FileContent, AbstractSyntaxTree


def parse_abstract_syntax_tree(file_content: FileContent, args: Args, filename: str) -> AbstractSyntaxTree:
    """Did my code coverage just increased? Answer is no: a doc string was ignored :tada:"""
    try:
        return ast.parse(file_content, filename=filename, type_comments=True)
    except:  # noqa: E722
        if not args.count and not args.quiet:
            print(f'Error: Failed to parse {filename} file, ignoring it.')
        return ast.Module()
