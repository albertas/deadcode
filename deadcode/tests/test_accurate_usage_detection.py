from unittest import skip

from deadcode.cli import main
from deadcode.tests.base import BaseTestCase


@skip
class TestAccurateUsageDetection(BaseTestCase):
    def test_function_call_with_one_argument(self):
        ## TODO:
        # Variable types should be tracked in each scope
        # When scope changes during call: parameter types should be mapped from arguments

        # When new type is defined: during import or definition: scope has to be updated.

        self.files = {
            "foo.py": """
                class X:
                    def used_method(self):
                        pass

                x = X()

                def foo(y):
                    y.used_method()

                foo(x)
                """
        }

        unused_names = main(["foo.py", "--no-color", "--fix"])
        self.assertIsNone(unused_names)

        self.assertFiles(
            {
                "foo.py": """
                    class X:
                        def used_method(self):
                            pass

                    x = X()

                    def foo(y):
                        y.used_method()

                    foo(x)
                    """
            }
        )
