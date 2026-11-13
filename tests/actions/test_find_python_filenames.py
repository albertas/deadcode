import logging

import pytest

from deadcode.actions.find_python_filenames import find_python_filenames
from deadcode.data_types import Args


def test_file_detection(arguments: Args):
    # Having
    arguments.paths = ['deadcode/cli.py']

    # When
    filenames = find_python_filenames(args=arguments)

    # Then
    assert filenames == ['deadcode/cli.py']


def test_exclude_directories(arguments: Args):
    # Having
    arguments.paths = ['deadcode/.']

    # When
    filenames = find_python_filenames(args=arguments)

    # Then
    assert any(f.startswith('deadcode/cli.py') for f in filenames)
    assert any(f.startswith('deadcode/utils') for f in filenames)

    # Having
    arguments.exclude = ['deadcode/utils', 'deadcode/cli.py']

    # When
    filenames = find_python_filenames(args=arguments)

    # Then
    assert not any(f.startswith('deadcode/cli.py') for f in filenames)
    assert not any(f.startswith('deadcode/utils') for f in filenames)


def test_exclude_files(arguments: Args):
    # Having
    arguments.paths = ['deadcode']

    # When
    filenames = find_python_filenames(args=arguments)

    # Then
    assert 'deadcode/cli.py' in filenames

    # Having
    arguments.exclude = ['deadcode/cli.py']

    # When
    filenames = find_python_filenames(args=arguments)

    # Then
    assert 'deadcode/cli.py' not in filenames


def test_provided_path_does_not_exist(arguments: Args, caplog: pytest.LogCaptureFixture):
    # Having
    arguments.paths = ['path_does_not_exist']

    # When
    with caplog.at_level(logging.ERROR):
        find_python_filenames(args=arguments)

    # Then
    assert caplog.records[0].name == 'root'
    assert caplog.records[0].message == 'Error: path_does_not_exist could not be found.'


def test_verbose_logs_ignored_path(arguments: Args, caplog: pytest.LogCaptureFixture):
    # Having
    arguments.paths = ['deadcode/cli.py']
    arguments.exclude = ['deadcode/cli.py']
    arguments.verbose = True

    # When
    with caplog.at_level(logging.INFO):
        find_python_filenames(args=arguments)

    # Then
    assert 'Ignoring: deadcode/cli.py' in [record.message for record in caplog.records]


def test_windows_backslash_path_handling(arguments: Args):
    # Having
    arguments.paths = ['deadcode/cli.py']
    arguments.exclude = ['deadcode\\cli.py']

    # When
    filenames = find_python_filenames(args=arguments)

    # Then
    assert filenames == []
