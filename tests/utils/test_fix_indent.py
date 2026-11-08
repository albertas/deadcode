from deadcode.utils.fix_indent import fix_indent


def test_indentation_is_not_removed_from_second_line():
    content = b'class MyTest:\n    pass\n'
    result = fix_indent(content)
    assert content == result
