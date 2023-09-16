from unittest import TestCase

from deadcode.cli import main
from deadcode.tests.base import BaseTestCase


class DeadCodeIntegrationTests(TestCase):
    def test_unused_variable_name_found_successfully(self):
        unused_names = main(["tests/files/variables.py", "--no-color"])

        self.assertEqual(
            unused_names,
            (
                "tests/files/variables.py:1:0: DC001 Variable `unused_global_variable` is never used\n"
                "tests/files/variables.py:3:0: DC001 Variable `ANOTHER_GLOBAL_VARIABLE` is never used\n"
                "tests/files/variables.py:5:0: DC001 Variable `third_global_varialbe` is never used"
            ),
        )

    def test_unused_function_name_found(self):
        unused_names = main(["tests/files/functions.py", "--no-color"])

        self.assertEqual(
            unused_names,
            (
                "tests/files/functions.py:1:0: DC002 Function `unused_function` is never used\n"
                "tests/files/functions.py:13:0: DC002 Function `another_unused_function` is never used\n"
                "tests/files/functions.py:14:4: DC002 Function `this_is_unused_closure` is never used"
            ),
        )

    def test_unused_class_name_found(self):
        unused_names = main(["tests/files/classes.py", "--no-color"])

        # TODO: Scope of a variable in the output would be really helpful (class name, function)
        # - dotted notation would suite perfectly
        self.assertEqual(
            unused_names,
            (
                "tests/files/classes.py:1:0: DC003 Class `UnusedClass` is never used\n"
                "tests/files/classes.py:13:0: DC003 Class `AnotherUnusedClass` is never used"
            ),
        )

    def test_run_dead_code_finder_with_a_subprocess_in_a_right_directory_main(self):
        unused_names = main(
            [
                "tests/files/variables.py",
                "deadcode/tests/files/variables.py",
                "--no-color",
            ]
        )
        self.assertEqual(
            unused_names,
            (
                "tests/files/variables.py:1:0: DC001 Variable `unused_global_variable` is never used\n"
                "tests/files/variables.py:3:0: DC001 Variable `ANOTHER_GLOBAL_VARIABLE` is never used\n"
                "tests/files/variables.py:5:0: DC001 Variable `third_global_varialbe` is never used"
            ),
        )


class DeadCodeTests(BaseTestCase):
    def test_invalid_python_file_found(self):
        self.files = {"tests/files/invalid_file.py": """This is invalid python file content."""}
        unused_names = main(["tests/files/invalid_file.py", "--no-color"])

        self.assertEqual(unused_names, None)
