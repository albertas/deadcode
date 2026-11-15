from unittest.mock import MagicMock

import pytest

from deadcode.actions import read_python_files as read_python_files_module
from deadcode.actions.read_python_files import chunk_filenames, read_file_chunk


def test_reads_files_in_input_order_including_duplicate_filenames(virtual_file_system):
    virtual_file_system.files = {'a.py': b'a = 1\n', 'b.py': b'b = 2\n'}

    assert read_file_chunk(['a.py', 'b.py', 'a.py']) == [b'a = 1\n', b'b = 2\n', b'a = 1\n']


def test_each_distinct_filename_is_opened_once(virtual_file_system):
    virtual_file_system.files = {'a.py': b'a = 1\n', 'b.py': b'b = 2\n', 'c.py': b'c = 3\n'}
    open_mock = read_python_files_module.open

    read_file_chunk(['a.py', 'b.py', 'c.py'])

    opened_filenames = [call.args[0] for call in open_mock.call_args_list]
    assert opened_filenames == ['a.py', 'b.py', 'c.py']


def test_chunk_filenames_splits_the_input_preserving_order():
    filenames = [f'{index}.py' for index in range(5)]

    assert chunk_filenames(filenames, chunk_size=2) == [['0.py', '1.py'], ['2.py', '3.py'], ['4.py']]


def test_chunk_filenames_rejects_a_non_positive_chunk_size():
    assert chunk_filenames(['a.py', 'b.py'], chunk_size=0) == [['a.py'], ['b.py']]


def test_chunk_filenames_returns_no_chunks_for_empty_input():
    assert chunk_filenames([]) == []


def test_os_error_propagates_unwrapped(virtual_file_system, monkeypatch):
    monkeypatch.setattr(
        'deadcode.actions.read_python_files.open',
        MagicMock(side_effect=OSError('boom')),
    )

    with pytest.raises(OSError, match='boom'):
        read_file_chunk(['missing.py'])
