"""
These tests should test command line value conversion into internal Args instance.
"""

from deadcode.actions.parse_arguments import parse_arguments
from deadcode.tests.base import BaseTestCase


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
