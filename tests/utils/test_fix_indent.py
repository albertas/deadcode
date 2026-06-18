from unittest import TestCase

from deadcode.utils.fix_indent import fix_indent


class TestCleandoc(TestCase):
    def test_indentation_is_not_removed_from_second_line(self):
        content = 'class MyTest:\n    pass\n'
        result = fix_indent(content)
        self.assertEqual(content, result)

    def test_fix_indent_for_empty_lines(self):
        indented_text = """\
            file2.py:1:12: DC07 Import `bar` is never used
            file2.py:1:7: DC07 Import `foo` is never used
            file2.py:1:17: DC07 Import `xyz` is never used

            Removed 3 unused code items!"""

        expected_indentation = """\
file2.py:1:12: DC07 Import `bar` is never used
file2.py:1:7: DC07 Import `foo` is never used
file2.py:1:17: DC07 Import `xyz` is never used

Removed 3 unused code items!"""

        text_without_indentation = fix_indent(indented_text)
        self.assertEqual(text_without_indentation, expected_indentation)

## TODO: add test for bytes as well:
#     def test_fix_indent_for_byte_lines(self):
#         indented_text = b"""\
#             file2.py:1:12: DC07 Import `bar` is never used
#             file2.py:1:7: DC07 Import `foo` is never used
#             file2.py:1:17: DC07 Import `xyz` is never used
#
#             Removed 3 unused code items!"""
#
#         expected_indentation = b"""\
# file2.py:1:12: DC07 Import `bar` is never used
# file2.py:1:7: DC07 Import `foo` is never used
# file2.py:1:17: DC07 Import `xyz` is never used
#
# Removed 3 unused code items!"""
#
#         text_without_indentation = fix_indent(indented_text)
#         self.assertEqual(expected_indentation, text_without_indentation)

    def test_fix_indent_last_empty_line(self):
        indented_text = """\
        foo.py:1:0: DC03 Class `UnusedClass` is never used

        --- foo.py
        +++ foo.py
        @@ -1,4 +1 @@
        -class UnusedClass:
        -    pass
        -
         print("Dont change this file")
        """

        expected_indentation = """\
foo.py:1:0: DC03 Class `UnusedClass` is never used

--- foo.py
+++ foo.py
@@ -1,4 +1 @@
-class UnusedClass:
-    pass
-
 print("Dont change this file")
"""

        text_without_indentation = fix_indent(indented_text)
        self.assertEqual(text_without_indentation, expected_indentation)
