import ast

from deadcode.actions.get_unused_import_parts import (  # noqa: PLC2701
    _end_of_line_content,
    _find_byte,
    _find_comma_between,
    _line_bytes,
    get_import_alias_key,
    get_unused_import_parts,
)
from deadcode.data_types import Part
from deadcode.visitor.code_item import CodeItem


def make_import_item(name: str, name_line: int, name_column: int, code_parts: list[Part] | None = None) -> CodeItem:
    return CodeItem(
        name=name,
        type_='import',
        filename=__file__,
        code_parts=code_parts,
        name_line=name_line,
        name_column=name_column,
    )


def make_alias(name: str, line: int, column: int, end_line: int | None, end_column: int | None) -> ast.alias:
    alias = ast.alias(name=name)
    alias.lineno = line
    alias.col_offset = column
    if end_line is not None:
        alias.end_lineno = end_line
    if end_column is not None:
        alias.end_col_offset = end_column
    return alias


def make_import_node(aliases: list[ast.alias], end_line: int | None = 1, end_column: int | None = 20) -> ast.Import:
    node = ast.Import(names=aliases)
    node.lineno = 1
    node.col_offset = 0
    if end_line is not None:
        node.end_lineno = end_line
    if end_column is not None:
        node.end_col_offset = end_column
    return node


def test_import_alias_key_uses_alias_name():
    # Having
    alias = make_alias('foo.bar', 3, 4, 3, 11)

    # When
    key = get_import_alias_key(alias)

    # Then
    assert key == ('foo', 3, 4)


def test_line_bytes_outside_content_is_empty():
    # Having
    content_lines = [b'a\n', b'b\n']

    # When
    before_first = _line_bytes(content_lines, 0)
    after_last = _line_bytes(content_lines, 3)

    # Then
    assert before_first == b''
    assert after_last == b''


def test_find_byte_returns_none_when_needle_is_missing():
    # Having
    content_lines = [b'abc\n']

    # When
    position = _find_byte(content_lines, 1, 0, 3, b',')

    # Then
    assert position is None


def test_find_comma_on_single_line():
    # Having
    content_lines = [b'import foo, bar\n']

    # When
    comma = _find_comma_between(content_lines, (1, 10), (1, 15))

    # Then
    assert comma == (1, 10)


def test_find_comma_on_start_line_of_range():
    # Having
    content_lines = [b'import foo,\n', b'    bar\n']

    # When
    comma = _find_comma_between(content_lines, (1, 10), (2, 4))

    # Then
    assert comma == (1, 10)


def test_find_comma_on_end_line_of_range():
    # Having
    content_lines = [b'import foo\n', b'    ,bar\n']

    # When
    comma = _find_comma_between(content_lines, (1, 10), (2, 5))

    # Then
    assert comma == (2, 4)


def test_find_comma_on_middle_line_of_range():
    # Having
    content_lines = [b'foo\n', b'    ,\n', b'bar\n']

    # When
    comma = _find_comma_between(content_lines, (1, 0), (3, 2))

    # Then
    assert comma == (2, 4)


def test_find_comma_returns_none_when_absent():
    # Having
    content_lines = [b'foo\n', b'bar\n']

    # When
    comma = _find_comma_between(content_lines, (1, 0), (2, 3))

    # Then
    assert comma is None


def test_end_of_line_content_without_terminator():
    # Having
    content_lines = [b'abc']

    # When
    end = _end_of_line_content(content_lines, 1)

    # Then
    assert end == 3


def test_unparsable_content_falls_back_to_code_parts():
    # Having
    fallback_part = Part(1, 1, 0, 5)
    item = make_import_item('foo', 1, 7, [fallback_part])

    # When
    parts = get_unused_import_parts(b'from x import (\n', [item])

    # Then
    assert parts == [fallback_part]


def test_import_node_without_end_position_is_skipped(monkeypatch):
    # Having
    alias = make_alias('foo', 1, 7, 1, 10)
    node = make_import_node([alias], end_line=None, end_column=None)
    monkeypatch.setattr(
        'deadcode.actions.get_unused_import_parts.ast.parse',
        lambda *_args, **_kwargs: ast.Module(body=[node]),
    )
    item = make_import_item('foo', 1, 7)

    # When
    parts = get_unused_import_parts(b'import foo\n', [item])

    # Then
    assert parts == []


def test_last_alias_with_previous_alias_without_end_position(monkeypatch):
    # Having
    foo = make_alias('foo', 1, 7, None, None)
    bar = make_alias('bar', 1, 11, 1, 14)
    node = make_import_node([foo, bar])
    monkeypatch.setattr(
        'deadcode.actions.get_unused_import_parts.ast.parse',
        lambda *_args, **_kwargs: ast.Module(body=[node]),
    )
    items = [make_import_item('bar', 1, 11)]

    # When
    parts = get_unused_import_parts(b'import foo, bar\n', items)

    # Then
    assert parts == [Part(1, 1, 11, 14)]


def test_next_alias_without_comma_is_skipped(monkeypatch):
    # Having
    foo = make_alias('foo', 1, 7, 1, 10)
    bar = make_alias('bar', 1, 11, 1, 14)
    node = make_import_node([foo, bar])
    monkeypatch.setattr(
        'deadcode.actions.get_unused_import_parts.ast.parse',
        lambda *_args, **_kwargs: ast.Module(body=[node]),
    )
    items = [make_import_item('foo', 1, 7)]

    # When
    parts = get_unused_import_parts(b'import foo bar\n', items)

    # Then
    assert parts == []


def test_last_alias_without_comma_before_it_is_skipped(monkeypatch):
    # Having
    foo = make_alias('foo', 1, 7, 1, 10)
    bar = make_alias('bar', 1, 11, 1, 14)
    node = make_import_node([foo, bar])
    monkeypatch.setattr(
        'deadcode.actions.get_unused_import_parts.ast.parse',
        lambda *_args, **_kwargs: ast.Module(body=[node]),
    )
    items = [make_import_item('bar', 1, 11)]

    # When
    parts = get_unused_import_parts(b'import foo bar\n', items)

    # Then
    assert parts == []
