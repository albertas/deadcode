import ast
from types import SimpleNamespace

import pytest

from deadcode.actions import parse_abstract_syntax_tree as seam
from deadcode.data_types import Args

PARSEABLE_CONTENT = b'import os\n\n\ndef main():\n    pass\n'
UNPARSEABLE_CONTENT = b'def broken(:\n'
FILENAME = 'example.py'


class NativeParseError(Exception):
    """Mimics the `ParseError` exception the native module defines."""


def make_native(parse_module):
    return SimpleNamespace(ParseError=NativeParseError, parse_module=parse_module)


def dump(tree):
    return ast.dump(tree, include_attributes=True)


def test_native_module_absent_falls_back_to_ast_parse(monkeypatch):
    monkeypatch.setattr(seam, 'load_native', lambda: None)

    result = seam.parse_abstract_syntax_tree(PARSEABLE_CONTENT, Args(), FILENAME)
    expected = ast.parse(PARSEABLE_CONTENT, filename=FILENAME, type_comments=True)

    assert dump(result) == dump(expected)


def test_native_stub_error_falls_back_to_ast_parse(monkeypatch):
    def parse_module(source, filename, type_comments):
        raise RuntimeError  # A stand-in for the stub's "not implemented" error.

    monkeypatch.setattr(seam, 'load_native', lambda: make_native(parse_module))

    result = seam.parse_abstract_syntax_tree(PARSEABLE_CONTENT, Args(), FILENAME)
    expected = ast.parse(PARSEABLE_CONTENT, filename=FILENAME, type_comments=True)

    assert dump(result) == dump(expected)


def test_native_parse_rejection_maps_into_the_failure_contract(monkeypatch, capsys):
    def parse_module(source, filename, type_comments):
        raise NativeParseError  # Any ParseError rejection lands in the failure contract.

    monkeypatch.setattr(seam, 'load_native', lambda: make_native(parse_module))

    result = seam.parse_abstract_syntax_tree(UNPARSEABLE_CONTENT, Args(), FILENAME)

    assert dump(result) == dump(ast.Module(body=[], type_ignores=[]))
    assert capsys.readouterr().out == f'Error: Failed to parse {FILENAME} file, ignoring it.\n'


@pytest.mark.parametrize('suppressor', [{'count': True}, {'quiet': True}])
def test_parse_failure_message_suppressed(monkeypatch, capsys, suppressor):
    monkeypatch.setattr(seam, 'load_native', lambda: None)

    result = seam.parse_abstract_syntax_tree(UNPARSEABLE_CONTENT, Args(**suppressor), FILENAME)

    assert dump(result) == dump(ast.Module(body=[], type_ignores=[]))
    assert capsys.readouterr().out == ''
