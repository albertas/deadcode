from unittest import TestCase

from deadcode.utils.fix_indent import fix_indent


class TestCleandoc(TestCase):
    def test_indentation_is_not_removed_from_second_line(self):
        content = 'class MyTest:\n    pass\n'
        result = fix_indent(content)
        self.assertEqual(content, result)
