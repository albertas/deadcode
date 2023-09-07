from deadcode.actions.find_python_filenames import find_python_filenames
from deadcode.tests.base import BaseTestCase


class TestFindPythonFilenames(BaseTestCase):
    def test_file_detection(self):
        self.args.paths = ["./cli.py"]
        filenames = find_python_filenames(args=self.args)
        self.assertListEqual(filenames, ["cli.py"])

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

    def test_provided_path_does_not_exist(self):
        self.args.paths = ["path_does_not_exist"]
        with self.assertLogs(level="ERROR") as cm:
            find_python_filenames(args=self.args)

        self.assertEqual(cm.output[0], "ERROR:root:Error: path_does_not_exist could not be found.")
