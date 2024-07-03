"""
Test unused assignment expression detection and removal.
"""

from unittest import skip

from deadcode.cli import main
from deadcode.utils.base_test_case import BaseTestCase


class TestAssignmentExpressionRemoval(BaseTestCase):
    def test_variable(self):
        self.files = {
            'foo.py': b"""
                unused_variable = 123
                print("Keep the file")
                """
        }

        unused_names = main(['foo.py', '--no-color', '--fix'])
        self.assertEqual(
            unused_names,
            ('foo.py:1:0: DC01 Variable `unused_variable` is never used\n\n' 'Removed 1 unused code item!'),
        )

        self.assertFiles(
            {
                'foo.py': b"""
                print("Keep the file")
            """
            }
        )

    @skip
    def test_variable_with_type_hint(self):
        self.files = {
            'foo.py': b"""
            unused_variable: List[int] = [123]
        """
        }

        unused_names = main(['foo.py', '--no-color', '--fix'])
        self.assertEqual(
            unused_names,
            ('foo.py:1:0: DC01 Variable `unused_variable` is never used\n\n' 'Removed 1 unused code item!'),
        )

        self.assertFiles({'foo.py': b""""""})

    @skip
    def test_unused_variable_in_multiple_inline_assignment_start(self):
        self.files = {
            'foo.py': b"""
            foo, bar, spam = None, [], "Spam"
            print(bar, spam)
        """
        }

    @skip
    def test_unused_variable_in_multiple_inline_assignment_end(self):
        self.files = {
            'foo.py': b"""
            foo, bar, spam = None, [], "Spam"
            print(foo, bar)
        """
        }

    @skip
    def test_unused_variable_in_multiple_inline_assignment_middle(self):
        self.files = {
            'foo.py': b"""
            foo, bar, spam = None, [], "Spam"
            print(foo, spam)
        """
        }

    @skip
    def test_multiple_unused_variables_in_multiple_inline_assignment(self):
        self.files = {
            'foo.py': b"""
            foo, bar, spam = None, [], "Spam"
            print(spam)
        """
        }

    @skip
    def test_all_unused_variables_in_multiple_inline_assignment(self):
        self.files = {
            'foo.py': b"""
            foo, bar, spam = None, [], "Spam"
        """
        }
