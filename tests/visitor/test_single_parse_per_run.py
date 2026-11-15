import ast
import os

from unittest.mock import MagicMock

import deadcode.visitor.dead_code_visitor
from deadcode.actions.get_unused_import_parts import get_unused_import_parts
from deadcode.cli import main
from deadcode.data_types import AbstractSyntaxTree, Args, FileContent, Part
from deadcode.utils.fix_indent import fix_indent
from deadcode.visitor import dead_code_visitor
from deadcode.visitor.code_item import CodeItem
from deadcode.visitor.dead_code_visitor import DeadCodeVisitor
from deadcode.visitor.module_exports import collect_module_exports

FILES = {
    'exports.py': b"__all__ = ['exported']\n\nexported = 1\nhidden = 2\n",
    'uses.py': b'from exports import *\nfrom os import chdir, getcwd\n\nprint(exported)\nprint(chdir)\n',
    'dynamic.py': b"__all__ = ['a']\n__all__ += extra\n",
    'only_comments.py': b'# just a comment\n',
    'empty.py': b'\n    ',
    'broken.py': b'def broken(:\n',
}


def _spy_on_module_parses(monkeypatch) -> list[bytes]:
    """Record the source of every parse routed through the native-first seam."""
    parsed_sources: list[bytes] = []
    real_parse = dead_code_visitor.parse_abstract_syntax_tree

    def counting_parse(file_content: FileContent, args: Args, filename: str) -> AbstractSyntaxTree:
        parsed_sources.append(file_content)
        return real_parse(file_content, args=args, filename=filename)

    monkeypatch.setattr('deadcode.visitor.dead_code_visitor.parse_abstract_syntax_tree', counting_parse)
    return parsed_sources


def _spy_on_comment_scans(monkeypatch) -> list[bytes]:
    """Record the source of every comment/noqa scan call."""
    scanned_sources: list[bytes] = []
    real_scan = dead_code_visitor.noqa.scan_comments_and_noqa

    def counting_scan(code: bytes):
        scanned_sources.append(code)
        return real_scan(code)

    monkeypatch.setattr('deadcode.visitor.dead_code_visitor.noqa.scan_comments_and_noqa', counting_scan)
    return scanned_sources


def _spy_on_file_reads() -> list[str]:
    """Record the file names opened by the visitor (the VirtualFileSystem open mock)."""
    visitor_open = deadcode.visitor.dead_code_visitor.open
    assert isinstance(visitor_open, MagicMock)
    return [call.args[0] for call in visitor_open.call_args_list]


def make_import_item(name: str, name_line: int, name_column: int, code_parts: list[Part]) -> CodeItem:
    return CodeItem(
        name=name,
        type_='import',
        filename='uses.py',
        code_parts=code_parts,
        name_line=name_line,
        name_column=name_column,
    )


def test_each_file_is_read_and_parsed_exactly_once_per_run(virtual_file_system, monkeypatch):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
            __all__ = ['exported']
            exported = 1
            hidden = 2
        """,
        'bar.py': b"""
            from foo import *
            print(exported)
        """,
        'empty.py': b'\n                ',
    }
    parsed_sources = _spy_on_module_parses(monkeypatch)
    scanned_sources = _spy_on_comment_scans(monkeypatch)

    # When
    result = main(['foo.py', 'bar.py', 'empty.py', '--no-color'])

    # Then: module-export collection and the visit pass share one parse per file.
    expected_sources = [fix_indent(virtual_file_system.files[name]) for name in ('foo.py', 'bar.py', 'empty.py')]
    assert parsed_sources == expected_sources
    # The comment/noqa scanner runs once per non-empty file only.
    assert scanned_sources == expected_sources[:2]

    read_filenames = _spy_on_file_reads()
    assert read_filenames.count('foo.py') == 1
    assert read_filenames.count('bar.py') == 1
    assert read_filenames.count('empty.py') == 1

    # Empty file handling is unchanged.
    assert result == 'empty.py DC11 Empty file\nfoo.py:3:0: DC01 Variable `hidden` is never used'


def test_module_export_collection_result_is_unchanged(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
            __all__ = ['foo', 'bar']

            foo = 1
            bar = 2
            spam = 3
        """,
        'bar.py': b"""
            from foo import *

            print(foo)
            print(bar)
        """,
    }

    # When
    unused_names = main(['foo.py', 'bar.py', '--no-color'])

    # Then: names exported via `__all__` are still honoured.
    assert unused_names == 'foo.py:5:0: DC01 Variable `spam` is never used'


def test_dynamic_module_export_result_is_unchanged(virtual_file_system):
    # Having: `__all__ += ['bar']` keeps exports unknown, so all public names count as exported.
    virtual_file_system.files = {
        'foo.py': b"""
            __all__ = ['foo']
            __all__ += ['bar']

            foo = 1
            bar = 2
            spam = 3
        """,
        'bar.py': b"""
            from foo import *

            print(foo)
            print(bar)
            print(spam)
        """,
    }

    # When
    unused_names = main(['foo.py', 'bar.py', '--no-color'])

    # Then: exports stay unknown, so every public name of foo.py counts as exported.
    assert unused_names is None


def test_file_that_fails_to_parse_is_skipped_by_export_collection(virtual_file_system, capsys):
    # Having: broken.py cannot be parsed, so its exports stay unknown and it
    # contributes nothing to usage detection.
    virtual_file_system.files = {
        'broken.py': b'def broken(:\n',
        'foo.py': b"""
            __all__ = ['exported']
            exported = 1
            hidden = 2
        """,
        'bar.py': b"""
            from foo import *
            print(exported)
        """,
    }

    # When
    result = main(['broken.py', 'foo.py', 'bar.py', '--no-color'])

    # Then: the parse-error message path is kept and the run still completes.
    captured = capsys.readouterr()
    assert 'Error: Failed to parse broken.py file, ignoring it.' in captured.out
    assert result == 'foo.py:3:0: DC01 Variable `hidden` is never used'


