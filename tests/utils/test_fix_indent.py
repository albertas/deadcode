from deadcode.utils.fix_indent import fix_indent


def test_indentation_is_not_removed_from_second_line():
    # Having
    content = b'class MyTest:\n    pass\n'

    # When
    result = fix_indent(content)

    # Then
    assert content == result


def test_leading_blank_lines_are_removed_from_text():
    # Having
    content = '\n\nclass MyTest:\n    pass\n'

    # When
    result = fix_indent(content)

    # Then
    assert result == 'class MyTest:\n    pass\n'


def test_unsupported_value_returns_none():
    # Having
    content = None

    # When
    result = fix_indent(content)  # type: ignore[type-var]

    # Then
    assert result is None
