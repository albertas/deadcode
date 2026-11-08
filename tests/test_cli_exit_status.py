from unittest.mock import MagicMock

from deadcode.cli import main, print_main


def test_findings_exit_with_status_one(virtual_file_system):
    virtual_file_system.files = {'sample.py': b'unused_variable = 1\n'}

    assert print_main(['sample.py', '--no-color']) == 1


def test_clean_file_exits_with_status_zero(virtual_file_system):
    virtual_file_system.files = {'sample.py': b'print("Hello")\n'}

    assert print_main(['sample.py', '--no-color']) == 0


def test_version_exits_with_status_zero():
    assert print_main(['--version']) == 0


def test_main_still_returns_findings_message(virtual_file_system):
    virtual_file_system.files = {'sample.py': b'unused_variable = 1\n'}

    assert main(['sample.py', '--no-color']) == 'sample.py:1:0: DC01 Variable `unused_variable` is never used'


def test_main_returns_none_for_clean_file(virtual_file_system):
    virtual_file_system.files = {'sample.py': b'print("Hello")\n'}

    assert main(['sample.py', '--no-color']) is None


def test_findings_with_quiet_exit_with_status_one_without_output(virtual_file_system, monkeypatch):
    virtual_file_system.files = {'sample.py': b'unused_variable = 1\n'}
    print_safely = MagicMock()
    monkeypatch.setattr('deadcode.cli.print_safely', print_safely)

    assert print_main(['sample.py', '--no-color', '--quiet']) == 1

    print_safely.assert_not_called()


def test_findings_with_count_exit_with_status_one(virtual_file_system):
    virtual_file_system.files = {'sample.py': b'unused_variable = 1\n'}

    assert print_main(['sample.py', '--no-color', '--count']) == 1


def test_findings_with_no_color_exit_with_status_one(virtual_file_system):
    virtual_file_system.files = {'sample.py': b'unused_variable = 1\n'}

    assert print_main(['sample.py', '--no-color']) == 1


def test_findings_with_only_exit_with_status_one(virtual_file_system):
    virtual_file_system.files = {
        'sample.py': b'unused_variable = 1\n',
        'other.py': b'another_unused_variable = 2\n',
    }

    assert print_main(['sample.py', '--no-color', '--only', 'sample.py']) == 1


def test_clean_file_with_count_exits_with_status_zero(virtual_file_system):
    virtual_file_system.files = {'sample.py': b'print("Hello")\n'}

    assert print_main(['sample.py', '--no-color', '--count']) == 0


def test_clean_file_with_quiet_exits_with_status_zero(virtual_file_system):
    virtual_file_system.files = {'sample.py': b'print("Hello")\n'}

    assert print_main(['sample.py', '--no-color', '--quiet']) == 0


def test_findings_with_dry_exit_with_status_one_and_do_not_write(virtual_file_system):
    original_content = b'unused_variable = 1\nprint("Keep")\n'
    virtual_file_system.files = {'sample.py': original_content}

    assert print_main(['sample.py', '--no-color', '--dry']) == 1

    virtual_file_system.assert_files({'sample.py': original_content})


def test_findings_with_fix_exit_with_status_one_then_zero_after_fix(virtual_file_system):
    virtual_file_system.files = {'sample.py': b'unused_variable = 1\nprint("Keep")\n'}

    assert print_main(['sample.py', '--no-color', '--fix']) == 1
    virtual_file_system.assert_files({'sample.py': b'print("Keep")\n'})

    virtual_file_system.files = {'sample.py': b'print("Keep")\n'}

    assert print_main(['sample.py', '--no-color', '--fix']) == 0
