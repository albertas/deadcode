from deadcode.cli import main
from deadcode.utils.base_test_case import BaseTestCase


class UnusedParameterTests(BaseTestCase):
    def test_unused_parameter_is_not_reported(self):
        # `visit_arg` is commented out (find_unused_code_visitor.py:337), so
        # parameters are never registered as definitions. This pins current
        # behavior: only the unused local `x` is reported, never `unused_param`.
        self.files = {
            'foo.py': """
                def f(unused_param):
                    x = 1
                    return 0


                f(2)
                """
        }
        unused_names = main(['foo.py', '--no-color'])
        # Control is built in: the unused local `x` IS reported, proving the
        # visitor ran and the gap is parameter-specific.
        self.assertEqual(unused_names, 'foo.py:2:4: DC01 Variable `x` is never used')
