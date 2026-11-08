from unittest.mock import MagicMock

from deadcode.cli import main, print_main


def test_findings_exit_with_status_one(virtual_file_system):
    # Having
    virtual_file_system.files = {'sample.py': b'unused_variable = 1\n'}

    # When
    result = print_main(['sample.py', '--no-color'])

    # Then
    assert result == 1


def test_clean_file_exits_with_status_zero(virtual_file_system):
    # Having
    virtual_file_system.files = {'sample.py': b'print("Hello")\n'}

    # When
    result = print_main(['sample.py', '--no-color'])

    # Then
    assert result == 0


def test_version_exits_with_status_zero():
    # When
    result = print_main(['--version'])

    # Then
    assert result == 0


def test_main_still_returns_findings_message(virtual_file_system):
    # Having
    virtual_file_system.files = {'sample.py': b'unused_variable = 1\n'}

    # When
    result = main(['sample.py', '--no-color'])

    # Then
    assert result == 'sample.py:1:0: DC01 Variable `unused_variable` is never used'


def test_main_returns_none_for_clean_file(virtual_file_system):
    # Having
    virtual_file_system.files = {'sample.py': b'print("Hello")\n'}

    # When
    result = main(['sample.py', '--no-color'])

    # Then
    assert result is None


def test_findings_with_quiet_exit_with_status_one_without_output(virtual_file_system, monkeypatch):
    # Having
    virtual_file_system.files = {'sample.py': b'unused_variable = 1\n'}
    print_safely = MagicMock()
    monkeypatch.setattr('deadcode.cli.print_safely', print_safely)

    # When
    result = print_main(['sample.py', '--no-color', '--quiet'])

    # Then
    assert result == 1

    print_safely.assert_not_called()


def test_findings_with_count_exit_with_status_one(virtual_file_system):
    # Having
    virtual_file_system.files = {'sample.py': b'unused_variable = 1\n'}

    # When
    result = print_main(['sample.py', '--no-color', '--count'])

    # Then
    assert result == 1


def test_findings_with_no_color_exit_with_status_one(virtual_file_system):
    # Having
    virtual_file_system.files = {'sample.py': b'unused_variable = 1\n'}

    # When
    result = print_main(['sample.py', '--no-color'])

    # Then
    assert result == 1


def test_findings_with_only_exit_with_status_one(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'sample.py': b'unused_variable = 1\n',
        'other.py': b'another_unused_variable = 2\n',
    }

    # When
    result = print_main(['sample.py', '--no-color', '--only', 'sample.py'])

    # Then
    assert result == 1


def test_clean_file_with_count_exits_with_status_zero(virtual_file_system):
    # Having
    virtual_file_system.files = {'sample.py': b'print("Hello")\n'}

    # When
    result = print_main(['sample.py', '--no-color', '--count'])

    # Then
    assert result == 0


def test_clean_file_with_quiet_exits_with_status_zero(virtual_file_system):
    # Having
    virtual_file_system.files = {'sample.py': b'print("Hello")\n'}

    # When
    result = print_main(['sample.py', '--no-color', '--quiet'])

    # Then
    assert result == 0


def test_findings_with_dry_exit_with_status_one_and_do_not_write(virtual_file_system):
    # Having
    original_content = b'unused_variable = 1\nprint("Keep")\n'
    virtual_file_system.files = {'sample.py': original_content}

    # When
    result = print_main(['sample.py', '--no-color', '--dry'])

    # Then
    assert result == 1

    virtual_file_system.assert_files({'sample.py': original_content})


def test_findings_with_fix_exit_with_status_one_then_zero_after_fix(virtual_file_system):
    # Having
    virtual_file_system.files = {'sample.py': b'unused_variable = 1\nprint("Keep")\n'}

    # When
    result = print_main(['sample.py', '--no-color', '--fix'])

    # Then
    assert result == 1
    virtual_file_system.assert_files({'sample.py': b'print("Keep")\n'})

    # Having
    virtual_file_system.files = {'sample.py': b'print("Keep")\n'}

    # When
    result = print_main(['sample.py', '--no-color', '--fix'])

    # Then
    assert result == 0
