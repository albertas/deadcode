import logging
from unittest.mock import MagicMock

from deadcode.cli import main, print_main


def test_verbose_configures_info_logging(virtual_file_system, monkeypatch):
    # Having
    virtual_file_system.files = {'sample.py': b'print("ok")\n'}
    basic_config = MagicMock()
    monkeypatch.setattr('deadcode.cli.logging.basicConfig', basic_config)

    # When
    main(['sample.py', '--no-color', '-v'])

    # Then
    basic_config.assert_called_once_with(level=logging.INFO)


def test_without_verbose_no_logging_is_configured(virtual_file_system, monkeypatch):
    # Having
    virtual_file_system.files = {'sample.py': b'print("ok")\n'}
    basic_config = MagicMock()
    monkeypatch.setattr('deadcode.cli.logging.basicConfig', basic_config)

    # When
    main(['sample.py', '--no-color'])

    # Then
    basic_config.assert_not_called()


def test_verbose_logs_files_to_be_checked(tmp_path, monkeypatch, caplog):
    # Having
    sample = tmp_path / 'sample.py'
    sample.write_bytes(b'print("ok")\n')
    monkeypatch.setattr('deadcode.cli.logging.basicConfig', MagicMock())

    # When
    with caplog.at_level(logging.INFO):
        main([str(sample), '--no-color', '-v'])

    # Then
    assert 'Files to be checked for dead code' in caplog.text


def test_without_verbose_no_file_logging(tmp_path, monkeypatch, caplog):
    # Having
    sample = tmp_path / 'sample.py'
    sample.write_bytes(b'print("ok")\n')
    monkeypatch.setattr('deadcode.cli.logging.basicConfig', MagicMock())

    # When
    with caplog.at_level(logging.INFO):
        main([str(sample), '--no-color'])

    # Then
    assert 'Files to be checked for dead code' not in caplog.text


def test_verbose_does_not_change_findings(virtual_file_system, monkeypatch):
    # Having
    virtual_file_system.files = {'sample.py': b'unused_variable = 1\n'}
    monkeypatch.setattr('deadcode.cli.logging.basicConfig', MagicMock())

    # When
    verbose_message = main(['sample.py', '--no-color', '-v'])
    message = main(['sample.py', '--no-color'])
    verbose_exit_status = print_main(['sample.py', '--no-color', '-v'])
    exit_status = print_main(['sample.py', '--no-color'])

    # Then
    assert verbose_message == message
    assert verbose_exit_status == 1
    assert exit_status == 1
