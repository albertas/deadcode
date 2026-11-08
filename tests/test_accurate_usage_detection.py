import pytest

from deadcode.cli import main

pytestmark = pytest.mark.skip(
    reason='Skipped without a recorded reason before the pytest migration; behaviour preserved'
)


def test_function_call_with_one_argument(virtual_file_system):
    ## TODO:
    # Variable types should be tracked in each scope
    # When scope changes during call: parameter types should be mapped from arguments

    # When new type is defined: during import or definition: scope has to be updated.

    virtual_file_system.files = {
        'foo.py': b"""
                class X:
                    def used_method(self):
                        pass

                x = X()

                def foo(y):
                    y.used_method()

                foo(x)
                """
    }

    unused_names = main(['foo.py', '--no-color', '--fix'])
    assert unused_names is None

    virtual_file_system.assert_files(
        {
            'foo.py': b"""
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
