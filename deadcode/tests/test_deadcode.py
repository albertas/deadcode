from deadcode.cli import main
from deadcode.tests.base import BaseTestCase


class DeadCodeIntegrationTests(BaseTestCase):
    def test_unused_variable_name_found(self):
        unused_names = main(["tests/files/variables.py", "--no-color"])

        self.assertEqual(
            unused_names,
            (
                "tests/files/variables.py:1:0: DC100 Global unused_global_variable is never used\n"
                "tests/files/variables.py:3:0: DC100 Global ANOTHER_GLOBAL_VARIABLE is never used\n"
                "tests/files/variables.py:5:0: DC100 Global third_global_varialbe is never used"
            ),
        )

    def test_unused_function_name_found(self):
        unused_names = main(["tests/files/functions.py", "--no-color"])

        self.assertEqual(
            unused_names,
            (
                "tests/files/functions.py:1:4: DC100 Global unused_function is never used\n"
                "tests/files/functions.py:13:4: DC100 Global another_unused_function is never used"
            ),
        )

    def test_unused_class_name_found(self):
        unused_names = main(["tests/files/classes.py", "--no-color"])

        self.assertEqual(
            unused_names,
            (
                "tests/files/classes.py:1:6: DC100 Global UnusedClass is never used\n"
                "tests/files/classes.py:13:6: DC100 Global AnotherUnusedClass is never used"
            ),
        )

    def test_invalid_python_file_found(self):
        self.read_files_mock = self.patch("deadcode.cli.read_files")
        self.read_files_mock.return_value = {"tests/files/invalid_file.py": """This is invalid python file content."""}
        unused_names = main(["tests/files/invalid_file.py", "--no-color"])

        self.assertEqual(unused_names, None)

    def test_file_contains_syntax_error(self):
        pass

    def test_reliably_remove_comments_by_using_ast_parse_and_ast_unparse(self):
        pass

    def test_parse_variable_usage_expressions_from_whole_ast_dump(self):
        pass

    def test_unused_names_found_in_subdirectories(self):
        pass

    def test_exclude_option(self):
        pass

    def test_ignore_names_option(self):
        pass

    def test_ignore_names_in_files_option(self):
        pass

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
                "tests/files/variables.py:1:0: DC100 Global unused_global_variable is never used\n"
                "tests/files/variables.py:3:0: DC100 Global ANOTHER_GLOBAL_VARIABLE is never used\n"
                "tests/files/variables.py:5:0: DC100 Global third_global_varialbe is never used"
            ),
        )

    def test_variable_is_marked_as_used_even_if_its_imported_as_a_different_name(self):
        pass
