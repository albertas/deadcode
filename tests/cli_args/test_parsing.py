"""
These tests should test command line value conversion into internal Args instance.
"""

from deadcode.actions.parse_arguments import parse_arguments
from deadcode.utils.base_test_case import BaseTestCase


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
        options = "."
        args = parse_arguments(options.split())
        self.assertEqual(args.paths, ["."])
        self.assertEqual(args.exclude, [])
        self.assertEqual(args.ignore_names, [])
        self.assertEqual(args.ignore_names_in_files, [])

    def test_calling_with_several_paths_argument(self):
        options = ". tests"
        args = parse_arguments(options.split())
        self.assertEqual(args.paths, [".", "tests"])
        self.assertEqual(args.exclude, [])
        self.assertEqual(args.ignore_names, [])
        self.assertEqual(args.ignore_names_in_files, [])

    def test_calling_with_exclude(self):
        options = ". --exclude=tests,venv"
        args = parse_arguments(options.split())
        self.assertEqual(args.paths, ["."])
        self.assertEqual(args.exclude, ["tests", "venv"])
        self.assertEqual(args.ignore_names, [])
        self.assertEqual(args.ignore_names_in_files, [])

    def test_calling_with_several_exclude_options(self):
        options = ". --exclude=tests,venv --exclude=migrations"
        args = parse_arguments(options.split())
        self.assertEqual(args.paths, ["."])
        self.assertEqual(args.exclude, ["tests", "venv", "migrations"])
        self.assertEqual(args.ignore_names, [])
        self.assertEqual(args.ignore_names_in_files, [])

    def test_calling_with_no_color_option(self):
        options = ". --no-color"
        args = parse_arguments(options.split())
        self.assertEqual(args.paths, ["."])
        self.assertEqual(args.no_color, True)

    def test_ignore_names_and_ignore_files_command_line_argument_parsing(self):
        options = ". --ignore-names-in-files=tests,venv --ignore-names=BaseTestCase,lambda_handler"
        args = parse_arguments(options.split())
        self.assertEqual(args.paths, ["."])
        self.assertEqual(args.exclude, [])
        self.assertEqual(args.ignore_names, ["BaseTestCase", "lambda_handler"])
        self.assertEqual(args.ignore_names_in_files, ["tests", "venv"])

    def test_verbose_flag_is_on_using_long_name(self):
        options = "--verbose ."
        args = parse_arguments(options.split())
        self.assertEqual(args.verbose, True)
        self.assertEqual(args.paths, ["."])

    def test_verbose_flag_is_on_using_short_name(self):
        options = ". -v"
        args = parse_arguments(options.split())
        self.assertEqual(args.paths, ["."])
        self.assertEqual(args.verbose, True)

    def test_calling_with_fix(self):
        options = ". --fix"
        args = parse_arguments(options.split())
        self.assertEqual(args.paths, ["."])
        self.assertEqual(args.dry, [])
        self.assertEqual(args.fix, True)

    def test_calling_with_dry(self):
        options = ". --dry --verbose"
        args = parse_arguments(options.split())
        self.assertEqual(args.paths, ["."])
        self.assertEqual(args.dry, ["__all_files__"])
        self.assertEqual(args.verbose, True)
        self.assertEqual(args.fix, False)

    def test_calling_with_fix_and_dry(self):
        options = ". --dry --fix"
        args = parse_arguments(options.split())
        self.assertEqual(args.dry, ["__all_files__"])
        self.assertEqual(args.fix, False)

    def test_calling_with_single_dry_filename(self):
        options = ". --dry foo.py --fix"
        args = parse_arguments(options.split())
        self.assertEqual(args.paths, ["."])
        self.assertEqual(args.dry, ["foo.py"])
        self.assertEqual(args.fix, False)

    def test_calling_with_two_dry_filenames(self):
        options = ". --fix --dry foo.py bar.py"
        args = parse_arguments(options.split())
        self.assertEqual(args.paths, ["."])
        self.assertEqual(args.dry, ["foo.py", "bar.py"])
        self.assertEqual(args.fix, False)
