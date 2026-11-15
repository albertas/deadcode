import asyncio
import inspect
from typing import Any
from unittest.mock import MagicMock

import pytest

from deadcode.actions import read_python_files as read_python_files_module
from deadcode.actions.read_python_files import read_python_files, read_python_files_sync


def test_reads_files_in_input_order_including_duplicate_filenames(virtual_file_system):
    virtual_file_system.files = {'a.py': b'a = 1\n', 'b.py': b'b = 2\n'}

    file_contents = asyncio.run(read_python_files(['a.py', 'b.py', 'a.py']))

    assert file_contents == [b'a = 1\n', b'b = 2\n', b'a = 1\n']


def test_each_distinct_filename_is_opened_once(virtual_file_system):
    virtual_file_system.files = {'a.py': b'a = 1\n', 'b.py': b'b = 2\n', 'c.py': b'c = 3\n'}
    open_mock = read_python_files_module.open

    asyncio.run(read_python_files(['a.py', 'b.py', 'c.py']))

    # Chunks run concurrently, so the mock records the opens in scheduling order.
    opened_filenames = [call.args[0] for call in open_mock.call_args_list]
    assert sorted(opened_filenames) == ['a.py', 'b.py', 'c.py']


def test_at_most_workers_chunk_tasks_are_submitted(virtual_file_system, monkeypatch):
    filenames = [f'{index}.py' for index in range(7)]
    virtual_file_system.files = {filename: f'x = {index}\n'.encode() for index, filename in enumerate(filenames)}
    original_to_thread = asyncio.to_thread
    chunk_calls = []

    async def counting_to_thread(function: Any, *args: Any, **kwargs: Any) -> Any:
        chunk_calls.append(function)
        return await original_to_thread(function, *args, **kwargs)

    monkeypatch.setattr(asyncio, 'to_thread', counting_to_thread)

    file_contents = asyncio.run(read_python_files(filenames, workers=3))

    assert file_contents == [f'x = {index}\n'.encode() for index in range(7)]
    assert len(chunk_calls) == 3


def test_empty_input_returns_empty_list_without_creating_tasks(monkeypatch):
    to_thread_mock = MagicMock()
    monkeypatch.setattr(asyncio, 'to_thread', to_thread_mock)

    assert asyncio.run(read_python_files([])) == []
    assert to_thread_mock.call_count == 0


def test_os_error_propagates_unwrapped(virtual_file_system, monkeypatch):
    monkeypatch.setattr(
        'deadcode.actions.read_python_files.open',
        MagicMock(side_effect=OSError('boom')),
    )

    with pytest.raises(OSError, match='boom'):
        asyncio.run(read_python_files(['missing.py']))


def test_read_python_files_is_a_coroutine_function():
    assert inspect.iscoroutinefunction(read_python_files)


def test_read_python_files_sync_matches_the_async_reader(virtual_file_system, monkeypatch):
    virtual_file_system.files = {'a.py': b'a = 1\n', 'b.py': b'b = 2\n'}
    monkeypatch.setattr(read_python_files_module, 'ASYNC_READ_MIN_FILES', 0)

    expected = asyncio.run(read_python_files(['a.py', 'b.py']))

    assert read_python_files_sync(['a.py', 'b.py']) == expected


def test_read_python_files_sync_skips_the_event_loop_for_small_corpora(virtual_file_system, monkeypatch):
    virtual_file_system.files = {'a.py': b'a = 1\n', 'b.py': b'b = 2\n'}
    run_mock = MagicMock()
    monkeypatch.setattr(asyncio, 'run', run_mock)

    assert read_python_files_sync(['a.py', 'b.py']) == [b'a = 1\n', b'b = 2\n']
    assert run_mock.call_count == 0
