"""
Test unused import detection and removal.
"""

from deadcode.cli import main
from deadcode.utils.fix_indent import fix_indent


def test_variable(virtual_file_system):
    virtual_file_system.files = {
        'file2.py': b"""
                from file1 import (
                    foo,
                    bar,
                    xyz
                )

                from file1 import foo

                def fn():
                    pass

                fn()
                """
    }

    unused_names = main('file2.py --no-color --fix -v'.split())

    assert unused_names == fix_indent("""\
                file2.py:2:4: DC07 Import `foo` is never used
                file2.py:3:4: DC07 Import `bar` is never used
                file2.py:4:4: DC07 Import `xyz` is never used
                file2.py:7:18: DC07 Import `foo` is never used

                Removed 4 unused code items!""")

    virtual_file_system.assert_files(
        {
            'file2.py': b"""
                    def fn():
                        pass

                    fn()
                    """
        }
    )
    assert b'fn()' in virtual_file_system.updated_files['file2.py']


def test_unused_single_line_from_import(virtual_file_system):
    virtual_file_system.files = {
        'file2.py': b"""
                from file1 import foo

                def fn():
                    pass

                fn()
                """
    }

    unused_names = main('file2.py --no-color --fix'.split())

    assert 'DC07 Import `foo` is never used' in (unused_names or '')

    virtual_file_system.assert_files(
        {
            'file2.py': b"""
                    def fn():
                        pass

                    fn()
                    """
        }
    )


def test_unused_import_of_several_names(virtual_file_system):
    virtual_file_system.files = {
        'file2.py': b"""
                import a, b

                def fn():
                    pass

                fn()
                """
    }

    unused_names = main('file2.py --no-color --fix'.split())

    assert 'DC07 Import `a` is never used' in (unused_names or '')
    assert 'DC07 Import `b` is never used' in (unused_names or '')

    virtual_file_system.assert_files(
        {
            'file2.py': b"""
                    def fn():
                        pass

                    fn()
                    """
        }
    )


def test_unused_single_line_parenthesized_import(virtual_file_system):
    virtual_file_system.files = {
        'file2.py': b"""
                from file1 import (foo, bar)

                def fn():
                    pass

                fn()
                """
    }

    unused_names = main('file2.py --no-color --fix'.split())

    assert 'DC07 Import `foo` is never used' in (unused_names or '')
    assert 'DC07 Import `bar` is never used' in (unused_names or '')

    virtual_file_system.assert_files(
        {
            'file2.py': b"""
                    def fn():
                        pass

                    fn()
                    """
        }
    )


def test_wildcard_import_is_kept(virtual_file_system):
    virtual_file_system.files = {
        'file2.py': b"""
                from file1 import *
                from file1 import foo

                def fn():
                    pass

                fn()
                """
    }

    unused_names = main('file2.py --no-color --fix'.split())

    assert 'DC07 Import `foo` is never used' in (unused_names or '')

    virtual_file_system.assert_files(
        {
            'file2.py': b"""
                    from file1 import *
                    def fn():
                        pass

                    fn()
                    """
        }
    )
    assert b'from file1 import *' in virtual_file_system.updated_files['file2.py']


def test_partial_same_line_import_removal(virtual_file_system):
    virtual_file_system.files = {
        'file2.py': b"""
                from mymodule.test import used_func, unused_func

                used_func()
                """
    }

    unused_names = main('file2.py --no-color --fix'.split())

    assert 'DC07 Import `unused_func` is never used' in (unused_names or '')
    assert 'DC07 Import `used_func` is never used' not in (unused_names or '')

    virtual_file_system.assert_files(
        {
            'file2.py': b"""
                    from mymodule.test import used_func

                    used_func()
                    """
        }
    )


def test_partial_import_removal_of_unused_names_between_a_used_name(virtual_file_system):
    virtual_file_system.files = {
        'file2.py': b"""
                from file1 import a, b, c

                b()
                """
    }

    unused_names = main('file2.py --no-color --fix'.split())

    assert 'DC07 Import `a` is never used' in (unused_names or '')
    assert 'DC07 Import `c` is never used' in (unused_names or '')
    assert 'DC07 Import `b` is never used' not in (unused_names or '')

    virtual_file_system.assert_files(
        {
            'file2.py': b"""
                    from file1 import b

                    b()
                    """
        }
    )


