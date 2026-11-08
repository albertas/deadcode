"""
Test unused assignment expression detection and removal.
"""

import pytest

from deadcode.cli import main


def test_variable(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                unused_variable = 123
                print("Keep the file")
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--fix'])

    # Then
    assert unused_names == ('foo.py:1:0: DC01 Variable `unused_variable` is never used\n\nRemoved 1 unused code item!')

    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                print("Keep the file")
            """
        }
    )


def test_multiline_call_assignment(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                unused_variable = function_call(
                    param1, param2, param3
                )
                print("Keep the file")
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--fix'])

    # Then
    assert unused_names == ('foo.py:1:0: DC01 Variable `unused_variable` is never used\n\nRemoved 1 unused code item!')

    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                print("Keep the file")
            """
        }
    )


def test_multiline_list_assignment(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                unused_variable = [
                    1,
                    2,
                ]
                print("Keep the file")
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--fix'])

    # Then
    assert unused_names == ('foo.py:1:0: DC01 Variable `unused_variable` is never used\n\nRemoved 1 unused code item!')

    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                print("Keep the file")
            """
        }
    )


def test_multiline_dict_assignment(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                unused_variable = {
                    'a': 1,
                }
                print("Keep the file")
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--fix'])

    # Then
    assert unused_names == ('foo.py:1:0: DC01 Variable `unused_variable` is never used\n\nRemoved 1 unused code item!')

    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                print("Keep the file")
            """
        }
    )


def test_multiline_parenthesised_binary_expression_assignment(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                unused_variable = (
                    1
                    + 2
                )
                print("Keep the file")
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--fix'])

    # Then
    assert unused_names == ('foo.py:1:0: DC01 Variable `unused_variable` is never used\n\nRemoved 1 unused code item!')

    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                print("Keep the file")
            """
        }
    )


def test_multiline_nested_call_assignment(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                unused_variable = outer_call(
                    inner_call(
                        1,
                    ),
                    3,
                )
                print("Keep the file")
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--fix'])

    # Then
    assert unused_names == ('foo.py:1:0: DC01 Variable `unused_variable` is never used\n\nRemoved 1 unused code item!')

    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                print("Keep the file")
            """
        }
    )


def test_multiline_fstring_assignment(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                unused_variable = f\"\"\"
                hello
                \"\"\"
                print("Keep the file")
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--fix'])

    # Then
    assert unused_names == ('foo.py:1:0: DC01 Variable `unused_variable` is never used\n\nRemoved 1 unused code item!')

    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                print("Keep the file")
            """
        }
    )


def test_multiline_triple_quoted_string_assignment(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                unused_variable = \"\"\"
                hello
                \"\"\"
                print("Keep the file")
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--fix'])

    # Then
    assert unused_names == ('foo.py:1:0: DC01 Variable `unused_variable` is never used\n\nRemoved 1 unused code item!')

    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                print("Keep the file")
            """
        }
    )


def test_multiline_annotated_assignment(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                unused_variable: list[int] = [
                    1,
                ]
                print("Keep the file")
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--fix'])

    # Then
    assert unused_names == ('foo.py:1:0: DC01 Variable `unused_variable` is never used\n\nRemoved 1 unused code item!')

    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                print("Keep the file")
            """
        }
    )


def test_multiline_augmented_assignment(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                unused_variable = 0
                unused_variable += (
                    1
                )
                print("Keep the file")
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--fix'])

    # Then
    assert unused_names == (
        'foo.py:1:0: DC01 Variable `unused_variable` is never used\n'
        'foo.py:2:0: DC01 Variable `unused_variable` is never used\n\n'
        'Removed 2 unused code items!'
    )

    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                print("Keep the file")
            """
        }
    )


def test_multiline_assignment_inside_function(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                def keep_function():
                    unused_variable = function_call(
                        param1,
                    )
                    print("Keep the file")

                keep_function()
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--fix'])

    # Then
    assert unused_names == ('foo.py:2:4: DC01 Variable `unused_variable` is never used\n\nRemoved 1 unused code item!')

    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                def keep_function():
                    print("Keep the file")

                keep_function()
            """
        }
    )


def test_multiline_assignment_inside_class(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                class KeepClass:
                    unused_variable = [
                        1,
                    ]

                    def keep_method(self):
                        pass

                KeepClass().keep_method()
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--fix'])

    # Then
    assert unused_names == ('foo.py:2:4: DC06 Name `unused_variable` is never used\n\nRemoved 1 unused code item!')

    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                class KeepClass:
                    def keep_method(self):
                        pass

                KeepClass().keep_method()
            """
        }
    )


def test_multiple_multiline_assignments(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                unused_call = function_call(
                    param1,
                )
                unused_list = [
                    1,
                ]
                print("Keep the file")
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--fix'])

    # Then
    assert unused_names == (
        'foo.py:1:0: DC01 Variable `unused_call` is never used\n'
        'foo.py:4:0: DC01 Variable `unused_list` is never used\n\n'
        'Removed 2 unused code items!'
    )

    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                print("Keep the file")
            """
        }
    )


def test_multiline_assignment_fix_is_idempotent(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                unused_variable = function_call(
                    param1, param2, param3
                )
                print("Keep the file")
                """
    }

    # When
    first_output = main(['foo.py', '--no-color', '--fix'])

    # Then
    assert 'DC01 Variable `unused_variable` is never used' in (first_output or '')

    # Having
    first_content = virtual_file_system.updated_files['foo.py']

    # Then
    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                print("Keep the file")
            """
        }
    )

    # Having
    virtual_file_system.files = {'foo.py': first_content}

    # When
    second_output = main(['foo.py', '--no-color', '--fix'])

    # Then
    assert 'never used' not in (second_output or '')
    assert virtual_file_system.updated_files['foo.py'] == first_content


@pytest.mark.skip(reason='Skipped without a recorded reason before the pytest migration; behaviour preserved')
def test_variable_with_type_hint(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
            unused_variable: List[int] = [123]
        """
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--fix'])

    # Then
    assert unused_names == ('foo.py:1:0: DC01 Variable `unused_variable` is never used\n\nRemoved 1 unused code item!')

    virtual_file_system.assert_files({'foo.py': b""""""})


@pytest.mark.skip(reason='Skipped without a recorded reason before the pytest migration; behaviour preserved')
def test_unused_variable_in_multiple_inline_assignment_start(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
            foo, bar, spam = None, [], "Spam"
            print(bar, spam)
        """
    }


@pytest.mark.skip(reason='Skipped without a recorded reason before the pytest migration; behaviour preserved')
def test_unused_variable_in_multiple_inline_assignment_end(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
            foo, bar, spam = None, [], "Spam"
            print(foo, bar)
        """
    }


@pytest.mark.skip(reason='Skipped without a recorded reason before the pytest migration; behaviour preserved')
def test_unused_variable_in_multiple_inline_assignment_middle(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
            foo, bar, spam = None, [], "Spam"
            print(foo, spam)
        """
    }


@pytest.mark.skip(reason='Skipped without a recorded reason before the pytest migration; behaviour preserved')
def test_multiple_unused_variables_in_multiple_inline_assignment(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
            foo, bar, spam = None, [], "Spam"
            print(spam)
        """
    }


@pytest.mark.skip(reason='Skipped without a recorded reason before the pytest migration; behaviour preserved')
def test_all_unused_variables_in_multiple_inline_assignment(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
            foo, bar, spam = None, [], "Spam"
        """
    }
