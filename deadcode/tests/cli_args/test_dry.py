from deadcode.cli import main
from deadcode.tests.base import BaseTestCase
from deadcode.utils.fix_indent import fix_indent


class TestDryCliOption(BaseTestCase):
    def test_unused_class_was_reported_to_be_removed(self):
        self.files = {
            "foo.py": """
                class UnusedClass:
                    pass

                print("Dont change this file")"""
        }

        unused_names = main("foo.py --no-color --fix --dry".split())
        self.assertEqual(
            unused_names,
            (
                fix_indent(
                    """\
                foo.py:1:0: DC03 Class `UnusedClass` is never used

                --- foo.py
                +++ foo.py
                @@ -1,4 +1 @@
                -class UnusedClass:
                -    pass
                -
                 print("Dont change this file")
                """
                )
            ),
        )

        self.assertFiles(
            {
                "foo.py": """
                    class UnusedClass:
                        pass

                    print("Dont change this file")"""
            }
        )

    def test_file_is_not_modified_if_fix_option_is_used_with_dry(self):
        self.files = {
            "foo.py": """
                class UnusedClass:
                    pass

                print("Dont change this file")"""
        }

        unused_names = main(["ignore_names_by_pattern.py", "--no-color", "--fix", "--dry"])
        self.assertEqual(
            unused_names,
            (
                fix_indent(
                    """\
                foo.py:1:0: DC03 Class `UnusedClass` is never used

                --- foo.py
                +++ foo.py
                @@ -1,4 +1 @@
                -class UnusedClass:
                -    pass
                -
                 print("Dont change this file")
                """
                )
            ),
        )

        self.assertFiles(
            {
                "foo.py": """
                    class UnusedClass:
                        pass

                    print("Dont change this file")"""
            }
        )

    def test_all_files_are_reported_if_no_filenames_are_provided_for_dry_option(self):
        self.files = {
            "foo.py": """
                class UnusedClass:
                    pass

                print("Dont change this file")""",
            "bar.py": """
                def unused_function():
                    pass

                print("Dont change this file")""",
        }

        unused_names = main(["ignore_names_by_pattern.py", "--no-color", "--dry"])
        self.assertEqual(
            unused_names,
            fix_indent(
                """\
                bar.py:1:0: DC02 Function `unused_function` is never used
                foo.py:1:0: DC03 Class `UnusedClass` is never used

                --- bar.py
                +++ bar.py
                @@ -1,4 +1 @@
                -def unused_function():
                -    pass
                -
                 print("Dont change this file")

                --- foo.py
                +++ foo.py
                @@ -1,4 +1 @@
                -class UnusedClass:
                -    pass
                -
                 print("Dont change this file")
            """
            ),
        )

        self.assertFiles(
            {
                "foo.py": """
                class UnusedClass:
                    pass

                print("Dont change this file")""",
                "bar.py": """
                def unused_function():
                    pass

                print("Dont change this file")""",
            }
        )

    def test_only_provided_filenames_to_dry_option_are_reported(self):
        self.files = {
            "foo.py": """
                class UnusedClass:
                    pass

                print("Dont change this file")""",
            "bar.py": """
                def unused_function():
                    pass

                print("Dont change this file")""",
        }

        unused_names = main(["ignore_names_by_pattern.py", "--no-color", "--dry", "foo.py"])
        self.assertEqual(
            unused_names,
            fix_indent(
                """\
                bar.py:1:0: DC02 Function `unused_function` is never used
                foo.py:1:0: DC03 Class `UnusedClass` is never used

                --- foo.py
                +++ foo.py
                @@ -1,4 +1 @@
                -class UnusedClass:
                -    pass
                -
                 print("Dont change this file")
            """
            ),
        )

        self.assertFiles(
            {
                "foo.py": """
                class UnusedClass:
                    pass

                print("Dont change this file")""",
                "bar.py": """
                def unused_function():
                    pass

                print("Dont change this file")""",
            }
        )

    def test_no_diff_is_shown_if_dry_option_filenames_are_incorrect(self):
        self.files = {
            "foo.py": """
                class UnusedClass:
                    pass

                print("Dont change this file")"""
        }

        unused_names = main("foo.py --no-color --fix --dry fooo.py".split())
        self.assertEqual(
            unused_names,
            "foo.py:1:0: DC03 Class `UnusedClass` is never used",
        )

        self.assertFiles(
            {
                "foo.py": """
                    class UnusedClass:
                        pass

                    print("Dont change this file")"""
            }
        )

    def test_pattern_usage_for_filenames_provided_to_dry_option(self):
        self.files = {
            "foo.py": """
                class UnusedClass:
                    pass

                print("Dont change this file")"""
        }

        unused_names = main(["ignore_names_by_pattern.py", "--no-color", "--fix", "--dry", "f*.py"])
        self.assertEqual(
            unused_names,
            (
                fix_indent(
                    """\
                foo.py:1:0: DC03 Class `UnusedClass` is never used

                --- foo.py
                +++ foo.py
                @@ -1,4 +1 @@
                -class UnusedClass:
                -    pass
                -
                 print("Dont change this file")
                """
                )
            ),
        )

        self.assertFiles(
            {
                "foo.py": """
                    class UnusedClass:
                        pass

                    print("Dont change this file")"""
            }
        )

    def test_coloring_of_a_diff(self):
        self.files = {
            "foo.py": """
                class UnusedClass:
                    pass

                print("Dont change this file")""",
            "bar.py": """
                def unused_function():
                    pass

                with open("tmp.txt", "r") as unused_var:
                    pass

                print("Dont change this file")""",
        }

        unused_names = main(["ignore_names_by_pattern.py", "--dry"])
        self.assertEqual(
            unused_names,
            fix_indent(
                """\
                bar.py:1:0: \x1b[91mDC02\x1b[0m Function `\x1b[1munused_function\x1b[0m` is never used
                bar.py:4:29: \x1b[91mDC01\x1b[0m Variable `\x1b[1munused_var\x1b[0m` is never used
                foo.py:1:0: \x1b[91mDC03\x1b[0m Class `\x1b[1mUnusedClass\x1b[0m` is never used

                \x1b[31m--- bar.py\x1b[0m
                \x1b[32m+++ bar.py\x1b[0m
                @@ -1,7 +1,4 @@
                \x1b[31m-def unused_function():\x1b[0m
                \x1b[31m-    pass\x1b[0m
                \x1b[31m-\x1b[0m
                \x1b[31m-with open("tmp.txt", "r") as unused_var:\x1b[0m
                \x1b[32m+with open("tmp.txt", "r"):\x1b[0m
                     pass
                 
                 print("Dont change this file")

                \x1b[31m--- foo.py\x1b[0m
                \x1b[32m+++ foo.py\x1b[0m
                @@ -1,4 +1 @@
                \x1b[31m-class UnusedClass:\x1b[0m
                \x1b[31m-    pass\x1b[0m
                \x1b[31m-\x1b[0m
                 print("Dont change this file")
                """
            ),
        )

        self.assertFiles(
            {
                "foo.py": """
                class UnusedClass:
                    pass

                print("Dont change this file")""",
                "bar.py": """
                def unused_function():
                    pass

                with open("tmp.txt", "r") as unused_var:
                    pass

                print("Dont change this file")""",
            }
        )
