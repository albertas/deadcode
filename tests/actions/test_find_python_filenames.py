import tempfile
from pathlib import Path

from deadcode.actions.find_python_filenames import find_python_filenames
from deadcode.utils.base_test_case import BaseTestCase


class TestFindPythonFilenames(BaseTestCase):
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
        (self.pkg / 'notes.txt').write_text('not python\n')

    def test_file_detection(self):
        self.args.paths = [str(self.cli_py)]
        filenames = find_python_filenames(args=self.args)
        self.assertListEqual(filenames, [str(self.cli_py)])

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

    def test_non_python_file_is_skipped(self):
        self.args.paths = [str(self.pkg)]
        filenames = find_python_filenames(args=self.args)
        self.assertFalse(any(f.endswith('notes.txt') for f in filenames))

    def test_provided_path_does_not_exist(self):
        missing = str(self.tree_root / 'path_does_not_exist')
        self.args.paths = [missing]
        with self.assertLogs(level='ERROR') as cm:
            find_python_filenames(args=self.args)
        self.assertEqual(cm.output[0], f'ERROR:root:Error: {missing} could not be found.')

    def test_verbose_logs_ignored_and_listed_files(self):
        self.args.paths = [str(self.cli_py)]
        self.args.exclude = [str(self.cli_py)]
        self.args.verbose = True
        with self.assertLogs(level='INFO') as cm:
            find_python_filenames(args=self.args)
        assert any('Ignoring' in message for message in cm.output)
        assert any('Files to be checked' in message for message in cm.output)
