"""
Test unused assignment expression detection and removal.
"""

import pytest

from deadcode.cli import main


def test_variable(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
                unused_variable = 123
                print("Keep the file")
                """
    }

    unused_names = main(['foo.py', '--no-color', '--fix'])
    assert unused_names == (
        'foo.py:1:0: DC01 Variable `unused_variable` is never used\n\n' 'Removed 1 unused code item!'
    )

    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                print("Keep the file")
            """
        }
    )


@pytest.mark.skip(reason='Skipped without a recorded reason before the pytest migration; behaviour preserved')
def test_variable_with_type_hint(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
            unused_variable: List[int] = [123]
        """
    }

    unused_names = main(['foo.py', '--no-color', '--fix'])
    assert unused_names == (
        'foo.py:1:0: DC01 Variable `unused_variable` is never used\n\n' 'Removed 1 unused code item!'
    )

    virtual_file_system.assert_files({'foo.py': b""""""})


@pytest.mark.skip(reason='Skipped without a recorded reason before the pytest migration; behaviour preserved')
def test_unused_variable_in_multiple_inline_assignment_start(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
            foo, bar, spam = None, [], "Spam"
            print(bar, spam)
        """
    }


@pytest.mark.skip(reason='Skipped without a recorded reason before the pytest migration; behaviour preserved')
def test_unused_variable_in_multiple_inline_assignment_end(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
            foo, bar, spam = None, [], "Spam"
            print(foo, bar)
        """
    }


@pytest.mark.skip(reason='Skipped without a recorded reason before the pytest migration; behaviour preserved')
def test_unused_variable_in_multiple_inline_assignment_middle(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
            foo, bar, spam = None, [], "Spam"
            print(foo, spam)
        """
    }


@pytest.mark.skip(reason='Skipped without a recorded reason before the pytest migration; behaviour preserved')
def test_multiple_unused_variables_in_multiple_inline_assignment(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
            foo, bar, spam = None, [], "Spam"
            print(spam)
        """
    }


@pytest.mark.skip(reason='Skipped without a recorded reason before the pytest migration; behaviour preserved')
def test_all_unused_variables_in_multiple_inline_assignment(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
            foo, bar, spam = None, [], "Spam"
        """
    }
