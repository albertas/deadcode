from deadcode.cli import main, print_main
from deadcode.utils.base_test_case import BaseTestCase


class TestCliExitStatus(BaseTestCase):
    def test_findings_exit_with_status_one(self):
        self.files = {'sample.py': b'unused_variable = 1\n'}

        self.assertEqual(print_main(['sample.py', '--no-color']), 1)

    def test_clean_file_exits_with_status_zero(self):
        self.files = {'sample.py': b'print("Hello")\n'}

        self.assertEqual(print_main(['sample.py', '--no-color']), 0)

    def test_version_exits_with_status_zero(self):
        self.assertEqual(print_main(['--version']), 0)

    def test_main_still_returns_findings_message(self):
        self.files = {'sample.py': b'unused_variable = 1\n'}

        self.assertEqual(
            main(['sample.py', '--no-color']),
            'sample.py:1:0: DC01 Variable `unused_variable` is never used',
        )

    def test_main_returns_none_for_clean_file(self):
        self.files = {'sample.py': b'print("Hello")\n'}

        self.assertIsNone(main(['sample.py', '--no-color']))

    def test_findings_with_quiet_exit_with_status_one_without_output(self):
        self.files = {'sample.py': b'unused_variable = 1\n'}
        print_safely = self.patch('deadcode.cli.print_safely')

        self.assertEqual(print_main(['sample.py', '--no-color', '--quiet']), 1)

        print_safely.assert_not_called()

    def test_findings_with_count_exit_with_status_one(self):
        self.files = {'sample.py': b'unused_variable = 1\n'}

        self.assertEqual(print_main(['sample.py', '--no-color', '--count']), 1)

    def test_findings_with_no_color_exit_with_status_one(self):
        self.files = {'sample.py': b'unused_variable = 1\n'}

        self.assertEqual(print_main(['sample.py', '--no-color']), 1)

    def test_findings_with_only_exit_with_status_one(self):
        self.files = {
            'sample.py': b'unused_variable = 1\n',
            'other.py': b'another_unused_variable = 2\n',
        }

        self.assertEqual(print_main(['sample.py', '--no-color', '--only', 'sample.py']), 1)

    def test_clean_file_with_count_exits_with_status_zero(self):
        self.files = {'sample.py': b'print("Hello")\n'}

        self.assertEqual(print_main(['sample.py', '--no-color', '--count']), 0)

    def test_clean_file_with_quiet_exits_with_status_zero(self):
        self.files = {'sample.py': b'print("Hello")\n'}

        self.assertEqual(print_main(['sample.py', '--no-color', '--quiet']), 0)

    def test_findings_with_dry_exit_with_status_one_and_do_not_write(self):
        original_content = b'unused_variable = 1\nprint("Keep")\n'
        self.files = {'sample.py': original_content}

        self.assertEqual(print_main(['sample.py', '--no-color', '--dry']), 1)

        self.assertFiles({'sample.py': original_content})

    def test_findings_with_fix_exit_with_status_one_then_zero_after_fix(self):
        self.files = {'sample.py': b'unused_variable = 1\nprint("Keep")\n'}

        self.assertEqual(print_main(['sample.py', '--no-color', '--fix']), 1)
        self.assertFiles({'sample.py': b'print("Keep")\n'})

        self.files = {'sample.py': b'print("Keep")\n'}

        self.assertEqual(print_main(['sample.py', '--no-color', '--fix']), 0)
