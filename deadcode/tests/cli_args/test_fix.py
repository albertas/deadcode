from unittest import skip

from deadcode.cli import main
from deadcode.tests.base import BaseTestCase


class TestFixCliOption(BaseTestCase):
    def test_unused_class_was_removed(self):
        self.files = {
            "ignore_names_by_pattern.py": """
                class UnusedClass:
                    pass
                """
        }

        unused_names = main(["ignore_names_by_pattern.py", "--no-color", "--fix"])
        self.assertEqual(
            unused_names,
            (
                "ignore_names_by_pattern.py:1:0: DC100 Global UnusedClass is never used\n\n"
                "Removed \x1b[1m1\x1b[0m unused code item!"
            ),
        )

        self.assertFiles({"ignore_names_by_pattern.py": """"""})

    def test_function_removal(self):
        self.files = {
            "ignore_names_by_pattern.py": """
                def foo(bar: str = "Bar") -> str:
                    return 1 ** 2
                """
        }

        unused_names = main(["ignore_names_by_pattern.py", "--no-color", "--fix"])
        self.assertEqual(
            unused_names,
            (
                "ignore_names_by_pattern.py:1:0: DC100 Global foo is never used\n\n"
                "Removed \x1b[1m1\x1b[0m unused code item!"
            ),
        )

        self.assertFiles({"ignore_names_by_pattern.py": """"""})

    # TODO: treat variables unused if they are referenced only by other unused code.

    def test_function_removal_in_the_middle(self):
        self.files = {
            "ignore_names_by_pattern.py": """
                used_variable = "one"

                def foo(bar: str = "Bar") -> str:
                    return 1 ** 2

                spam = "Spam"
                print(spam, used_variable)
                """
        }

        unused_names = main(["ignore_names_by_pattern.py", "--no-color", "--fix"])
        self.assertEqual(
            unused_names,
            (
                "ignore_names_by_pattern.py:3:0: DC100 Global foo is never used\n\n"
                "Removed \x1b[1m1\x1b[0m unused code item!"
            ),
        )

        self.assertFiles(
            {
                "ignore_names_by_pattern.py": """
                used_variable = "one"

                spam = "Spam"
                print(spam, used_variable)
                """
            }
        )

    def test_function_removal_of_several_items(self):
        self.files = {
            "ignore_names_by_pattern.py": """
                used_variable = "one"

                unused_variable = ""

                def unused_function(bar: str = "Bar") -> str:
                    return 1 ** 2

                spam = "Spam"
                print(spam, used_variable)
                """
        }

        unused_names = main(["ignore_names_by_pattern.py", "--no-color", "--fix"])
        self.assertEqual(
            unused_names,
            (
                "ignore_names_by_pattern.py:3:0: DC100 Global unused_variable is never used\n"
                "ignore_names_by_pattern.py:5:0: DC100 Global unused_function is never used\n\n"
                "Removed \x1b[1m2\x1b[0m unused code items!"
            ),
        )

        self.assertFiles(
            {
                "ignore_names_by_pattern.py": """
                used_variable = "one"

                spam = "Spam"
                print(spam, used_variable)
                """
            }
        )

    def test_empty_lines_are_removed_properly_indented(self):
        self.files = {
            "foo.py": """
                    name = "World"

                    unused_variable = "This variable is unused"


                    def say_hello_world():
                        print(f"Hello {name}")


                    def unused_function():
                        pass


                    say_hello_world()


                    class Example:
                        def unused_method(self):
                            pass

                        def foo(self):
                            another_unused_variable = "Hello world"

                            with open("example.txt") as unused_file:
                                print("File was openned")


                    class UnusedClass:
                        def unused_method(self):
                            pass


                    instance = Example()
                    print(instance.foo())
                """
        }

        main(["ignore_names_by_pattern.py", "--no-color", "--fix"])

        self.assertFiles(
            {
                "foo.py": """
                    name = "World"

                    def say_hello_world():
                        print(f"Hello {name}")


                    say_hello_world()


                    class Example:
                        def foo(self):
                            with open("example.txt"):
                                print("File was openned")


                    instance = Example()
                    print(instance.foo())
                """
            }
        )

    def test_empty_lines_are_removed_properly(self):
        self.files = {
            "foo.py": """
                NAME = "World"

                UNUSED_VARIABLE = "This variable is unused"


                def say_hello_world():
                    print(f"Hello {NAME}")


                def unused_function():
                    pass


                say_hello_world()


                class Example:
                    def foo(self):
                        pass


                class UnusedClass:
                    def unused_method(self):
                        pass


                instance = Example()
                print(instance.foo())
                """
        }

        main(["ignore_names_by_pattern.py", "--no-color", "--fix"])

        self.assertFiles(
            {
                "foo.py": """
                    NAME = "World"

                    def say_hello_world():
                        print(f"Hello {NAME}")


                    say_hello_world()


                    class Example:
                        def foo(self):
                            pass


                    instance = Example()
                    print(instance.foo())
                """
            }
        )


