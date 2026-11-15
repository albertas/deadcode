import asyncio
import ast
import inspect
import threading

import pytest

from deadcode.data_types import Args
from deadcode.visitor import dead_code_visitor as visitor_module
from deadcode.visitor.dead_code_visitor import DeadCodeVisitor


def visit(virtual_file_system, args: Args | None = None) -> DeadCodeVisitor:
    visitor = DeadCodeVisitor(list(virtual_file_system.files), args or Args())
    asyncio.run(visitor.visit_abstract_syntax_trees())
    return visitor


def test_visit_abstract_syntax_trees_is_a_coroutine_function():
    assert inspect.iscoroutinefunction(DeadCodeVisitor.visit_abstract_syntax_trees)


def test_visit_reads_only_the_first_wave_before_visiting(virtual_file_system, monkeypatch):
    filenames = [f'{index}.py' for index in range(10)]
    virtual_file_system.files = {filename: f'x = {index}\n'.encode() for index, filename in enumerate(filenames)}
    original_reader = visitor_module._read_and_parse_chunk  # noqa: SLF001
    read_calls: list[list[str]] = []
    visited: list[str] = []

    def recording_reader(chunk: list[str]) -> list[tuple[str, bytes, ast.Module | None]]:
        read_calls.append(list(chunk))
        return original_reader(chunk)

    def failing_visit(self: DeadCodeVisitor, file_path: str, _content: bytes, _tree: ast.Module | None) -> None:
        visited.append(file_path)
        message = 'stop after the first file'
        raise RuntimeError(message)

    monkeypatch.setattr(visitor_module, '_read_and_parse_chunk', recording_reader)
    monkeypatch.setattr(visitor_module, 'chunk_filenames', lambda names: [[name] for name in names])
    monkeypatch.setattr(visitor_module, 'DEFAULT_WORKERS', 2)
    monkeypatch.setattr(DeadCodeVisitor, '_visit_file', failing_visit)

    with pytest.raises(RuntimeError, match='stop after the first file'):
        visit(virtual_file_system)

    assert read_calls == [['0.py'], ['1.py']]
    assert visited == ['0.py']


def test_wave_chunks_run_concurrently_and_visits_keep_input_order(virtual_file_system, monkeypatch):
    filenames = [f'{index}.py' for index in range(3)]
    virtual_file_system.files = {filename: f'x = {index}\n'.encode() for index, filename in enumerate(filenames)}
    original_reader = visitor_module._read_and_parse_chunk  # noqa: SLF001
    barrier = threading.Barrier(3)
    visited: list[str] = []

    def blocking_reader(chunk: list[str]) -> list[tuple[str, bytes, ast.Module | None]]:
        barrier.wait(timeout=10)
        return original_reader(chunk)

    original_visit = DeadCodeVisitor._visit_file  # noqa: SLF001

    def recording_visit(self: DeadCodeVisitor, file_path: str, content: bytes, tree: ast.Module | None) -> None:
        visited.append(file_path)
        original_visit(self, file_path, content, tree)

    monkeypatch.setattr(visitor_module, 'chunk_filenames', lambda names: [[name] for name in names])
    monkeypatch.setattr(visitor_module, 'DEFAULT_WORKERS', 3)
    monkeypatch.setattr(visitor_module, '_read_and_parse_chunk', blocking_reader)
    monkeypatch.setattr(DeadCodeVisitor, '_visit_file', recording_visit)

    visitor = visit(virtual_file_system)

    assert visited == filenames
    assert len(visitor.module_exports) == 3


def test_syntax_error_is_reported_once_per_file_and_visited_as_empty(virtual_file_system, monkeypatch, capsys):
    virtual_file_system.files = {'broken.py': b'def broken(:\n'}
    original_report = visitor_module.report_parse_failure
    reported: list[str] = []

    def recording_report(args: Args, filename: str) -> None:
        reported.append(filename)
        original_report(args, filename)

    monkeypatch.setattr(visitor_module, 'report_parse_failure', recording_report)

    visit(virtual_file_system)

    assert reported == ['broken.py']
    assert capsys.readouterr().out.count('Error: Failed to parse broken.py file, ignoring it.') == 1


def test_count_suppresses_the_parse_failure_message(virtual_file_system, capsys):
    virtual_file_system.files = {'broken.py': b'def broken(:\n'}

    visit(virtual_file_system, Args(count=True))

    assert 'Error: Failed to parse' not in capsys.readouterr().out


def test_whitespace_only_file_yields_an_empty_file_finding(monkeypatch):
    monkeypatch.setattr(
        visitor_module,
        '_read_and_parse_chunk',
        lambda filenames: [(filename, b'   \n\n', ast.parse(b'   \n\n')) for filename in filenames],
    )
    visitor = DeadCodeVisitor(['empty.py'], Args())

    asyncio.run(visitor.visit_abstract_syntax_trees())

    assert [item.name for item in visitor.unused_file] == ['empty.py']
    assert visitor.module_exports['empty'] == set()
