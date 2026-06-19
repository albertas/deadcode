import tempfile
from pathlib import Path

from deadcode.utils.base_test_case import BaseTestCase
from deadcode.actions.find_python_filenames import find_python_filenames


class TestExcludeCliArgUnit(BaseTestCase):
    def setUp(self):
        super().setUp()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tree_root = Path(self._tmp.name)

        self.pkg = self.tree_root / 'pkg'
        self.utils = self.pkg / 'utils'
        self.utils.mkdir(parents=True)
        self.cli_py = self.pkg / 'cli.py'
        self.cli_py.write_text('x = 1\n')
        (self.utils / 'helper.py').write_text('y = 2\n')

    def test_exclude_directories(self):
        self.args.paths = [str(self.pkg)]
        filenames = find_python_filenames(args=self.args)
        self.assertTrue(any(f == str(self.cli_py) for f in filenames))
        self.assertTrue(any(str(self.utils) in f for f in filenames))

        self.args.exclude = [str(self.utils), str(self.cli_py)]
        filenames = find_python_filenames(args=self.args)
        self.assertFalse(any(f == str(self.cli_py) for f in filenames))
        self.assertFalse(any(str(self.utils) in f for f in filenames))

    def test_exclude_files(self):
        self.args.paths = [str(self.pkg)]
        filenames = find_python_filenames(args=self.args)
        self.assertTrue(str(self.cli_py) in filenames)

        self.args.exclude = [str(self.cli_py)]
        filenames = find_python_filenames(args=self.args)
        self.assertFalse(str(self.cli_py) in filenames)
