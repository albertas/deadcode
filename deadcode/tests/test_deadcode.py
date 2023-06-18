from unittest import TestCase
from unittest.mock import MagicMock, patch

from deadcode.cli import main
from deadcode.actions.parse_arguments import parse_arguments


class BaseTestCase(TestCase):
    def patch(self, path: str) -> MagicMock:
        patcher = patch(path)
        self.addCleanup(patcher.stop)
        return patcher.start()


class FindDeadCodeTests(BaseTestCase):
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

    def test_colorful_output(self):
        self.read_files_mock = self.patch("deadcode.cli.read_files")
        self.read_files_mock.return_value = {
            "tests/files/variables.py": """\
unused_global_variable = True
ANOTHER_GLOBAL_VARIABLE = "This variable is unused"
third_global_varialbe3 = 12 * 25
THIS_ONE_IS_USED = "World"
print(THIS_ONE_IS_USED)"""
        }
        unused_names = main(["tests/files/variables.py"])

        self.assertEqual(
            unused_names,
            (
                "tests/files/variables.py:1:0: \x1b[91mDC100\x1b[0m Global "
                "\x1b[1munused_global_variable\x1b[0m is never used\n"
                "tests/files/variables.py:2:0: \x1b[91mDC100\x1b[0m Global "
                "\x1b[1mANOTHER_GLOBAL_VARIABLE\x1b[0m is never used\n"
                "tests/files/variables.py:3:0: \x1b[91mDC100\x1b[0m Global "
                "\x1b[1mthird_global_varialbe3\x1b[0m is never used"
            ),
        )

    def test_unused_variable_name_found_file_content_patched(self):
        self.read_files_mock = self.patch("deadcode.cli.read_files")
        self.read_files_mock.return_value = {
            "tests/files/variables.py": """\
unused_global_variable = True
ANOTHER_GLOBAL_VARIABLE = "This variable is unused"
third_global_varialbe3 = 12 * 25
THIS_ONE_IS_USED = "World"
print(THIS_ONE_IS_USED)"""
        }
        unused_names = main(["tests/files/variables.py", "--no-color"])

        self.assertEqual(
            unused_names,
            (
                "tests/files/variables.py:1:0: DC100 Global unused_global_variable is never used\n"
                "tests/files/variables.py:2:0: DC100 Global ANOTHER_GLOBAL_VARIABLE is never used\n"
                "tests/files/variables.py:3:0: DC100 Global third_global_varialbe3 is never used"
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


class CommandLineArgParsingTests(BaseTestCase):
    def setUp(self):
        self.tomlib_load_mock = self.patch("deadcode.actions.parse_arguments.tomllib.load")
        self.tomlib_load_mock.return_value = {
            "tool": {
                "deadcode": {
                    "exclude": [],
                    "ignore_names": [],
                    "ignore_names_in_files": [],
                }
            }
        }

    def test_calling_with_one_paths_argument(self):
        args = parse_arguments(["."])
        self.assertEqual(args.paths, ["."])
        self.assertEqual(args.exclude, [])
        self.assertEqual(args.ignore_names, [])
        self.assertEqual(args.ignore_names_in_files, [])

    def test_calling_with_several_paths_argument(self):
        args = parse_arguments([".", "tests"])
        self.assertEqual(args.paths, [".", "tests"])
        self.assertEqual(args.exclude, [])
        self.assertEqual(args.ignore_names, [])
        self.assertEqual(args.ignore_names_in_files, [])

    def test_calling_with_exclude(self):
        args = parse_arguments([".", "--exclude=tests,venv"])
        self.assertEqual(args.paths, ["."])
        self.assertEqual(args.exclude, ["tests", "venv"])
        self.assertEqual(args.ignore_names, [])
        self.assertEqual(args.ignore_names_in_files, [])

    def test_calling_with_several_exclude_options(self):
        args = parse_arguments([".", "--exclude=tests,venv", "--exclude=migrations"])
        self.assertEqual(args.paths, ["."])
        self.assertEqual(args.exclude, ["tests", "venv", "migrations"])
        self.assertEqual(args.ignore_names, [])
        self.assertEqual(args.ignore_names_in_files, [])

    def test_calling_with_no_color_option(self):
        args = parse_arguments([".", "--no-color"])
        self.assertEqual(args.paths, ["."])
        self.assertEqual(args.no_color, True)

    def test_ignore_names_and_ignore_files_command_line_argument_parsing(self):
        args = parse_arguments(
            [
                ".",
                "--ignore-names-in-files=tests,venv",
                "--ignore-names=BaseTestCase,lambda_handler",
            ]
        )
        self.assertEqual(args.paths, ["."])
        self.assertEqual(args.exclude, [])
        self.assertEqual(args.ignore_names, ["BaseTestCase", "lambda_handler"])
        self.assertEqual(args.ignore_names_in_files, ["tests", "venv"])
