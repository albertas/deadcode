from deadcode.cli import main
from deadcode.tests.base import BaseTestCase


class TestScopeTracking(BaseTestCase):
    def test_class_should_be_in_scope(self):
        self.files = {
            "foo.py": """
                class Foo:
                    pass
                """
        }

        unused_names = main(["foo.py", "--no-color", "--fix"])
        self.assertEqual(
            unused_names,
            ("foo.py:1:0: DC003 Class `Foo` is never used\n\n" "Removed 1 unused code item!"),
        )

        self.assertFiles({})

    def test_class_and_its_method_should_be_in_scope(self):
        self.files = {
            "foo.py": """
                class Foo:
                    def bar(self):
                        variable = 123
                """
        }

        main(["foo.py", "--no-color", "--fix"])
        self.assertFiles({})

        # TODO: get nested scope for testing.

    def test_name_is_overriden(self):
        self.files = {
            "foo.py": """
                class Foo:
                    pass


                class Foo:
                    pass
                """
        }

        main(["foo.py", "--no-color", "--fix"])
        self.assertFiles({})

    def test_multi_parent_inheritance_should_be_tracked(self):
        self.files = {
            "foo.py": """
                class Foo:
                    pass


                class Bar(Foo):
                    pass


                class Spam(Bar):
                    pass
                """
        }

        result = main(["foo.py", "--no-color", "--fix", "--ignore-definitions-if-inherits-from=Foo"])
        self.assertFiles(
            {
                "foo.py": """
                class Foo:
                    pass


                class Bar(Foo):
                    pass


                class Spam(Bar):
                    pass
                """
            }
        )

        self.assertIsNone(result)
