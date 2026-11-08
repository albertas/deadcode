from deadcode.cli import main


def test_else_is_not_changed_when_condition_is_true(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
                if True:
                    print("Main block")
                else:
                    print("Else block")
                """
    }

    result = main(['foo.py', '--no-color', '--fix'])
    assert result is None

    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                if True:
                    print("Main block")
                else:
                    print("Else block")
                """
        }
    )


def test_else_is_not_changed_when_condition_is_false(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
                if False:
                    print("Main block")
                else:
                    print("Else block")
                """
    }

    result = main(['foo.py', '--no-color', '--fix'])
    assert result is None

    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                if False:
                    print("Main block")
                else:
                    print("Else block")
                """
        }
    )


def test_while_is_not_changed_when_condition_is_true(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
                while True:
                    print("Main block")
                else:
                    print("Else block")
                """
    }

    result = main(['foo.py', '--no-color', '--fix'])
    assert result is None

    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                while True:
                    print("Main block")
                else:
                    print("Else block")
                """
        }
    )


def test_while_is_not_changed_when_condition_is_false(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
                while False:
                    print("Main block")
                else:
                    print("Else block")
                """
    }

    result = main(['foo.py', '--no-color', '--fix'])
    assert result is None

    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                while False:
                    print("Main block")
                else:
                    print("Else block")
                """
        }
    )
