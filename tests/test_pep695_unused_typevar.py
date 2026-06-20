import sys
from unittest import expectedFailure, skipUnless

from deadcode.cli import main
from deadcode.utils.base_test_case import BaseTestCase


@skipUnless(sys.version_info >= (3, 12), 'PEP 695 generics require 3.12+')
class Pep695UnusedTypeVarTests(BaseTestCase):
    @expectedFailure
    def test_unused_generic_type_param_is_reported(self):
        # `T` is declared but never referenced in the signature or body. It is a
        # TypeVar.name str, not a Name node, and there is no visit_TypeVar, so
        # it is untracked. Correct: `T` IS reported. Predicted current: None.
        self.files = {
            'foo.py': """
                def f[T](x: int) -> int:
                    return x


                f(1)
                """
        }
        unused_names = main(['foo.py', '--no-color'])
        # CONFIRM exact DC code + line:col on a 3.12+ run when the fix lands.
        self.assertEqual(unused_names, 'foo.py:1:6: DC01 Variable `T` is never used')

    def test_used_generic_type_param_is_not_reported(self):
        # Control: `T` is referenced in the signature -> not reported.
        self.files = {
            'foo.py': """
                def g[T](x: T) -> T:
                    return x


                g(1)
                """
        }
        unused_names = main(['foo.py', '--no-color'])
        assert unused_names is None
