"""
Test class def.
"""

import pytest

from deadcode.cli import main


def test_class_def__(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                class MyTest:
                    pass
                """
    }

    # When
    main(['foo.py', '--no-color', '--fix'])

    # Then
    virtual_file_system.assert_files({})


def test_class_def_and_method_def(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                class MyTest:
                    def some_method(self):
                        pass
                """
    }

    # When
    main(['foo.py', '--no-color', '--fix'])

    # Then
    virtual_file_system.assert_files({})


def test_class_def(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                class MyTest:
                    pass
                """,
        'bar.py': b"""
                class MyTest:
                    pass
                """,
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--fix'])

    # Then
    assert unused_names == (
        'bar.py:1:0: DC03 Class `MyTest` is never used\n'
        'foo.py:1:0: DC03 Class `MyTest` is never used\n\n'
        'Removed 2 unused code items!'
    )

    virtual_file_system.assert_files({})


@pytest.mark.skip(reason='Skipped without a recorded reason before the pytest migration; behaviour preserved')
def test_definition_imported_from_other_file(virtual_file_system):
    # TODO: this use case has to be solved by using scopes

    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                class MyTest:
                    pass
                """,
        'bar.py': b"""
                class MyTest:
                    pass
                """,
        'spam.py': b"""
                from foo import MyTest

                instance = MyTest()
                print(instance)
                """,
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--fix'])

    # Then
    assert unused_names == ('bar.py:1:0: DC03 Class `MyTest` is never used\n\n' 'Removed 2 unused code items!')

    virtual_file_system.assert_files({})


@pytest.mark.skip(reason='Skipped without a recorded reason before the pytest migration; behaviour preserved')
def test_methods_with_the_same_name(virtual_file_system):
    # TODO: this use case has to be solved by using scopes

    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                class Bar:
                    def foo(self):
                        pass

                class Spam:
                    def foo(self):
                        pass

                bar = Bar()
                spam = Spam()
                print(bar, spam)
                print(bar.foo())
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--fix'])

    # Then
    assert unused_names == ('foo.py:2:4: DC04 Method `foo` is never used\n\n' 'Removed 1 unused code item!')

    virtual_file_system.assert_files({})
