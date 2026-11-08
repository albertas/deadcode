from deadcode.actions.remove_file_parts_from_content import remove_as_from_end, remove_file_parts_from_content
from deadcode.data_types import Part


def test_remove_as_from_end_without_whitespace_before_as():
    # Having
    line = b'as'

    # When
    updated_line = remove_as_from_end(line)

    # Then
    assert updated_line == b'as'


def test_leading_comma_on_last_removed_line_is_removed():
    # Having
    content_lines = [b'from x import (\n', b'    foo,\n', b'    bar,\n', b')\n']
    unused_file_parts = [Part(1, 3, 0, 7)]

    # When
    updated_content_lines = remove_file_parts_from_content(content_lines, unused_file_parts)

    # Then
    assert updated_content_lines == [b')\n']


def test_residual_text_after_removed_block_is_kept():
    # Having
    content_lines = [b'foo(\n', b'    bar\n']
    unused_file_parts = [Part(1, 2, 0, 4)]

    # When
    updated_content_lines = remove_file_parts_from_content(content_lines, unused_file_parts)

    # Then
    assert updated_content_lines == [b'bar\n']


def test_comment_before_removed_block_is_kept():
    # Having
    content_lines = [b'# comment before\n', b'unused = 1\n', b'print(2)\n']
    unused_file_parts = [Part(2, 2, 0, 10)]

    # When
    updated_content_lines = remove_file_parts_from_content(content_lines, unused_file_parts)

    # Then
    assert updated_content_lines == [b'# comment before\n', b'print(2)\n']


def test_comment_after_removed_block_is_kept():
    # Having
    content_lines = [b'print(1)\n', b'unused = 1\n', b'# comment after\n']
    unused_file_parts = [Part(2, 2, 0, 10)]

    # When
    updated_content_lines = remove_file_parts_from_content(content_lines, unused_file_parts)

    # Then
    assert updated_content_lines == [b'print(1)\n', b'# comment after\n']


def test_trailing_comment_on_removed_line_is_kept():
    # Having
    content_lines = [b'print(1)\n', b'unused = 1  # comment after\n']
    unused_file_parts = [Part(2, 2, 0, 10)]

    # When
    updated_content_lines = remove_file_parts_from_content(content_lines, unused_file_parts)

    # Then
    assert updated_content_lines == [b'print(1)\n', b'  # comment after\n']
