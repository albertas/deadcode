"""
Test class def.
"""
from unittest import skip

from deadcode.cli import main
from deadcode.tests.base import BaseTestCase


class TestClassDefRemoval(BaseTestCase):
    def test_class_def__(self):
        self.files = {
            "foo.py": """
                class MyTest:
                    pass
                """
        }

        main(["foo.py", "--no-color", "--fix"])

        self.assertFiles({})

    def test_class_def_and_method_def(self):
        self.files = {
            "foo.py": """
                class MyTest:
                    def some_method(self):
                        pass
                """
        }

        main(["foo.py", "--no-color", "--fix"])

        self.assertFiles({})

    def test_class_def(self):
        self.files = {
            "foo.py": """
                class MyTest:
                    pass
                """,
            "bar.py": """
                class MyTest:
                    pass
                """,
        }

        unused_names = main(["foo.py", "--no-color", "--fix"])
        self.assertEqual(
            unused_names,
            (
                "bar.py:1:0: DC003 Class `MyTest` is never used\n"
                "foo.py:1:0: DC003 Class `MyTest` is never used\n\n"
                "Removed 2 unused code items!"
            ),
        )

        self.assertFiles({})

    @skip
    def test_definition_imported_from_other_file(self):
        # TODO: this use case has to be solved by using scopes

        self.files = {
            "foo.py": """
                class MyTest:
                    pass
                """,
            "bar.py": """
                class MyTest:
                    pass
                """,
            "spam.py": """
                from foo import MyTest

                instance = MyTest()
                print(instance)
                """,
        }

        unused_names = main(["foo.py", "--no-color", "--fix"])
        self.assertEqual(
            unused_names,
            ("bar.py:1:0: DC003 Class `MyTest` is never used\n\n" "Removed 2 unused code items!"),
        )

        self.assertFiles({})

    @skip
    def test_methods_with_the_same_name(self):
        # TODO: this use case has to be solved by using scopes

        self.files = {
            "foo.py": """
                class Bar:
                    def foo(self):
                        pass

                class Spam:
                    def foo(self):
                        pass

                bar = Bar()
                spam = Spam()
                print(bar, spam)
                print(bar.foo())
                """
        }

        unused_names = main(["foo.py", "--no-color", "--fix"])
        self.assertEqual(
            unused_names,
            ("foo.py:2:4: DC004 Method `foo` is never used\n\n" "Removed 1 unused code item!"),
        )

        self.assertFiles({})
