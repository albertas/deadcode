from deadcode.cli import main, print_main


def test_quiet_with_findings_suppresses_output(virtual_file_system, capsys):
    # Having
    virtual_file_system.files = {'sample.py': b'unused_variable = 1\n'}

    # When
    message = main(['sample.py', '--quiet', '--no-color'])

    # Then
    assert message == ''
    assert capsys.readouterr().out == ''

    # When
    result = print_main(['sample.py', '--quiet', '--no-color'])

    # Then
    assert result == 1


def test_quiet_with_clean_file_suppresses_banner(virtual_file_system, capsys):
    # Having
    virtual_file_system.files = {'sample.py': b'print("ok")\n'}

    # When
    message = main(['sample.py', '--quiet', '--no-color'])

    # Then
    assert message is None
    assert capsys.readouterr().out == ''

    # When
    result = print_main(['sample.py', '--quiet', '--no-color'])

    # Then
    assert result == 0


def test_quiet_on_cascade_returns_empty_message_with_exit_1(virtual_file_system, capsys):
    # Having
    virtual_file_system.files = {
        'main.py': b"""
                def helper():
                    return 1


                def main_helper():
                    helper()
                """,
    }

    # When
    message = main(['main.py', '--quiet', '--no-color'])

    # Then
    assert message == ''
    assert capsys.readouterr().out == ''

    # When
    result = print_main(['main.py', '--quiet', '--no-color'])

    # Then
    assert result == 1


def test_quiet_with_count_suppresses_output(virtual_file_system, capsys):
    # Having
    virtual_file_system.files = {'sample.py': b'unused_variable = 1\n'}

    # When
    message = main(['sample.py', '--quiet', '--count', '--no-color'])

    # Then
    assert message == ''
    assert capsys.readouterr().out == ''

    # When
    result = print_main(['sample.py', '--quiet', '--count', '--no-color'])

    # Then
    assert result == 1