def test_partial_multi_line_parenthesized_import_removal(virtual_file_system):
    virtual_file_system.files = {
        'file2.py': b"""
                from file1 import (
                    used_func,
                    unused_func,
                    other_unused_func,
                )

                used_func()
                """
    }

    unused_names = main('file2.py --no-color --fix'.split())

    assert 'DC07 Import `unused_func` is never used' in (unused_names or '')
    assert 'DC07 Import `other_unused_func` is never used' in (unused_names or '')
    assert 'DC07 Import `used_func` is never used' not in (unused_names or '')

    virtual_file_system.assert_files(
        {
            'file2.py': b"""
                    from file1 import (
                        used_func,
                    )

                    used_func()
                    """
        }
    )


def test_partial_as_alias_import_removal(virtual_file_system):
    virtual_file_system.files = {
        'file2.py': b"""
                from file1 import foo as bar, used_func

                used_func()
                """
    }

    unused_names = main('file2.py --no-color --fix'.split())

    assert 'DC07 Import `bar` is never used' in (unused_names or '')
    assert 'DC07 Import `used_func` is never used' not in (unused_names or '')

    virtual_file_system.assert_files(
        {
            'file2.py': b"""
                    from file1 import used_func

                    used_func()
                    """
        }
    )


def test_partial_import_of_several_names(virtual_file_system):
    virtual_file_system.files = {
        'file2.py': b"""
                import a, b

                a()
                """
    }

    unused_names = main('file2.py --no-color --fix'.split())

    assert 'DC07 Import `b` is never used' in (unused_names or '')
    assert 'DC07 Import `a` is never used' not in (unused_names or '')

    virtual_file_system.assert_files(
        {
            'file2.py': b"""
                    import a

                    a()
                    """
        }
    )


def test_duplicate_import_with_one_protected_occurrence(virtual_file_system):
    virtual_file_system.files = {
        'file2.py': b"""
                from file1 import foo  # noqa: DC07
                from file1 import foo

                fn()
                """
    }

    unused_names = main('file2.py --no-color --fix'.split())

    assert 'DC07 Import `foo` is never used' in (unused_names or '')

    virtual_file_system.assert_files(
        {
            'file2.py': b"""
                    from file1 import foo  # noqa: DC07
                    fn()
                    """
        }
    )


def test_partial_import_with_noqa_protected_alias(virtual_file_system):
    virtual_file_system.files = {
        'file2.py': b"""
                from file1 import (
                    used_func,
                    unused_func,
                    protected_func,  # noqa: DC07
                )

                used_func()
                """
    }

    unused_names = main('file2.py --no-color --fix'.split())

    assert 'DC07 Import `unused_func` is never used' in (unused_names or '')
    assert 'protected_func' not in (unused_names or '')

    virtual_file_system.assert_files(
        {
            'file2.py': b"""
                    from file1 import (
                        used_func,
                        protected_func,  # noqa: DC07
                    )

                    used_func()
                    """
        }
    )
    assert b'protected_func' in virtual_file_system.updated_files['file2.py']


def test_unused_multi_line_parenthesized_import_block(virtual_file_system):
    virtual_file_system.files = {
        'file2.py': b"""
                def fn():
                    pass

                from file1 import (
                    foo,
                    bar,
                )

                fn()
                """
    }

    unused_names = main('file2.py --no-color --fix'.split())

    assert 'DC07 Import `foo` is never used' in (unused_names or '')
    assert 'DC07 Import `bar` is never used' in (unused_names or '')

    virtual_file_system.assert_files(
        {
            'file2.py': b"""
                    def fn():
                        pass

                    fn()
                    """
        }
    )


def test_issue_24_partly_used_multi_name_from_import(virtual_file_system):
    virtual_file_system.files = {
        'file2.py': b"""
                from mymodule.test import used_func, unused_func

                used_func()
                """
    }

    unused_names = main('file2.py --no-color --fix'.split())

    assert 'DC07 Import `unused_func` is never used' in (unused_names or '')
    assert 'DC07 Import `used_func` is never used' not in (unused_names or '')

    first_content = virtual_file_system.updated_files['file2.py']
    virtual_file_system.assert_files(
        {
            'file2.py': b"""
                    from mymodule.test import used_func

                    used_func()
                    """
        }
    )

    virtual_file_system.files = {'file2.py': first_content}
    second_output = main('file2.py --no-color --fix'.split())

    assert 'never used' not in (second_output or '')
    assert virtual_file_system.updated_files['file2.py'] == first_content


