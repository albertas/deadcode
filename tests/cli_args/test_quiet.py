from deadcode.cli import main, print_main


def test_quiet_with_findings_suppresses_output(virtual_file_system, capsys):
    # Having
    virtual_file_system.files = {'sample.py': b'unused_variable = 1\n'}

    # When
    message = main(['sample.py', '--quiet', '--no-color'])

    # Then
    assert message == ''
    assert capsys.readouterr().out == ''
    assert print_main(['sample.py', '--quiet', '--no-color']) == 1


def test_quiet_with_clean_file_suppresses_banner(virtual_file_system, capsys):
    # Having
    virtual_file_system.files = {'sample.py': b'print("ok")\n'}

    # When
    message = main(['sample.py', '--quiet', '--no-color'])

    # Then
    assert message is None
    assert capsys.readouterr().out == ''
    assert print_main(['sample.py', '--quiet', '--no-color']) == 0


def test_quiet_with_count_suppresses_output(virtual_file_system, capsys):
    # Having
    virtual_file_system.files = {'sample.py': b'unused_variable = 1\n'}

    # When
    message = main(['sample.py', '--quiet', '--count', '--no-color'])

    # Then
    assert message == ''
    assert capsys.readouterr().out == ''
    assert print_main(['sample.py', '--quiet', '--count', '--no-color']) == 1
