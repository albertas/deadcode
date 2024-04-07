from deadcode.utils.base_test_case import BaseTestCase
from deadcode.actions.find_python_filenames import find_python_filenames


class TestExcludeCliArgUnit(BaseTestCase):
    def test_exclude_directories(self):
        self.args.paths = ['deadcode/.']
        filenames = find_python_filenames(args=self.args)
        self.assertTrue(any(f.startswith('deadcode/cli.py') for f in filenames))
        self.assertTrue(any(f.startswith('deadcode/utils') for f in filenames))

        self.args.exclude = ['deadcode/utils', 'deadcode/cli.py']
        filenames = find_python_filenames(args=self.args)
        self.assertFalse(any(f.startswith('deadcode/cli.py') for f in filenames))
        self.assertFalse(any(f.startswith('deadcode/utils') for f in filenames))

    def test_exclude_files(self):
        self.args.paths = ['deadcode/.']
        filenames = find_python_filenames(args=self.args)
        self.assertTrue('deadcode/cli.py' in filenames)

        self.args.exclude = ['deadcode/cli.py']
        filenames = find_python_filenames(args=self.args)
        self.assertFalse('deadcode/cli.py' in filenames)
