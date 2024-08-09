from deadcode import __version__
from deadcode.cli import main
from deadcode.utils.base_test_case import BaseTestCase


class TestVersionCliOption(BaseTestCase):
    def test_show_version(self):
        self.files = {
            'foo.py': b"""
                class UnusedClass:
                    pass

                print("Dont change this file")""",
            'bar.py': b"""
                def unused_function():
                    pass

                print("Dont change this file")""",
        }

        result = main('--version'.split())

        self.assertEqual(result, __version__)

    def test_show_version_when_path_provided(self):
        self.files = {
            'foo.py': b"""
                class UnusedClass:
                    pass

                print("Dont change this file")""",
            'bar.py': b"""
                def unused_function():
                    pass

                print("Dont change this file")""",
        }

        result = main('. --version'.split())

        self.assertEqual(result, __version__)
