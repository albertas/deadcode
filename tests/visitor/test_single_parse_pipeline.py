import asyncio
import ast

from deadcode.actions import parse_abstract_syntax_tree as parse_module
from deadcode.data_types import Args
from deadcode.visitor import dead_code_visitor as visitor_module
from deadcode.visitor.dead_code_visitor import DeadCodeVisitor


def visit(virtual_file_system, args: Args | None = None) -> DeadCodeVisitor:
    visitor = DeadCodeVisitor(list(virtual_file_system.files), args or Args())
    asyncio.run(visitor.visit_abstract_syntax_trees())
    return visitor


def test_static_all_contributes_exactly_those_exports(virtual_file_system):
    virtual_file_system.files = {'foo.py': b"__all__ = ['x', 'Y']\nx = 1\nY = 2\nz = 3\n"}

    visitor = visit(virtual_file_system)

    assert visitor.module_exports['foo'] == {'x', 'Y'}


def test_a_file_without_all_contributes_its_public_module_names(virtual_file_system):
    virtual_file_system.files = {'foo.py': b'def public():\n    pass\n_private = 1\n'}

    visitor = visit(virtual_file_system)

    assert visitor.module_exports['foo'] == {'public'}


def test_whitespace_only_file_contributes_an_empty_export_set(monkeypatch):
    monkeypatch.setattr(
        visitor_module,
        '_read_and_parse_chunk',
        lambda filenames: [(filename, b'\n   \n', ast.parse(b'\n   \n')) for filename in filenames],
    )
    visitor = DeadCodeVisitor(['empty.py'], Args())

    asyncio.run(visitor.visit_abstract_syntax_trees())

    assert visitor.module_exports['empty'] == set()
    assert [item.name for item in visitor.unused_file] == ['empty.py']


def test_syntax_error_file_contributes_no_exports_and_reports_once(virtual_file_system, capsys):
    virtual_file_system.files = {'broken.py': b'def broken(:\n'}

    visitor = visit(virtual_file_system)

    assert 'broken' not in visitor.module_exports
    output = capsys.readouterr().out
    assert output.count('Error: Failed to parse broken.py file, ignoring it.') == 1


def test_plain_parse_fallback_contributes_exports_when_main_parse_fails(virtual_file_system, monkeypatch, capsys):
    virtual_file_system.files = {'fallback.py': b'def public():\n    pass\n'}
    original_parse = ast.parse

    def rejecting_type_comments(source: str | bytes, *args: object, **kwargs: object) -> ast.Module:
        if kwargs.get('type_comments'):
            message = 'type comments rejected'
            raise SyntaxError(message)
        return original_parse(source, *args, **kwargs)

    monkeypatch.setattr(parse_module.ast, 'parse', rejecting_type_comments)

    visitor = visit(virtual_file_system)

    assert visitor.module_exports['fallback'] == {'public'}
    assert capsys.readouterr().out.count('Error: Failed to parse fallback.py file, ignoring it.') == 1


def test_normal_path_parses_each_file_once_with_type_comments(virtual_file_system, monkeypatch):
    virtual_file_system.files = {'a.py': b'a = 1\n', 'b.py': b'b = 2\n'}
    original_parse = ast.parse
    calls: list[bool] = []

    def counting_parse(source: str | bytes, *args: object, **kwargs: object) -> ast.Module:
        calls.append(bool(kwargs.get('type_comments')))
        return original_parse(source, *args, **kwargs)

    monkeypatch.setattr(parse_module.ast, 'parse', counting_parse)

    visit(virtual_file_system)

    assert calls == [True, True]
