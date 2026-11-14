from deadcode.cli import main, print_main
from deadcode.utils.fix_indent import fix_indent


def test_fix_removes_whole_cascade_in_one_run(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'file.py': b"""
                def helper():
                    return 1


                def main_helper():
                    helper()


                print('survives')
                """
    }

    # When
    unused_names = main(['file.py', '--fix', '--no-color'])

    # Then
    assert unused_names == (
        fix_indent(
            """\
                file.py:1:0: DC02 Function `helper` is never used
                file.py:5:0: DC02 Function `main_helper` is never used

                Removed 2 unused code items!"""
        )
    )

    virtual_file_system.assert_files(
        {
            'file.py': b"""
                    print('survives')
                    """
        }
    )


def test_dry_shows_both_removals_and_exits_1(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'file.py': b"""
                def helper():
                    return 1


                def main_helper():
                    helper()


                print('survives')
                """
    }

    # When
    unused_names = main(['file.py', '--dry', '--no-color'])
    exit_status = print_main(['file.py', '--dry', '--no-color'])

    # Then
    assert unused_names is not None
    assert 'file.py:1:0: DC02 Function `helper` is never used' in unused_names
    assert 'file.py:5:0: DC02 Function `main_helper` is never used' in unused_names
    # The unified diff removes both definitions of the cascade in one run.
    assert '--- file.py' in unused_names
    assert '+++ file.py' in unused_names
    assert '-def helper():' in unused_names
    assert '-def main_helper():' in unused_names
    assert " print('survives')" in unused_names

    assert exit_status == 1

    virtual_file_system.assert_files({'file.py': virtual_file_system.files['file.py']})


def test_fix_removes_cross_module_cascade_in_one_run(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'x.py': b"""
                def foo():
                    return 1
                """,
        'y.py': b"""
                from x import foo


                def relay():
                    return foo()
                """,
        'z.py': b"""
                print('goodbye')
                """,
    }

    # When
    unused_names = main(['.', '--fix', '--no-color'])

    # Then
    assert unused_names == (
        fix_indent(
            """\
                x.py:1:0: DC02 Function `foo` is never used
                y.py:1:14: DC07 Import `foo` is never used
                y.py:4:0: DC02 Function `relay` is never used

                Removed 3 unused code items!"""
        )
    )

    # `x.py` and `y.py` become empty after the removal and are deleted; `z.py` is untouched.
    virtual_file_system.assert_files(
        {
            'z.py': b"""
                    print('goodbye')
                    """
        },
        removed=['x.py', 'y.py'],
    )
