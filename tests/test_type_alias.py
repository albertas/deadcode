import sys
from unittest import skipUnless

from deadcode.cli import main
from deadcode.utils.base_test_case import BaseTestCase


@skipUnless(sys.version_info >= (3, 12), 'type alias syntax requires 3.12+')
class TypeAliasTests(BaseTestCase):
    def test_unused_type_alias_is_reported(self):
        self.files = {
            'foo.py': """
                type Number = int
                """
        }
        unused_names = main(['foo.py', '--no-color'])
        # CONFIRM exact line:col by running once on 3.12+; col 0 is best-effort.
        self.assertEqual(unused_names, 'foo.py:1:0: DC01 Variable `Number` is never used')

    def test_used_type_alias_is_not_reported(self):
        self.files = {
            'foo.py': """
                type Number = int

                def double(value: Number) -> Number:
                    return value * 2

                print(double(2))
                """
        }
        unused_names = main(['foo.py', '--no-color'])
        assert unused_names is None

    def test_fix_removes_unused_type_alias(self):
        self.files = {
            'foo.py': """
                type Number = int
                """
        }
        main(['foo.py', '--no-color', '--fix'])
        self.assertFiles({})