class TestAddPassForEmptyBlock(BaseTestCase):
    def test_empty_class_block(self):
        self.files = {
            "foo.py": """
            class Example:
                def unused_method(self):
                    print("Unused method")

            example = Example()
            print(example)
            """
        }

        main([".", "--fix"])

        self.assertFiles(
            {
                "foo.py": """
            class Example:
                pass

            example = Example()
            print(example)
            """
            }
        )

    def test_empty_function_block(self):
        self.files = {
            "foo.py": """
            def foo():
                bar = 1

            foo()
            """
        }

        main([".", "--fix"])

        self.assertFiles(
            {
                "foo.py": """
            def foo():
                pass

            foo()
            """
            }
        )

    def test_empty_if_main_block(self):
        self.files = {
            "foo.py": """
            import sys

            if sys.argv[1:]:
                unused = 1
            """
        }

        main([".", "--fix"])

        # TODO: assertion still does not work, why there is a difference in the last line?
        self.assertFiles(
            {
                "foo.py": """
            import sys

            if sys.argv[1:]:
                pass
            """
            }
        )

    def test_empty_if_else_block(self):
        self.files = {
            "foo.py": """
            if spam:
                bar = 1
                print(bar)
            else:
                unused = 1
            """
        }

        main([".", "--fix"])

        self.assertFiles(
            {
                "foo.py": """
            if spam:
                bar = 1
                print(bar)
            else:
                pass
            """
            }
        )

    @skip
    def test_empty_if_statement_else_block(self):
        self.files = {
            "foo.py": """
            if spam:
                bar = 1
                print(bar)
            else:
                pass
            """
        }

        main([".", "--fix"])

        self.assertFiles(
            {
                "foo.py": """
            if spam:
                bar = 1
                print(bar)
            """
            }
        )

    @skip
    def test_if_is_not_fixed_correctly_when_branch_is_unreachable(self):
        self.files = {
            "foo.py": """
            if False:
                bar = 1
                print(bar)
            else:
                unused = 1
            """
        }

        main([".", "--fix"])

        self.assertFiles(
            {
                "foo.py": """
            if True:
                pass
            """
            }
        )

    def test_empty_with_block(self):
        self.files = {
            "foo.py": """
            with open("tmp.txt") as f:
                unused = 1
            """
        }

        main([".", "--fix"])

        self.assertFiles(
            {
                "foo.py": """
            with open("tmp.txt"):
                pass
            """
            }
        )

    def test_empty_block_is_at_the_end_of_file(self):
        pass  # tested by test_empty_with_block

    def test_some_code_follows_empty_block(self):
        pass  # tested by test_empty_class_block


class TestKeepCorrectNumberOfEmptyLinesAfterRemovalOfCodeBlock(BaseTestCase):
    def test_space_is_kept_after_whole_class_block_removal(self):
        self.files = {
            "foo.py": """
            class Example:
                def unused_method(self):
                    print("Unused method")

            example = Example()
            print(example)
            """
        }

        main([".", "--fix"])

        self.assertFiles(
            {
                "foo.py": """
            class Example:
                pass

            example = Example()
            print(example)
            """
            }
        )

    def test_two_spaces_are_kept_after_whole_class_block_removal(self):
        self.files = {
            "foo.py": """
            class Example:
                def unused_method(self):
                    print("Unused method")


            example = Example()
            print(example)
            """
        }

        main([".", "--fix"])

        self.assertFiles(
            {
                "foo.py": """
            class Example:
                pass


            example = Example()
            print(example)
            """
            }
        )

    def test_two_spaces_are_kept_after_one_method_removal(self):
        self.files = {
            "foo.py": """
            class Example:
                def unused_method(self):
                    print("Unused method")

                def used_method(self):
                    print("Used method")


            example = Example()
            print(example.used_method())
            """
        }

        main([".", "--fix"])

        self.assertFiles(
            {
                "foo.py": """
            class Example:
                def used_method(self):
                    print("Used method")


            example = Example()
            print(example.used_method())
            """
            }
        )

    def test_assignment(self):
        self.files = {
            "foo.py": """
            bar = 1
            """
        }

        main([".", "--fix"])

        self.assertFiles({"foo.py": """"""})
