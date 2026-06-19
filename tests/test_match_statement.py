from deadcode.cli import main
from deadcode.utils.base_test_case import BaseTestCase


class MatchStatementTests(BaseTestCase):
    def test_unused_var_in_match_subject_is_reported(self):
        # `unused_helper` is defined but never read; the `match` consumes `command`.
        # `handle` is called so only `unused_helper` surfaces as unused.
        self.files = {
            'foo.py': """
                unused_helper = 1

                def handle(command):
                    match command:
                        case "start":
                            return True
                        case _:
                            return False

                handle("stop")
                """
        }
        unused_names = main(['foo.py', '--no-color'])
        self.assertEqual(unused_names, 'foo.py:1:0: DC01 Variable `unused_helper` is never used')

    def test_name_bound_in_case_pattern_is_used(self):
        # `value` is bound by a class/keyword pattern and then read -> not reported.
        self.files = {
            'foo.py': """
                class Point:
                    __match_args__ = ()
                    x = 0

                def handle(command):
                    match command:
                        case Point(x=value):
                            return value
                        case _:
                            return None

                handle(Point())
                """
        }
        unused_names = main(['foo.py', '--no-color'])
        assert unused_names is None

    def test_capture_pattern_binding_is_used(self):
        # Sequence capture pattern binds `a`, `b`; both are read -> not reported.
        self.files = {
            'foo.py': """
                def handle(command):
                    match command:
                        case [a, b]:
                            return a + b
                        case _:
                            return 0

                handle([1, 2])
                """
        }
        unused_names = main(['foo.py', '--no-color'])
        assert unused_names is None
