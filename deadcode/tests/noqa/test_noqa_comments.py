from unittest import skip

from deadcode.cli import main
from deadcode.tests.base import BaseTestCase


class TestNoqaComments(BaseTestCase):
    def test_unused_class_is_unchanged_if_noqa_comment_is_provided(self):
        self.files = {
            "foo.py": """
                class MyTest:  # noqa: DC003
                    pass
                """
        }

        unused_names = main(["foo.py", "--no-color", "--fix"])

        self.assertFiles(
            {
                "foo.py": """
                class MyTest:  # noqa: DC003
                    pass
                """
            }
        )

        self.assertEqual(unused_names, None)

    def test_noqa_all(self):
        self.files = {
            "foo.py": """
                instance = "labas"  # noqa
                """
        }

        unused_names = main(["foo.py", "--no-color", "--fix"])

        self.assertFiles(
            {
                "foo.py": """
                instance = "labas"  # noqa
                """
            }
        )

        self.assertEqual(unused_names, None)

    def test_unused_variable(self):
        self.files = {
            "foo.py": """
                unused_variable = "Hello"  # noqa: DC001
                    pass
                """
        }

        unused_names = main(["foo.py", "--no-color", "--fix"])
        self.assertEqual(unused_names, None)

        self.assertFiles(
            {
                "foo.py": """
                unused_variable = "Hello"  # noqa: DC001
                    pass
                """
            }
        )

    def test_unused_variable_but_wrong_noqa_specified(self):
        self.files = {
            "foo.py": """
                unused_variable = "Hello"  # noqa: DC002
                """
        }

        unused_names = main(["foo.py", "--no-color", "--fix"])

        self.assertFiles({})
        self.assertEqual(
            unused_names,
            ("foo.py:1:0: DC001 Variable `unused_variable` is never used\n\n" "Removed 1 unused code item!"),
        )

    def test_unused_function(self):
        self.files = {
            "foo.py": """
                def unused_function():  # noqa: DC002
                    pass
                """
        }

        unused_names = main(["foo.py", "--no-color", "--fix"])
        self.assertEqual(unused_names, None)

        self.assertFiles(
            {
                "foo.py": """
                def unused_function():  # noqa: DC002
                    pass
                """
            }
        )

    def test_unused_method(self):
        self.files = {
            "foo.py": """
                class MyTest:
                    def unused_method(self):  # noqa: DC004
                        pass

                instance = MyTest()
                print(instance)
                """
        }

        unused_names = main(["foo.py", "--no-color", "--fix"])

        self.assertFiles(
            {
                "foo.py": """
                class MyTest:
                    def unused_method(self):  # noqa: DC004
                        pass

                instance = MyTest()
                print(instance)
                """
            }
        )

        self.assertEqual(unused_names, None)

    @skip
    def test_unused_attribute(self):
        # TODO: DC005 does not work.
        self.files = {
            "foo.py": """
                class MyTest:
                    unused_attribute = 123  # noqa: DC005

                instance = MyTest()
                print(instance)
                """
        }

        unused_names = main(["foo.py", "--no-color", "--fix"])

        self.assertFiles(
            {
                "foo.py": """
                class MyTest:
                    unused_attribute = 123  # noqa: DC005

                instance = MyTest()
                print(instance)
                """
            }
        )

        self.assertEqual(unused_names, None)

    @skip
    def test_unused_name(self):
        # TODO: DC006 does not work.
        self.files = {
            "foo.py": """
                class MyTest:
                    unused_attribute = 123  # noqa: DC006

                instance = MyTest()
                print(instance)
                """
        }

        unused_names = main(["foo.py", "--no-color", "--fix"])

        self.assertFiles(
            {
                "foo.py": """
                class MyTest:
                    unused_attribute = 123  # noqa: DC006

                instance = MyTest()
                print(instance)
                """
            }
        )

        self.assertEqual(unused_names, None)

    def test_unused_import(self):
        self.files = {
            "foo.py": """
                from typing import Optional  # noqa: DC007
                """
        }

        unused_names = main(["foo.py", "--no-color", "--fix"])

        self.assertFiles(
            {
                "foo.py": """
                from typing import Optional  # noqa: DC007
                """
            }
        )

        self.assertEqual(unused_names, None)

    @skip
    def test_unused_property(self):
        self.files = {
            "foo.py": """
                class Foo:
                    @property
                    def bar(self):  # noqa: DC008
                        return None
                """
        }

        unused_names = main(["foo.py", "--no-color", "--fix"])

        self.assertFiles(
            {
                "foo.py": """
                class Foo:
                    @property
                    def bar(self):  # noqa: DC008
                        return None
                """
            }
        )

        self.assertEqual(unused_names, None)

    @skip
    def test_unreachable_code(self):
        # TODO: identify all cases, when unreachable code is detected, and write unit tests

        self.files = {
            "foo.py": """
                if True:
                    pass
                else:  # noqa: DC009
                    print("Hello world")
                """
        }

        unused_names = main(["foo.py", "--no-color", "--fix"])

        self.assertFiles(
            {
                "foo.py": """
                if True:
                    pass
                else:  # noqa: DC009
                    print("Hello world")
                """
            }
        )

        self.assertEqual(unused_names, None)

    def test_empty_file(self):
        # TODO: this test passes only because comment is treated as non empty file content
        self.files = {
            "foo.py": """
                # noqa: DC011
                """
        }

        unused_names = main(["foo.py", "--no-color", "--fix"])

        self.assertFiles(
            {
                "foo.py": """
                # noqa: DC011
                """
            }
        )

        self.assertEqual(unused_names, None)

    def test_commented_out_code(self):
        # TODO: this test only passes because commented-out-code check is not yet implemented
        self.files = {
            "foo.py": """
                # print("Hello world")  # noqa: DC012
                """
        }

        unused_names = main(["foo.py", "--no-color", "--fix"])

        self.assertFiles(
            {
                "foo.py": """
                # print("Hello world")  # noqa: DC012
                """
            }
        )

        self.assertEqual(unused_names, None)

    @skip
    def test_ignore_expression(self):
        self.files = {
            "foo.py": """
                class Foo:  # noqa: DC013
                    this_attiribute_is_unused = True

                    def this_method_is_not_used_as_well(self):
                        pass
                """
        }

        unused_names = main(["foo.py", "--no-color", "--fix"])

        self.assertFiles(
            {
                "foo.py": """
                class Foo:  # noqa: DC013
                    this_attiribute_is_unused = True

                    def this_method_is_not_used_as_well(self):
                        pass
                """
            }
        )

        self.assertEqual(unused_names, None)
