from unittest import expectedFailure

from deadcode.cli import main
from deadcode.utils.base_test_case import BaseTestCase


class ScopeBlindMatchingTests(BaseTestCase):
    @expectedFailure
    def test_unused_method_shadowed_by_unrelated_use_is_reported(self):
        # `B.run` is genuinely unused, but `A().run()` marks the bare name
        # `run` used, so the scope-blind flat match suppresses it. Correct
        # behavior: `B.run` IS reported. Currently main() returns None.
        self.files = {
            'foo.py': """
                class A:
                    def run(self):
                        return 1


                class B:
                    def run(self):
                        return 2


                A().run()
                B()
                """
        }
        unused_names = main(['foo.py', '--no-color'])
        # CONFIRM line:col when the fix lands; until then this assertion fails
        # (None != string) and @expectedFailure makes the test pass.
        self.assertEqual(unused_names, 'foo.py:7:4: DC04 Method `run` is never used')

    def test_distinctly_named_unused_method_is_reported(self):
        # Control: a uniquely-named unused method IS reported, proving the
        # visitor ran and the F1 gap is specific to name collisions.
        self.files = {
            'foo.py': """
                class A:
                    def run(self):
                        return 1


                class B:
                    def distinctly_unused(self):
                        return 2


                A().run()
                B()
                """
        }
        unused_names = main(['foo.py', '--no-color'])
        self.assertEqual(unused_names, 'foo.py:7:4: DC04 Method `distinctly_unused` is never used')
