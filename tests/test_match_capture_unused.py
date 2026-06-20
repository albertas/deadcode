import sys
from unittest import expectedFailure, skipUnless

from deadcode.cli import main
from deadcode.utils.base_test_case import BaseTestCase


@skipUnless(sys.version_info >= (3, 10), 'match statements require 3.10+')
class MatchCaptureUnusedTests(BaseTestCase):
    @expectedFailure
    def test_unused_match_capture_is_reported(self):
        # Capture `a` in `case [a]` is bound but never read. Captures bind via
        # str attrs (MatchAs/MatchStar/MatchMapping), not Name nodes, and there
        # is no visit_MatchAs, so they are never tracked. Correct: `a` IS
        # reported. Currently main() returns None.
        self.files = {
            'foo.py': """
                def handle(command):
                    match command:
                        case [a]:
                            return 0
                        case _:
                            return 1


                handle([1])
                """
        }
        unused_names = main(['foo.py', '--no-color'])
        # CONFIRM line:col when the fix lands.
        self.assertEqual(unused_names, 'foo.py:3:14: DC01 Variable `a` is never used')

    def test_unused_local_in_match_function_is_reported(self):
        # Control: an ordinary unused local in the same function IS reported,
        # proving the visitor ran inside the match construct.
        self.files = {
            'foo.py': """
                def handle(command):
                    leftover = 5
                    match command:
                        case [a]:
                            return 0
                        case _:
                            return 1


                handle([1])
                """
        }
        unused_names = main(['foo.py', '--no-color'])
        self.assertEqual(unused_names, 'foo.py:2:4: DC01 Variable `leftover` is never used')
