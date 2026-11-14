import ast
from unittest.mock import MagicMock

import deadcode.visitor.dead_code_visitor
from deadcode.cli import main
from deadcode.utils.fix_indent import fix_indent


def _spy_on_module_parses(monkeypatch) -> list[bytes]:
    """Record the source of every module-level parse (ast.parse with type_comments=True)."""
    parsed_sources: list[bytes] = []
    original_parse = ast.parse

    def counting_parse(source: object, *args: object, **kwargs: object):
        if kwargs.get('type_comments'):
            parsed_sources.append(source)
        return original_parse(source, *args, **kwargs)

    monkeypatch.setattr('deadcode.visitor.dead_code_visitor.ast.parse', counting_parse)
    return parsed_sources


def _spy_on_file_reads() -> list[str]:
    """Record the file names opened by the visitor (the VirtualFileSystem open mock)."""
    visitor_open = deadcode.visitor.dead_code_visitor.open
    assert isinstance(visitor_open, MagicMock)
    return [call.args[0] for call in visitor_open.call_args_list]


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

    # When
    result = main(['foo.py', 'bar.py', 'empty.py', '--no-color'])

    # Then: module-export collection and the visit pass share one parse per file.
    expected_sources = [fix_indent(virtual_file_system.files[name]) for name in ('foo.py', 'bar.py', 'empty.py')]
    assert parsed_sources == expected_sources

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
