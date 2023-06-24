from deadcode.cli import main
from deadcode.tests.base import BaseTestCase


class IgnoreNamesByPatternTests(BaseTestCase):
    def test_count_several_classes(self):
        # Having
        self.read_files_mock = self.patch("deadcode.cli.read_files")
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

        # When
        unused_name_count = main(["ignore_names_by_pattern.py", "--no-color", "--count"])

        # Then
        self.assertEqual(unused_name_count, "4")

    def test_count_variables_function_and_class(self):
        # Having
        self.read_files_mock = self.patch("deadcode.cli.read_files")
        self.read_files_mock.return_value = {
            "ignore_names_by_pattern.py": """
first_variable = 0
def this_is_a_function():
    pass
class MyModel:
    def __init__(self):
        pass
"""
        }

        # When
        unused_name_count = main(["ignore_names_by_pattern.py", "--no-color", "--count"])

        # Then
        self.assertEqual(unused_name_count, "3")