def test_export_collection_runs_before_the_visit_pass(virtual_file_system):
    # Having: bar.py is analysed before foo.py in file order, but usage detection
    # of bar.py's wildcard import must still see foo.py's exports.
    virtual_file_system.files = {
        'bar.py': b"""
            from foo import *

            print(exported)
        """,
        'foo.py': b"""
            __all__ = ['exported']
            exported = 1
            hidden = 2
        """,
    }

    # When
    unused_names = main(['bar.py', 'foo.py', '--no-color'])

    # Then: `exported` is a known export of foo.py, so the wildcard usage is live.
    assert unused_names == 'foo.py:3:0: DC01 Variable `hidden` is never used'


def test_each_file_is_parsed_exactly_once_per_run(virtual_file_system, monkeypatch):
    # Having
    virtual_file_system.files = FILES

    parsed_filenames: list[str] = []
    real_parse = dead_code_visitor.parse_abstract_syntax_tree

    def counting_parse(file_content: FileContent, args: Args, filename: str) -> AbstractSyntaxTree:
        parsed_filenames.append(str(filename))
        return real_parse(file_content, args=args, filename=filename)

    monkeypatch.setattr(dead_code_visitor, 'parse_abstract_syntax_tree', counting_parse)

    # When
    visitor = DeadCodeVisitor(list(FILES), Args())
    visitor.visit_abstract_syntax_trees()

    # Then: one parse call per file, in the given file order.
    assert parsed_filenames == list(FILES)
    assert visitor.get_unused_code_items() is not None


def test_module_exports_match_a_fresh_parse_of_each_file(virtual_file_system):
    # Having
    virtual_file_system.files = FILES

    # When
    visitor = DeadCodeVisitor(list(FILES), Args())
    visitor.visit_abstract_syntax_trees()

    # Then: the cached exports equal the ones a fresh plain parse produces.
    expected_exports = {}
    for filename, content in FILES.items():
        try:
            tree = ast.parse(content, filename=filename)
        except SyntaxError:
            continue
        exports = collect_module_exports(tree)
        if exports is not None:
            expected_exports[os.path.splitext(filename)[0]] = exports

    assert visitor.module_exports == expected_exports


def test_findings_are_produced_from_the_cached_trees(virtual_file_system):
    # Having
    virtual_file_system.files = FILES

    # When
    visitor = DeadCodeVisitor(list(FILES), Args())
    visitor.visit_abstract_syntax_trees()

    # Then: export resolution, import analysis and the empty-file report keep
    # their previous results for the same fixtures.
    findings = {(str(item.filename), item.type_, item.name) for item in visitor.get_unused_code_items()}
    assert ('exports.py', 'variable', 'hidden') in findings
    assert ('uses.py', 'import', 'getcwd') in findings
    assert ('empty.py', 'unused_file', 'empty.py') in findings
    # `a` in dynamic.py is listed in `__all__`, so it counts as exported.
    assert not [item for item in findings if item[0] == 'dynamic.py']
    assert not [item for item in findings if item[0] == 'broken.py']


def test_cached_tree_is_reused_without_parsing_content_again(monkeypatch):
    # Having
    content = b'import foo, bar\n\nprint(foo)\n'
    item = make_import_item('bar', 1, 11, [Part(1, 1, 11, 14)])

    parse_calls: list[tuple] = []
    real_parse = ast.parse

    def counting_parse(*args: object, **kwargs: object) -> ast.Module:
        parse_calls.append(args)
        return real_parse(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr('deadcode.actions.get_unused_import_parts.ast.parse', counting_parse)

    tree = ast.parse(content)
    parse_calls.clear()

    # When
    parts_from_cached_tree = get_unused_import_parts(content, [item], cached_tree=tree)

    # Then: the cached tree is used and the result matches a fresh parse.
    assert parse_calls == []
    assert parts_from_cached_tree == get_unused_import_parts(content, [item])


def test_import_parts_analysis_matches_a_fresh_parse(virtual_file_system, monkeypatch):
    # Having
    virtual_file_system.files = FILES

    parsed_trees: dict[str, AbstractSyntaxTree] = {}
    real_parse = dead_code_visitor.parse_abstract_syntax_tree

    def tree_recording_parse(file_content: FileContent, args: Args, filename: str) -> AbstractSyntaxTree:
        node = real_parse(file_content, args=args, filename=filename)
        parsed_trees[str(filename)] = node
        return node

    monkeypatch.setattr(dead_code_visitor, 'parse_abstract_syntax_tree', tree_recording_parse)

    visitor = DeadCodeVisitor(list(FILES), Args())
    visitor.visit_abstract_syntax_trees()

    unused_import_items = [
        item for item in visitor.get_unused_code_items() if item.type_ == 'import' and str(item.filename) == 'uses.py'
    ]
    assert unused_import_items

    content = FILES['uses.py']
    cached_tree = parsed_trees['uses.py']

    # When
    parts_from_cached_tree = get_unused_import_parts(content, unused_import_items, cached_tree=cached_tree)
    parts_from_fresh_parse = get_unused_import_parts(content, unused_import_items)

    # Then
    assert parts_from_cached_tree == parts_from_fresh_parse
