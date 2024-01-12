from unittest import skip

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

    def test_take_parent_scopes_into_consideration_when_searching_for_definition(self):
        self.files = {
            "foo.py": """
                class Foo:
                    pass


                class Bar(Foo):
                    class Spam(Foo):
                        pass

                    class Eggs(Spam):
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
                    class Spam(Foo):
                        pass

                    class Eggs(Spam):
                        pass
                """
            }
        )

        self.assertIsNone(result)

    @skip("This feature is being implemented")
    def test_type_tracking_for_function_arguments(self):
        self.files = {
            "foo.py": """
                class Foo:
                    def bar(self):
                        pass

                def spam(eggs):
                    eggs.bar()

                foo = Foo()
                spam(foo)

                def bar():
                    pass
                """
        }

        result = main(["foo.py", "--no-color", "--fix"])

        # TODO: detect eggs type inside spam function and mark Foo.bar as used in CodeItem instance.
        # Usages should be marked directly on the CodeItem instances, not in a pool of names.

        self.assertFiles(
            {
                "foo.py": """
                class Foo:
                    def bar(self):
                        pass

                def spam(eggs):
                    eggs.bar()

                foo = Foo()
                spam(foo)
                """
            }
        )

        self.assertIsNone(result)

    @skip(">> Observed types in scope definition is still being implemented")
    def test_scope_update_for_method_call_expression(self):
        # >>> TODO: Mark types in scope usage correctly for method invocation
        self.files = {
            "foo.py": """
                Bar().spam()
                """
        }

        result = main(["foo.py", "--no-color", "--fix"])

        self.assertFiles({"foo.py": """"""})

        self.assertIsNone(result)