def test_issue_24_fully_unused_single_name_from_import(virtual_file_system):
    virtual_file_system.files = {
        'file2.py': b"""
                from mymodule.test import unused_func

                print(1)
                """
    }

    unused_names = main('file2.py --no-color --fix'.split())

    assert 'DC07 Import `unused_func` is never used' in (unused_names or '')

    first_content = virtual_file_system.updated_files['file2.py']
    virtual_file_system.assert_files(
        {
            'file2.py': b"""
                    print(1)
                    """
        }
    )

    virtual_file_system.files = {'file2.py': first_content}
    second_output = main('file2.py --no-color --fix'.split())

    assert 'never used' not in (second_output or '')
    assert virtual_file_system.updated_files['file2.py'] == first_content


def test_partial_backslash_continued_import_removal(virtual_file_system):
    virtual_file_system.files = {
        'file2.py': b"""
                from m import used, \\
                    unused

                used()
                """
    }

    unused_names = main('file2.py --no-color --fix'.split())

    assert 'DC07 Import `unused` is never used' in (unused_names or '')

    first_content = virtual_file_system.updated_files['file2.py']
    virtual_file_system.assert_files(
        {
            'file2.py': b"""
                    from m import used
                    used()
                    """
        }
    )

    virtual_file_system.files = {'file2.py': first_content}
    second_output = main('file2.py --no-color --fix'.split())

    assert 'never used' not in (second_output or '')
    assert virtual_file_system.updated_files['file2.py'] == first_content


def test_partial_multi_line_last_alias_removal(virtual_file_system):
    virtual_file_system.files = {
        'file2.py': b"""
                from file1 import (
                    used_func,
                    unused_func,
                )

                used_func()
                """
    }

    unused_names = main('file2.py --no-color --fix'.split())

    assert 'DC07 Import `unused_func` is never used' in (unused_names or '')

    first_content = virtual_file_system.updated_files['file2.py']
    virtual_file_system.assert_files(
        {
            'file2.py': b"""
                    from file1 import (
                        used_func
                    )

                    used_func()
                    """
        }
    )

    virtual_file_system.files = {'file2.py': first_content}
    second_output = main('file2.py --no-color --fix'.split())

    assert 'never used' not in (second_output or '')
    assert virtual_file_system.updated_files['file2.py'] == first_content


def test_fully_unused_import_followed_by_statement_on_same_line(virtual_file_system):
    virtual_file_system.files = {'file2.py': b'from m import unused; print(1)\n'}

    unused_names = main('file2.py --no-color --fix'.split())

    assert 'DC07 Import `unused` is never used' in (unused_names or '')

    first_content = virtual_file_system.updated_files['file2.py']
    virtual_file_system.assert_files({'file2.py': b'print(1)\n'})

    virtual_file_system.files = {'file2.py': first_content}
    second_output = main('file2.py --no-color --fix'.split())

    assert 'never used' not in (second_output or '')
    assert virtual_file_system.updated_files['file2.py'] == first_content


def test_fully_unused_import_preceded_by_statement_on_same_line(virtual_file_system):
    virtual_file_system.files = {'file2.py': b'print(1); from m import unused\n'}

    unused_names = main('file2.py --no-color --fix'.split())

    assert 'DC07 Import `unused` is never used' in (unused_names or '')

    first_content = virtual_file_system.updated_files['file2.py']
    virtual_file_system.assert_files({'file2.py': b'print(1)\n'})

    virtual_file_system.files = {'file2.py': first_content}
    second_output = main('file2.py --no-color --fix'.split())

    assert 'never used' not in (second_output or '')
    assert virtual_file_system.updated_files['file2.py'] == first_content


def test_fully_unused_import_with_trailing_comment(virtual_file_system):
    virtual_file_system.files = {'file2.py': b'from m import unused  # only used for typing\n\nprint(1)\n'}

    unused_names = main('file2.py --no-color --fix'.split())

    assert 'DC07 Import `unused` is never used' in (unused_names or '')

    first_content = virtual_file_system.updated_files['file2.py']
    virtual_file_system.assert_files({'file2.py': b'print(1)\n'})

    virtual_file_system.files = {'file2.py': first_content}
    second_output = main('file2.py --no-color --fix'.split())

    assert 'never used' not in (second_output or '')
    assert virtual_file_system.updated_files['file2.py'] == first_content
