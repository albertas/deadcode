import logging

import pytest

from deadcode.actions.find_python_filenames import find_python_filenames
from deadcode.data_types import Args


def test_file_detection(arguments: Args):
    arguments.paths = ['deadcode/cli.py']
    filenames = find_python_filenames(args=arguments)
    assert filenames == ['deadcode/cli.py']


def test_exclude_directories(arguments: Args):
    arguments.paths = ['deadcode/.']
    filenames = find_python_filenames(args=arguments)
    assert any(f.startswith('deadcode/cli.py') for f in filenames)
    assert any(f.startswith('deadcode/utils') for f in filenames)

    arguments.exclude = ['deadcode/utils', 'deadcode/cli.py']
    filenames = find_python_filenames(args=arguments)
    assert not any(f.startswith('deadcode/cli.py') for f in filenames)
    assert not any(f.startswith('deadcode/utils') for f in filenames)


def test_exclude_files(arguments: Args):
    arguments.paths = ['deadcode']
    filenames = find_python_filenames(args=arguments)
    assert 'deadcode/cli.py' in filenames

    arguments.exclude = ['deadcode/cli.py']
    filenames = find_python_filenames(args=arguments)
    assert 'deadcode/cli.py' not in filenames


def test_provided_path_does_not_exist(arguments: Args, caplog: pytest.LogCaptureFixture):
    arguments.paths = ['path_does_not_exist']
    with caplog.at_level(logging.ERROR):
        find_python_filenames(args=arguments)

    assert caplog.records[0].name == 'root'
    assert caplog.records[0].message == 'Error: path_does_not_exist could not be found.'
