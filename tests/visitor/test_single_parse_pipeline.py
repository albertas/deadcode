import ast
from typing import Any

from deadcode.actions import parse_abstract_syntax_tree as parse_module
from deadcode.actions.parse_abstract_syntax_tree import parse_abstract_syntax_tree
from deadcode.data_types import Args
from deadcode.visitor.dead_code_visitor import DeadCodeVisitor


def visit(virtual_file_system, args: Args | None = None) -> DeadCodeVisitor:
    filenames = list(virtual_file_system.files)
    visitor = DeadCodeVisitor(filenames, args or Args())
    visitor.visit_abstract_syntax_trees()
    return visitor


def test_all_contributes_exports_through_the_main_parse(virtual_file_system):
    virtual_file_system.files = {'foo.py': b"__all__ = ['x']\nx = 1\n"}

    visitor = visit(virtual_file_system)

    assert visitor.module_exports == {'foo': {'x'}}


def test_file_without_all_contributes_public_names(virtual_file_system):
    virtual_file_system.files = {'foo.py': b'def x():\n    ...\n\n\n_y = 1\n'}

    visitor = visit(virtual_file_system)

    assert visitor.module_exports == {'foo': {'x'}}


def test_empty_file_contributes_an_empty_export_set(virtual_file_system, monkeypatch):
    virtual_file_system.files = {'empty.py': b''}
    monkeypatch.setattr('deadcode.actions.read_python_files._read_chunk', lambda filenames: [b'' for _ in filenames])

    visitor = visit(virtual_file_system)

    assert visitor.module_exports == {'empty': set()}
    unused_items = list(visitor.get_unused_code_items())
    assert [(item.name, item.message) for item in unused_items] == [('empty.py', 'Empty file')]


def test_syntax_error_file_prints_the_existing_message_and_records_no_exports(virtual_file_system, capsys):
    virtual_file_system.files = {'broken.py': b'def broken(:\n'}

    visitor = visit(virtual_file_system)

    assert 'broken' not in visitor.module_exports
    assert capsys.readouterr().out == 'Error: Failed to parse broken.py file, ignoring it.\n'


def test_type_comment_failure_falls_back_to_a_plain_parse_for_exports(virtual_file_system, capsys):
    virtual_file_system.files = {'typed.py': b'x: int  # type: int\n'}

    visitor = visit(virtual_file_system)

    assert visitor.module_exports == {'typed': {'x'}}
    assert capsys.readouterr().out == 'Error: Failed to parse typed.py file, ignoring it.\n'


def test_normal_path_parses_each_file_once_with_type_comments(virtual_file_system, monkeypatch):
    virtual_file_system.files = {'foo.py': b'x = 1\n'}
    original_parse = parse_module.ast.parse
    calls: list[dict[str, Any]] = []

    def counting_parse(*args: Any, **kwargs: Any) -> ast.Module:
        calls.append(kwargs)
        return original_parse(*args, **kwargs)

    monkeypatch.setattr(parse_module.ast, 'parse', counting_parse)

    visitor = visit(virtual_file_system)

    assert visitor.module_exports == {'foo': {'x'}}
    type_comment_calls = [kwargs for kwargs in calls if kwargs.get('type_comments')]
    assert len(type_comment_calls) == 1
    assert type_comment_calls[0]['filename'] == 'foo.py'


def test_parse_abstract_syntax_tree_returns_the_tree_for_valid_content():
    tree = parse_abstract_syntax_tree(b'x = 1\n', Args(), 'foo.py')

    assert isinstance(tree, ast.Module)
    assert [statement.targets[0].id for statement in tree.body] == ['x']


def test_parse_abstract_syntax_tree_returns_an_empty_module_and_prints_on_failure(capsys):
    tree = parse_abstract_syntax_tree(b'def broken(:\n', Args(), 'foo.py')

    assert isinstance(tree, ast.Module)
    assert tree.body == []
    assert capsys.readouterr().out == 'Error: Failed to parse foo.py file, ignoring it.\n'


def test_parse_abstract_syntax_tree_suppresses_the_message_when_counting(capsys):
    tree = parse_abstract_syntax_tree(b'def broken(:\n', Args(count=True), 'foo.py')

    assert tree.body == []
    assert capsys.readouterr().out == ''
