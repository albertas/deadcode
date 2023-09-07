from deadcode.tests.base import BaseTestCase
from deadcode.actions.find_python_filenames import find_python_filenames


class TestExcludeCliArgUnit(BaseTestCase):
    def test_exclude_directories(self):
        self.args.paths = ["."]
        filenames = find_python_filenames(args=self.args)
        self.assertTrue(any(f.startswith("tests") for f in filenames))
        self.assertTrue(any(f.startswith("utils") for f in filenames))

        self.args.exclude = ["tests", "utils"]
        filenames = find_python_filenames(args=self.args)
        self.assertFalse(any(f.startswith("tests") for f in filenames))
        self.assertFalse(any(f.startswith("utils") for f in filenames))

    def test_exclude_files(self):
        self.args.paths = ["."]
        filenames = find_python_filenames(args=self.args)
        self.assertTrue("cli.py" in filenames)

        self.args.exclude = ["cli.py"]
        filenames = find_python_filenames(args=self.args)
        self.assertFalse("cli.py" in filenames)
