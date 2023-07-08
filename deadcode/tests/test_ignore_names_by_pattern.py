from deadcode.cli import main
from deadcode.tests.base import BaseTestCase


class IgnoreNamesByPatternTests(BaseTestCase):
    def setUp(self):
        self.read_files_mock = self.patch("deadcode.cli.read_files")

    def test_ignore_names_matched_exactly(self):
        self.read_files_mock.return_value = {
            "ignore_names_by_pattern.py": """
class MyModel:
    pass

class MyUserModel:
    pass

class Unused:
    pass

class ThisClassShouldBeIgnored:
    pass
"""
        }
        unused_names = main(
            ["ignore_names_by_pattern.py", "--no-color", "--ignore-names=MyModel,MyUserModel,ThisClassShouldBeIgnored"]
        )

        self.assertEqual(
            unused_names,
            ("ignore_names_by_pattern.py:8:6: DC100 Global Unused is never used"),
        )

    def test_ignore_names_matched_by_word_and_group_regexp_patterns(self):
        self.read_files_mock.return_value = {
            "ignore_names_by_pattern.py": """
class MyModel:
    pass

class MyUserModel:
    pass

class Unused:
    pass

class ThisClassShouldBeIgnored:
    pass
"""
        }
        unused_names = main(["ignore_names_by_pattern.py", "--no-color", "--ignore-names=\\w*Model,.*[Ii]{1}gnore.*"])

        self.assertEqual(
            unused_names,
            ("ignore_names_by_pattern.py:8:6: DC100 Global Unused is never used"),
        )

    def test_ignore_names_matched_by_dot_regexp_pattern(self):
        self.read_files_mock.return_value = {
            "ignore_names_by_pattern.py": """
class MyModel:
    pass

class MyUserModel:
    pass

class Unused:
    pass

class ThisClassShouldBeIgnored:
    pass
"""
        }
        unused_names = main(["ignore_names_by_pattern.py", "--no-color", "--ignore-names=.*Model,.*Ignore.*"])

        self.assertEqual(
            unused_names,
            ("ignore_names_by_pattern.py:8:6: DC100 Global Unused is never used"),
        )
