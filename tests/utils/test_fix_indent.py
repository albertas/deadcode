from deadcode.utils.fix_indent import fix_indent


def test_indentation_is_not_removed_from_second_line():
    # Having
    content = b'class MyTest:\n    pass\n'

    # When
    result = fix_indent(content)

    # Then
    assert content == result
