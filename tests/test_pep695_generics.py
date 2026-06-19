import sys
from unittest import skipUnless

from deadcode.cli import main
from deadcode.utils.base_test_case import BaseTestCase


@skipUnless(sys.version_info >= (3, 12), 'PEP 695 generics require 3.12+')
class Pep695GenericsTests(BaseTestCase):
    def test_type_param_is_not_reported_as_unused(self):
        # Guard against the `T` type parameter being flagged dead while used in
        # the signature/body. The whole function IS used.
        self.files = {
            'foo.py': """
                def first[T](items: list[T]) -> T:
                    return items[0]

                print(first([1, 2, 3]))
                """
        }
        unused_names = main(['foo.py', '--no-color'])
        assert unused_names is None

    def test_unused_generic_function_is_reported(self):
        self.files = {
            'foo.py': """
                def first[T](items: list[T]) -> T:
                    return items[0]
                """
        }
        unused_names = main(['foo.py', '--no-color'])
        # CONFIRM exact line:col by running once on 3.12+; expected:
        self.assertEqual(unused_names, 'foo.py:1:0: DC02 Function `first` is never used')

    def test_fix_removes_unused_generic_class(self):
        self.files = {
            'foo.py': """
                class Box[T]:
                    pass
                """
        }
        main(['foo.py', '--no-color', '--fix'])
        self.assertFiles({})
