"""
Test method def.
"""

from deadcode.cli import main
from deadcode.utils.base_test_case import BaseTestCase


class TestUnusedMethodRemoval(BaseTestCase):
    def test_method(self):
        self.files = {
            "foo.py": """
                class MyTest:
                    def some_method(self):
                        pass

                instance = MyTest()
                print(instance)
                """
        }

        main(["foo.py", "--no-color", "--fix"])

        self.assertFiles(
            {
                "foo.py": """
            class MyTest:
                pass

            instance = MyTest()
            print(instance)
        """
            }
        )

    def test_method_at_the_end_of_file(self):
        self.files = {
            "bar.py": """
                class MyTest:
                    def some_method(self):
                        pass
                """,
            "foo.py": """
                from foo import MyTest

                instance = MyTest()
                print(instance)
                """,
        }

        main(["foo.py", "--no-color", "--fix"])

        self.assertFiles(
            {
                "bar.py": """
            class MyTest:
                pass
            """,
                "foo.py": """
                from foo import MyTest

                instance = MyTest()
                print(instance)
            """,
            }
        )
