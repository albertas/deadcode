"""
Test empty files detection and removal.
"""

from deadcode.cli import main
from deadcode.utils.base_test_case import BaseTestCase


class TestAssignmentExpressionRemoval(BaseTestCase):
    def test_file_removal(self):
        self.files = {
            'foo.py': b"""
                """
        }

        unused_names = main(['foo.py', '--no-color', '--fix'])
        self.assertEqual(
            unused_names,
            ('foo.py DC11 Empty file\n\n' 'Removed 1 unused code item!'),
        )

        self.assertFiles({}, removed=['foo.py'])

    def test_file_removal_from_subpath(self):
        self.files = {
            'bar/foo.py': b"""
                """
        }

        unused_names = main(['bar/foo.py', '--no-color', '--fix'])
        self.assertEqual(
            unused_names,
            ('bar/foo.py DC11 Empty file\n\n' 'Removed 1 unused code item!'),
        )

        self.assertFiles({}, removed=['bar/foo.py'])
