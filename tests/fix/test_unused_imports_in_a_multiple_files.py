"""
Test unused import detection when code items are imported from one file to another.

# Just write nice tests for imports.
    # Import to another file.
    # Import with an alias in another file.
    # Import variable, function, class.
    # Relative imports.
    # Make tests for local import.

Tests should be based on: test_method_at_the_end_of_file test.
"""

from unittest import skip

from deadcode.cli import main
from deadcode.utils.base_test_case import BaseTestCase
from deadcode.utils.fix_indent import fix_indent


class TestCodeItemUsageWhenImportingFromDifferentFiles(BaseTestCase):
    def test_variable(self):
        # This test unexpectedly works.

        self.files = {
            'foo.py': """
                def bar():
                    return 123
                """,
            'spam.py': """
                from foo import bar
                print(bar())
                """
        }

        unused_names = main('file.py --no-color --fix -v'.split())
        self.assertEqual(
            unused_names,
            None
        )
        self.assertFiles(
            {
                'foo.py': """
                    def bar():
                        return 123
                    """,
                'spam.py': """
                    from foo import bar
                    print(bar())
                    """
            }
        )

    def test_method_at_the_end_of_file(self):
        self.files = {
            'bar.py': """
                class MyTest:
                    def some_method(self):
                        pass
                """,
            'foo.py': """
                from foo import MyTest

                instance = MyTest()
                print(instance)
                """,
        }

        main(['foo.py', '--no-color', '--fix'])

        # TODO: whole MyTest was removed, probably the reason is that not all
        # files were analysed before applying fixing.
        #
        # Lets fix: fix part applying only after all files were visited.

        self.assertFiles(
            {
                'bar.py': """
            class MyTest:
                pass
            """,
                'foo.py': """
                from foo import MyTest

                instance = MyTest()
                print(instance)
            """,
            }
        )

    def test_method_at_the_end_of_file_and_class_does_not_have_overlapping_parts_with_its_method(self):
        self.files = {
            'bar.py': """
                class MyTest:
                    def some_method(self):
                        print('remove me')
                """,
            'foo.py': """
                from foo import MyTest

                instance = MyTest()
                print(instance)
                """,
        }

        main(['foo.py', '--no-color', '--fix'])

        # TODO: whole MyTest was removed, probably the reason is that not all
        # files were analysed before applying fixing.
        #
        # Lets fix: fix part applying only after all files were visited.


        # TODO: detect, why pass was not preserved?
        # Method was removed, but its pass statement was not preserved.
        # Why it was not preserved?

        self.assertFiles(
            {
                'bar.py': """
            class MyTest:
                pass
            """,
                'foo.py': """
                from foo import MyTest

                instance = MyTest()
                print(instance)
            """,
            }
        )

        # self.assertFiles(
        #     {
        #         'bar.py': """
        #     class MyTest:
        #         pass
        #     """,
        #         'foo.py': """
        #         from foo import MyTest

        #         instance = MyTest()
        #         print(instance)
        #     """,
        #     }
        # )
