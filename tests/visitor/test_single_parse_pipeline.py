import asyncio
import ast
import inspect
from typing import Any

import pytest

from deadcode.visitor import dead_code_visitor as visitor_module
from deadcode.actions import parse_abstract_syntax_tree as parse_module
from deadcode.actions.parse_abstract_syntax_tree import parse_abstract_syntax_tree
from deadcode.data_types import Args
from deadcode.visitor.dead_code_visitor import DeadCodeVisitor


def visit(virtual_file_system, args: Args | None = None) -> DeadCodeVisitor:
    filenames = list(virtual_file_system.files)
    visitor = DeadCodeVisitor(filenames, args or Args())
    asyncio.run(visitor.visit_abstract_syntax_trees())
    return visitor


def test_visit_abstract_syntax_trees_is_a_coroutine_function():
    assert inspect.iscoroutinefunction(DeadCodeVisitor.visit_abstract_syntax_trees)


def test_visit_reads_and_parses_new_chunks_only_after_visiting_the_previous_wave(virtual_file_system, monkeypatch):
    filenames = [f'{index}.py' for index in range(10)]
    virtual_file_system.files = {filename: f'x = {index}\n'.encode() for index, filename in enumerate(filenames)}
    reader = visitor_module._read_and_parse_chunk  # noqa: SLF001
    read_calls: list[list[str]] = []
    visited: list[str] = []

    def recording_reader(chunk: list[str]) -> list[tuple[str, bytes, ast.Module | None]]:
        read_calls.append(list(chunk))
        return reader(chunk)

    def failing_visit(self: DeadCodeVisitor, file_path: str, _file_content: bytes, _node: ast.Module | None) -> None:
        visited.append(file_path)
        message = 'stop after the first file'
        raise RuntimeError(message)

    monkeypatch.setattr(visitor_module, '_read_and_parse_chunk', recording_reader)
    monkeypatch.setattr(visitor_module, 'chunk_filenames', lambda names: [[name] for name in names])
    monkeypatch.setattr(visitor_module, 'DEFAULT_WORKERS', 2)
    monkeypatch.setattr(DeadCodeVisitor, '_visit_file', failing_visit)

    with pytest.raises(RuntimeError, match='stop after the first file'):
        visit(virtual_file_system)

    # Only the first wave of two chunks is read before the visitor starts; the
    # remaining eight chunks are never loaded into memory.
    assert read_calls == [['0.py'], ['1.py']]
    assert visited == ['0.py']


def test_at_most_workers_chunks_are_processed_concurrently(virtual_file_system, monkeypatch):
    filenames = [f'{index}.py' for index in range(7)]
    virtual_file_system.files = {filename: f'x = {index}\n'.encode() for index, filename in enumerate(filenames)}
    original_to_thread = asyncio.to_thread
    active_tasks = 0
    max_active_tasks = 0

    async def counting_to_thread(function: Any, *args: Any, **kwargs: Any) -> Any:
        nonlocal active_tasks, max_active_tasks
        active_tasks += 1
        max_active_tasks = max(max_active_tasks, active_tasks)
        try:
            return await original_to_thread(function, *args, **kwargs)
        finally:
            active_tasks -= 1

    monkeypatch.setattr(asyncio, 'to_thread', counting_to_thread)
    monkeypatch.setattr(visitor_module, 'chunk_filenames', lambda names: [[name] for name in names])
    monkeypatch.setattr(visitor_module, 'DEFAULT_WORKERS', 3)

    visitor = visit(virtual_file_system)

    assert len(visitor.module_exports) == 7
    assert max_active_tasks == 3


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
    monkeypatch.setattr(
        'deadcode.visitor.dead_code_visitor.read_file_chunk', lambda filenames: [b'' for _ in filenames]
    )

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
