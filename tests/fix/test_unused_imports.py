"""
Test unused import detection and removal.
"""

from deadcode.cli import main
from deadcode.utils.base_test_case import BaseTestCase
from deadcode.utils.fix_indent import fix_indent


class TestAssignmentExpressionRemoval(BaseTestCase):
    def test_variable(self):
        self.files = {
            'file2.py': b"""
                from file1 import (
                    foo,
                    bar,
                    xyz
                )

                from file1 import foo

                def fn():
                    pass

                fn()
                """
        }

        unused_names = main('file2.py --no-color --fix -v'.split())

        self.assertEqual(
            unused_names,
            fix_indent("""\
                file2.py:2:4: DC07 Import `foo` is never used
                file2.py:3:4: DC07 Import `bar` is never used
                file2.py:4:4: DC07 Import `xyz` is never used
                file2.py:7:18: DC07 Import `foo` is never used

                Removed 4 unused code items!"""),
        )

        self.assertFiles(
            {
                'file2.py': b"""
                    def fn():
                        pass

                    fn()
                    """
            }
        )
        self.assertIn(b'fn()', self.updated_files['file2.py'])

    def test_unused_single_line_from_import(self):
        self.files = {
            'file2.py': b"""
                from file1 import foo

                def fn():
                    pass

                fn()
                """
        }

        unused_names = main('file2.py --no-color --fix'.split())

        self.assertIn('DC07 Import `foo` is never used', unused_names or '')

        self.assertFiles(
            {
                'file2.py': b"""
                    def fn():
                        pass

                    fn()
                    """
            }
        )

    def test_unused_import_of_several_names(self):
        self.files = {
            'file2.py': b"""
                import a, b

                def fn():
                    pass

                fn()
                """
        }

        unused_names = main('file2.py --no-color --fix'.split())

        self.assertIn('DC07 Import `a` is never used', unused_names or '')
        self.assertIn('DC07 Import `b` is never used', unused_names or '')

        self.assertFiles(
            {
                'file2.py': b"""
                    def fn():
                        pass

                    fn()
                    """
            }
        )

    def test_unused_single_line_parenthesized_import(self):
        self.files = {
            'file2.py': b"""
                from file1 import (foo, bar)

                def fn():
                    pass

                fn()
                """
        }

        unused_names = main('file2.py --no-color --fix'.split())

        self.assertIn('DC07 Import `foo` is never used', unused_names or '')
        self.assertIn('DC07 Import `bar` is never used', unused_names or '')

        self.assertFiles(
            {
                'file2.py': b"""
                    def fn():
                        pass

                    fn()
                    """
            }
        )

    def test_wildcard_import_is_kept(self):
        self.files = {
            'file2.py': b"""
                from file1 import *
                from file1 import foo

                def fn():
                    pass

                fn()
                """
        }

        unused_names = main('file2.py --no-color --fix'.split())

        self.assertIn('DC07 Import `foo` is never used', unused_names or '')

        self.assertFiles(
            {
                'file2.py': b"""
                    from file1 import *
                    def fn():
                        pass

                    fn()
                    """
            }
        )
        self.assertIn(b'from file1 import *', self.updated_files['file2.py'])

    def test_partial_same_line_import_removal(self):
        self.files = {
            'file2.py': b"""
                from mymodule.test import used_func, unused_func

                used_func()
                """
        }

        unused_names = main('file2.py --no-color --fix'.split())

        self.assertIn('DC07 Import `unused_func` is never used', unused_names or '')
        self.assertNotIn('DC07 Import `used_func` is never used', unused_names or '')

        self.assertFiles(
            {
                'file2.py': b"""
                    from mymodule.test import used_func

                    used_func()
                    """
            }
        )

    def test_partial_import_removal_of_unused_names_between_a_used_name(self):
        self.files = {
            'file2.py': b"""
                from file1 import a, b, c

                b()
                """
        }

        unused_names = main('file2.py --no-color --fix'.split())

        self.assertIn('DC07 Import `a` is never used', unused_names or '')
        self.assertIn('DC07 Import `c` is never used', unused_names or '')
        self.assertNotIn('DC07 Import `b` is never used', unused_names or '')

        self.assertFiles(
            {
                'file2.py': b"""
                    from file1 import b

                    b()
                    """
            }
        )

    def test_partial_multi_line_parenthesized_import_removal(self):
        self.files = {
            'file2.py': b"""
                from file1 import (
                    used_func,
                    unused_func,
                    other_unused_func,
                )

                used_func()
                """
        }

        unused_names = main('file2.py --no-color --fix'.split())

        self.assertIn('DC07 Import `unused_func` is never used', unused_names or '')
        self.assertIn('DC07 Import `other_unused_func` is never used', unused_names or '')
        self.assertNotIn('DC07 Import `used_func` is never used', unused_names or '')

        self.assertFiles(
            {
                'file2.py': b"""
                    from file1 import (
                        used_func,
                    )

                    used_func()
                    """
            }
        )

    def test_partial_as_alias_import_removal(self):
        self.files = {
            'file2.py': b"""
                from file1 import foo as bar, used_func

                used_func()
                """
        }

        unused_names = main('file2.py --no-color --fix'.split())

        self.assertIn('DC07 Import `bar` is never used', unused_names or '')
        self.assertNotIn('DC07 Import `used_func` is never used', unused_names or '')

        self.assertFiles(
            {
                'file2.py': b"""
                    from file1 import used_func

                    used_func()
                    """
            }
        )

    def test_partial_import_of_several_names(self):
        self.files = {
            'file2.py': b"""
                import a, b

                a()
                """
        }

        unused_names = main('file2.py --no-color --fix'.split())

        self.assertIn('DC07 Import `b` is never used', unused_names or '')
        self.assertNotIn('DC07 Import `a` is never used', unused_names or '')

        self.assertFiles(
            {
                'file2.py': b"""
                    import a

                    a()
                    """
            }
        )

    def test_duplicate_import_with_one_protected_occurrence(self):
        self.files = {
            'file2.py': b"""
                from file1 import foo  # noqa: DC07
                from file1 import foo

                fn()
                """
        }

        unused_names = main('file2.py --no-color --fix'.split())

        self.assertIn('DC07 Import `foo` is never used', unused_names or '')

        self.assertFiles(
            {
                'file2.py': b"""
                    from file1 import foo  # noqa: DC07
                    fn()
                    """
            }
        )

    def test_partial_import_with_noqa_protected_alias(self):
        self.files = {
            'file2.py': b"""
                from file1 import (
                    used_func,
                    unused_func,
                    protected_func,  # noqa: DC07
                )

                used_func()
                """
        }

        unused_names = main('file2.py --no-color --fix'.split())

        self.assertIn('DC07 Import `unused_func` is never used', unused_names or '')
        self.assertNotIn('protected_func', unused_names or '')

        self.assertFiles(
            {
                'file2.py': b"""
                    from file1 import (
                        used_func,
                        protected_func,  # noqa: DC07
                    )

                    used_func()
                    """
            }
        )
        self.assertIn(b'protected_func', self.updated_files['file2.py'])

    def test_unused_multi_line_parenthesized_import_block(self):
        self.files = {
            'file2.py': b"""
                def fn():
                    pass

                from file1 import (
                    foo,
                    bar,
                )

                fn()
                """
        }

        unused_names = main('file2.py --no-color --fix'.split())

        self.assertIn('DC07 Import `foo` is never used', unused_names or '')
        self.assertIn('DC07 Import `bar` is never used', unused_names or '')

        self.assertFiles(
            {
                'file2.py': b"""
                    def fn():
                        pass

                    fn()
                    """
            }
        )
