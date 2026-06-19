from deadcode.cli import main
from deadcode.utils.base_test_case import BaseTestCase


class WalrusTests(BaseTestCase):
    def test_unused_walrus_target_is_reported(self):
        # `total` is bound by walrus but never read afterwards.
        # `run` is called so only `total` surfaces as unused.
        self.files = {
            'foo.py': """
                def run(values):
                    if (total := sum(values)):
                        return len(values)
                    return 0

                run([])
                """
        }
        unused_names = main(['foo.py', '--no-color'])
        # Column confirmed from a real run: col 8 is the position of `total` inside `(total := ...)`.
        self.assertEqual(unused_names, 'foo.py:2:8: DC01 Variable `total` is never used')

    def test_used_walrus_target_is_not_reported(self):
        # `total` is bound by walrus and read in the body -> not reported.
        self.files = {
            'foo.py': """
                def run(values):
                    if (total := sum(values)):
                        return total
                    return 0

                run([])
                """
        }
        unused_names = main(['foo.py', '--no-color'])
        assert unused_names is None
