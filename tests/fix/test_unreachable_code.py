from deadcode.cli import main


def test_else_is_removed_when_condition_is_true(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                if True:
                    print("Main block")
                else:
                    print("Else block")
                """
    }

    # When
    result = main(['foo.py', '--no-color', '--fix'])

    # Then
    assert result == 'foo.py:4:4: DC09 Unreachable `else` block\n\nRemoved 1 unused code item!'

    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                if True:
                    print("Main block")
                else:
                    pass
                """
        }
    )


def test_if_is_removed_when_condition_is_false(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                if False:
                    print("Main block")
                else:
                    print("Else block")
                """
    }

    # When
    result = main(['foo.py', '--no-color', '--fix'])

    # Then
    assert result == 'foo.py:2:4: DC09 Unsatisfiable `if` condition\n\nRemoved 1 unused code item!'

    virtual_file_system.assert_files({}, removed=['foo.py'])


def test_else_is_removed_when_while_condition_is_true(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                while True:
                    print("Main block")
                else:
                    print("Else block")
                """
    }

    # When
    result = main(['foo.py', '--no-color', '--fix'])

    # Then
    assert result == 'foo.py:4:4: DC09 Unreachable `else` block\n\nRemoved 1 unused code item!'

    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                while True:
                    print("Main block")
                else:
                    pass
                """
        }
    )


def test_while_is_removed_when_condition_is_false(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                while False:
                    print("Main block")
                else:
                    print("Else block")
                """
    }

    # When
    result = main(['foo.py', '--no-color', '--fix'])

    # Then
    assert result == 'foo.py:2:4: DC09 Unsatisfiable `while` condition\n\nRemoved 1 unused code item!'

    virtual_file_system.assert_files({}, removed=['foo.py'])


def test_code_after_return_is_removed(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                def unused_function():
                    return 1
                    print("Unreachable")
                """
    }

    # When
    result = main(['foo.py', '--no-color', '--fix'])

    # Then
    assert result == (
        'foo.py:1:0: DC02 Function `unused_function` is never used\n'
        "foo.py:3:4: DC13 unreachable code after 'return'\n"
        '\n'
        'Removed 2 unused code items!'
    )

    virtual_file_system.assert_files({}, removed=['foo.py'])


def test_elif_block_is_reported(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                if True:
                    print("Main block")
                elif False:
                    print("Unreachable block")
                """
    }

    # When
    result = main(['foo.py', '--no-color'])

    # Then
    assert result == ('foo.py:3:0: DC09 Unreachable `else` block\n' 'foo.py:4:4: DC09 Unsatisfiable `if` condition')
