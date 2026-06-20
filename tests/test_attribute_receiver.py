from unittest import expectedFailure

from deadcode.cli import main
from deadcode.utils.base_test_case import BaseTestCase


class AttributeReceiverTests(BaseTestCase):
    @expectedFailure
    def test_function_shadowed_by_same_named_attribute_is_reported(self):
        # `value` (a module function) is never called. But `obj.value` is a
        # bare-attr Load (visit_Attribute:348) that marks the name `value`
        # used, cross-contaminating the function. Correct: the function IS
        # reported. Currently main() returns None.
        self.files = {
            'foo.py': """
                def value():
                    return 1


                class C:
                    def go(self, obj):
                        return obj.value


                C().go(None)
                """
        }
        unused_names = main(['foo.py', '--no-color'])
        self.assertEqual(unused_names, 'foo.py:1:0: DC02 Function `value` is never used')

    def test_distinctly_named_unused_function_is_reported(self):
        # Control: a uniquely-named unused function IS reported.
        self.files = {
            'foo.py': """
                def distinctly_unused():
                    return 1


                class C:
                    def go(self, obj):
                        return obj.value


                C().go(None)
                """
        }
        unused_names = main(['foo.py', '--no-color'])
        self.assertEqual(unused_names, 'foo.py:1:0: DC02 Function `distinctly_unused` is never used')
