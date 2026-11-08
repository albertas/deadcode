from deadcode.cli import main, print_main


def test_count_returns_number_of_findings(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'one.py': b'unused_one = 1\n',
        'two.py': b'unused_two = 2\n',
    }

    # When
    message = main(['one.py', 'two.py', '--count', '--no-color'])

    # Then
    assert message == '2'


def test_count_only_reflects_only_option(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'one.py': b'unused_one = 1\n',
        'two.py': b'unused_two = 2\n',
    }

    # When
    message = main(['one.py', 'two.py', '--count', '--only', 'one.py', '--no-color'])

    # Then
    assert message == '1'


def test_count_exit_status(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'one.py': b'unused_one = 1\n',
        'two.py': b'unused_two = 2\n',
    }

    # When
    exit_status = print_main(['one.py', 'two.py', '--count', '--no-color'])

    # Then
    assert exit_status == 1


def test_count_with_only_matching_nothing_is_clean(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'one.py': b'unused_one = 1\n',
        'two.py': b'unused_two = 2\n',
    }

    # When
    message = main(['one.py', 'two.py', '--count', '--only', 'missing.py', '--no-color'])
    exit_status = print_main(['one.py', 'two.py', '--count', '--only', 'missing.py', '--no-color'])

    # Then
    assert message is None
    assert exit_status == 0
