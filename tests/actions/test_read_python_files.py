import ast
from unittest.mock import MagicMock

import pytest

from deadcode.actions import read_python_files as read_python_files_module
from deadcode.actions.parse_abstract_syntax_tree import parse_abstract_syntax_tree
from deadcode.actions.read_python_files import (
    READ_CHUNK_FILES,
    _read_and_parse_chunk,
    chunk_filenames,
    read_file_chunk,
)
from deadcode.data_types import Args


def test_chunk_filenames_returns_no_chunks_for_empty_input():
    assert chunk_filenames([]) == []


def test_chunk_filenames_uses_the_default_chunk_size():
    filenames = [f'{index}.py' for index in range(70)]

    chunks = chunk_filenames(filenames)

    assert [len(chunk) for chunk in chunks] == [READ_CHUNK_FILES, READ_CHUNK_FILES, 6]
    assert [name for chunk in chunks for name in chunk] == filenames


@pytest.mark.parametrize('chunk_size', [0, -1])
def test_chunk_filenames_treats_a_non_positive_chunk_size_as_one(chunk_size):
    assert chunk_filenames(['a.py', 'b.py'], chunk_size=chunk_size) == [['a.py'], ['b.py']]


def test_read_file_chunk_preserves_order_and_duplicates(virtual_file_system):
    virtual_file_system.files = {'a.py': b'a = 1\n', 'b.py': b'b = 2\n'}

    assert read_file_chunk(['b.py', 'a.py', 'b.py']) == [
        ('b.py', b'b = 2\n'),
        ('a.py', b'a = 1\n'),
        ('b.py', b'b = 2\n'),
    ]


def test_read_file_chunk_opens_every_entry_once(virtual_file_system):
    virtual_file_system.files = {'a.py': b'a = 1\n', 'b.py': b'b = 2\n', 'c.py': b'c = 3\n'}
    open_mock = read_python_files_module.open

    read_file_chunk(['a.py', 'b.py', 'c.py'])

    assert [call.args[0] for call in open_mock.call_args_list] == ['a.py', 'b.py', 'c.py']


def test_read_file_chunk_propagates_os_error(virtual_file_system, monkeypatch):
    monkeypatch.setattr('deadcode.actions.read_python_files.open', MagicMock(side_effect=OSError('boom')))

    with pytest.raises(OSError, match='boom'):
        read_file_chunk(['missing.py'])


def test_read_and_parse_chunk_returns_files_and_trees_in_input_order(virtual_file_system):
    virtual_file_system.files = {'a.py': b'a = 1\n', 'b.py': b'b = 2\n'}

    parsed = _read_and_parse_chunk(['b.py', 'a.py'])

    assert [(filename, content) for filename, content, _tree in parsed] == [
        ('b.py', b'b = 2\n'),
        ('a.py', b'a = 1\n'),
    ]
    assert all(isinstance(tree, ast.Module) for _filename, _content, tree in parsed)


def test_read_and_parse_chunk_returns_none_for_a_syntax_error(virtual_file_system, capsys):
    virtual_file_system.files = {'broken.py': b'def broken(:\n'}

    parsed = _read_and_parse_chunk(['broken.py'])

    assert parsed == [('broken.py', b'def broken(:\n', None)]
    assert capsys.readouterr().out == ''


def test_read_and_parse_chunk_parses_every_file_once(virtual_file_system, monkeypatch):
    virtual_file_system.files = {'a.py': b'a = 1\n', 'b.py': b'b = 2\n'}
    parser = MagicMock(wraps=read_python_files_module.parse_abstract_syntax_tree_or_none)
    monkeypatch.setattr(read_python_files_module, 'parse_abstract_syntax_tree_or_none', parser)

    _read_and_parse_chunk(['a.py', 'b.py'])

    assert parser.call_count == 2


def test_read_and_parse_chunk_propagates_os_error(virtual_file_system, monkeypatch):
    monkeypatch.setattr('deadcode.actions.read_python_files.open', MagicMock(side_effect=OSError('boom')))

    with pytest.raises(OSError, match='boom'):
        _read_and_parse_chunk(['missing.py'])


def test_parse_abstract_syntax_tree_returns_a_parsed_module():
    tree = parse_abstract_syntax_tree(b'x = 1\n', Args(), 'ok.py')

    assert isinstance(tree, ast.Module)
    assert tree.body


def test_parse_abstract_syntax_tree_reports_a_failure_and_returns_an_empty_module(capsys):
    tree = parse_abstract_syntax_tree(b'def broken(:\n', Args(), 'broken.py')

    assert tree.body == []
    assert capsys.readouterr().out.count('Error: Failed to parse broken.py file, ignoring it.') == 1
