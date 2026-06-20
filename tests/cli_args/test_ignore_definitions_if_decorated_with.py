from deadcode.cli import main
from deadcode.utils.base_test_case import BaseTestCase


class TestIgnoreDefinitionIfDecoratedWith(BaseTestCase):
    def test_decorated_function_suppressed_plain_helper_still_reported(self):
        self.files = {
            'foo.py': """
                def register(func):
                    return func


                @register
                def registered_handler():
                    return 1


                def unused_helper():
                    return 2
                """
        }

        # With the flag: the decorated function is suppressed, the plain helper is not.
        output = main(['foo.py', '--no-color', '--ignore-definitions-if-decorated-with=@register'])
        self.assertEqual(output, 'foo.py:10:0: DC02 Function `unused_helper` is never used')

        # Without the flag: the decorated function IS reported (the gate is what suppresses it).
        output_without_flag = main(['foo.py', '--no-color'])
        self.assertEqual(
            output_without_flag,
            'foo.py:6:0: DC02 Function `registered_handler` is never used\n'
            'foo.py:10:0: DC02 Function `unused_helper` is never used',
        )
