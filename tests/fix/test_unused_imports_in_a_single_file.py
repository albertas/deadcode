"""
Test unused import detection and removal from a single file.
"""

from unittest import skip

from deadcode.cli import main
from deadcode.utils.base_test_case import BaseTestCase
from deadcode.utils.fix_indent import fix_indent


class TestAssignmentExpressionRemoval(BaseTestCase):
    def test_variable(self):
        self.files = {
            'file.py': """
                from file1 import (
                    foo,
                    bar,
                    xyz
                )

                from file2 import foo

                def fn():
                    pass

                fn()
                """
        }
        unused_names = main('file.py --no-color --fix -v'.split())
        self.assertEqual(
            unused_names,
            fix_indent("""\
                file.py:2:4: DC07 Import `foo` is never used
                file.py:3:4: DC07 Import `bar` is never used
                file.py:4:4: DC07 Import `xyz` is never used
                file.py:7:18: DC07 Import `foo` is never used

                Removed 4 unused code items!"""),
        )
        self.assertFiles(
            {
                'file.py': """
                    def fn():
                        pass

                    fn()
                    """
            }
        )

    def test_unused_import_removal(self):
        self.files = {
            'file.py': """
                import foo, bar, xyz

                def fn():
                    pass

                fn()
                """
        }

        unused_names = main('file.py --no-color --fix -v'.split())

        self.assertEqual(
            unused_names,
            fix_indent("""\
                file.py:1:12: DC07 Import `bar` is never used
                file.py:1:7: DC07 Import `foo` is never used
                file.py:1:17: DC07 Import `xyz` is never used

                Removed 3 unused code items!"""),
        )

        self.assertFiles(
            {
                'file.py': """
                    def fn():
                        pass

                    fn()
                    """
            }
        )

    def test_unused_import_from_removal(self):
        self.files = {
            'file.py': """
                from file1 import (
                    foo,
                    bar,
                    xyz
                )

                def fn():
                    pass

                fn()
                """
        }

        unused_names = main('file.py --no-color --fix -v'.split())

        self.assertEqual(
            unused_names,
            fix_indent("""\
                file.py:2:4: DC07 Import `foo` is never used
                file.py:3:4: DC07 Import `bar` is never used
                file.py:4:4: DC07 Import `xyz` is never used

                Removed 3 unused code items!"""),
        )

        self.assertFiles(
            {
                'file.py': """
                    def fn():
                        pass

                    fn()
                    """
            }
        )

    def test_remove_simple_import(self):
        self.files = {
            'file.py': """
                from file1 import foo, eggs, bar as spam

                def fn():
                    print(eggs)

                fn()
                """
        }

        unused_names = main('file.py --no-color --fix -v'.split())

        self.assertEqual(
            unused_names,
            fix_indent("""\
                file.py:1:18: DC07 Import `foo` is never used
                file.py:1:29: DC07 Import `spam` is never used

                Removed 2 unused code items!"""),
        )

        self.assertFiles(
            {
                'file.py': """
                    from file1 import eggs

                    def fn():
                        print(eggs)

                    fn()
                    """
            }
        )

    def test_spacing_between_removed_import_expressions(self):
        self.files = {
            'file.py': """
                import os
                from file1 import (
                    foo,
                    bar,
                    xyz
                )
                import another_unused
                import sys

                from file2 import third_unused

                def fn():
                    print(os.version)
                    print(sys.version)

                fn()
                """
        }
        unused_names = main('file.py --no-color --fix -v'.split())
        # self.assertEqual(
        #     unused_names,
        #     fix_indent("""\
        #         file.py:3:4: DC07 Import `foo` is never used
        #         file.py:4:4: DC07 Import `bar` is never used
        #         file.py:5:4: DC07 Import `xyz` is never used
        #         file.py:7:7: DC07 Import `another_unused` is never used
        #         file.py:10:18: DC07 Import `third_unused` is never used

        #         Removed 5 unused code items!""")
        # )
        self.assertFiles(
            {
                'file.py': """
                    import os
                    import sys

                    def fn():
                        print(os.version)
                        print(sys.version)

                    fn()
                    """
            }
        )

    def test_aliases_are_removed(self):
        self.files = {
            'file.py': """
                from spam import (
                    foo as foo_alias,
                    bar as bar_alias,
                    eggs as eggs_alias,
                )

                print(bar_alias)
                """
        }
        ## Are detected parts correct?:
        # [Part(line_start=1, line_end=3, col_start=17, col_end=4), Part(line_start=3, line_end=5, col_start=20, col_end=2)]
        # from spam import bar as bar_alias
        #
        # It seems that detected characters are correct.
        # Where is the issue? Lets try reproducing it at the writing method level.

        # print(bar_alias)

        unused_names = main('file.py --no-color --fix -v'.split())
        # self.assertEqual(
        #     unused_names,
        #     fix_indent("""\
        #         file.py:3:4: DC07 Import `foo_alias` is never used
        #         file.py:7:4: DC07 Import `eggs_alias` is never used

        #         Removed 2 unused code items!""")
        # )

        # This comparison ignores empty lines, why is it?
        # I want number of empty lines to be accurate here.

        self.assertFiles(
            {
                'file.py': """
                    from spam import bar as bar_alias

                    print(bar_alias)
                    """
            }
        )

        # # Actually expected result is:
        # self.assertFiles(
        #     {
        #         'file.py': """
        #             from spam import bar as bar_alias

        #             print(bar_alias)
        #             """
        #     }
        # )
