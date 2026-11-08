from deadcode.cli import main


def test_commented_out_code_is_removed(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
                unused_variable = 1
                # print("Hello world")
                print(unused_variable)
                """
    }

    result = main(['foo.py', '--no-color', '--fix'])
    assert result == 'foo.py:2:0: DC12 Commented out code\n\nRemoved 1 unused code item!'

    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                unused_variable = 1
                print(unused_variable)
                """
        }
    )


def test_trailing_commented_out_code_keeps_the_code(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
                unused_variable = 1  # print("Hello world")
                print(unused_variable)
                """
    }

    result = main(['foo.py', '--no-color', '--fix'])
    assert result == 'foo.py:1:21: DC12 Commented out code\n\nRemoved 1 unused code item!'

    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                unused_variable = 1
                print(unused_variable)
                """
        }
    )


def test_plain_comment_is_not_reported(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
                # TODO: explain the next line
                print("Keep the file")
                """
    }

    assert main(['foo.py', '--no-color']) is None
