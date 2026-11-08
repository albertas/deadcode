from deadcode.cli import main, print_main


def test_no_color_removes_banner_colors(virtual_file_system, capsys):
    # Having
    virtual_file_system.files = {'sample.py': b'print("ok")\n'}

    # When
    exit_status = print_main(['sample.py', '--no-color'])

    # Then
    assert exit_status == 0
    assert capsys.readouterr().out == 'Well done! ✨ 🚀 ✨\n'


def test_banner_keeps_colors_without_the_flag(virtual_file_system, capsys):
    # Having
    virtual_file_system.files = {'sample.py': b'print("ok")\n'}

    # When
    exit_status = print_main(['sample.py'])

    # Then
    assert exit_status == 0
    assert '\033[1m' in capsys.readouterr().out


def test_no_color_removes_finding_colors(virtual_file_system):
    # Having
    virtual_file_system.files = {'sample.py': b'unused_variable = 1\n'}

    # When
    message = main(['sample.py', '--no-color'])

    # Then
    assert message == 'sample.py:1:0: DC01 Variable `unused_variable` is never used'
    assert '\033' not in message
