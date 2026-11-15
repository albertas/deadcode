import ast

from types import ModuleType
from typing import cast

from deadcode._native_loader import load_native
from deadcode.data_types import AbstractSyntaxTree, Args, FileContent
from deadcode.utils.print_safely import print_safely


def _parse_with_python(file_content: FileContent, filename: str) -> AbstractSyntaxTree:
    return ast.parse(file_content, filename=filename, type_comments=True)


def _failed_parse_result(args: Args, filename: str) -> AbstractSyntaxTree:
    if not args.count and not args.quiet:
        print_safely(f'Error: Failed to parse {filename} file, ignoring it.')
    return ast.Module(body=[], type_ignores=[])


def _parse_with_native(
    native: ModuleType | None, file_content: FileContent, args: Args, filename: str
) -> AbstractSyntaxTree | None:
    """Parse with the native module; None means "fall back to `ast.parse`".

    A native parse rejection (the native module's `ParseError`) is mapped into
    today's failure contract, while any other native failure — a stub that is
    not implemented, an import problem, a native crash — silently falls back to
    the Python parser.
    """
    if native is None:
        return None
    try:
        return cast('AbstractSyntaxTree', native.parse_module(file_content, filename, True))
    except native.ParseError:
        return _failed_parse_result(args, filename)
    except:  # noqa: E722
        return None


def parse_abstract_syntax_tree(file_content: FileContent, args: Args, filename: str) -> AbstractSyntaxTree:
    """Did my code coverage just increased? Answer is no: a doc string was ignored :tada:"""
    try:
        native = load_native()
        tree = _parse_with_native(native, file_content, args, filename)
        if tree is None:
            tree = _parse_with_python(file_content, filename)
        return tree
    except:  # noqa: E722
        return _failed_parse_result(args, filename)


# The string parse modes route to their native entry point. `exec` is the
# default `ast.parse` mode the commented-out-code candidate check uses.
_NATIVE_ENTRY_POINTS = {
    'eval': 'parse_expression',
    'exec': 'parse_statement',
    'func_type': 'parse_func_type',
}


def _native_parse(mode: str, source: str, filename: str) -> ast.AST:
    """Parse a string in the given mode, native first, `ast.parse` as fallback.

    The same contract as the module seam: the native module is skipped when
    absent or when it gives up on the source, and a native parse rejection
    surfaces as `SyntaxError` — the Python path's own failure kind — so the
    call sites' `except SyntaxError` handling keeps working in both modes.
    """
    native = load_native()
    if native is None:
        return ast.parse(source, filename=filename, mode=mode)
    try:
        entry_point = getattr(native, _NATIVE_ENTRY_POINTS[mode])
        return cast('ast.AST', entry_point(source, filename))
    except native.ParseError as error:
        message = f'Failed to parse {filename} in {mode} mode: {error}'
        raise SyntaxError(message) from None
    except:  # noqa: E722
        return ast.parse(source, filename=filename, mode=mode)
