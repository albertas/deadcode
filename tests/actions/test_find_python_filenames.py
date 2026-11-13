import logging
from pathlib import Path, PureWindowsPath

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


def test_discovery_returns_forward_slash_paths(tmp_path: Path, arguments: Args):
    # Having
    package = tmp_path / 'pkg'
    package.mkdir()
    (package / 'mod.py').write_text('')
    (tmp_path / 'top.py').write_text('')
    arguments.paths = [str(tmp_path)]

    # When
    filenames = find_python_filenames(args=arguments)

    # Then
    assert any(filename.endswith('/pkg/mod.py') for filename in filenames)
    assert any(filename.endswith('/top.py') for filename in filenames)
    assert all('\\' not in filename for filename in filenames)


def test_discovery_normalizes_windows_paths(
    monkeypatch: pytest.MonkeyPatch, arguments: Args, caplog: pytest.LogCaptureFixture
):
    # Having
    files = {'C:\\root\\pkg\\mod.py', 'C:\\root\\skip.py'}
    directories = {
        'C:\\root': ['C:\\root\\pkg', 'C:\\root\\skip.py'],
        'C:\\root\\pkg': ['C:\\root\\pkg\\mod.py'],
    }
    seen_values = []

    class WindowsPath(PureWindowsPath):
        def is_file(self) -> bool:
            return str(self) in files

        def is_dir(self) -> bool:
            return str(self) in directories

        def exists(self) -> bool:
            return self.is_file() or self.is_dir()

        def glob(self, pattern: str) -> list['WindowsPath']:
            return [WindowsPath(child) for child in directories.get(str(self), [])]

    def make_path(value: str) -> WindowsPath:
        seen_values.append(str(value))
        return WindowsPath(value)

    monkeypatch.setattr('deadcode.actions.find_python_filenames.Path', make_path)
    arguments.paths = ['C:\\root']
    arguments.exclude = ['C:\\root\\skip.py']
    arguments.verbose = True

    # When
    with caplog.at_level(logging.INFO):
        filenames = find_python_filenames(args=arguments)

    # Then
    assert filenames == ['C:/root/pkg/mod.py']
    assert all('\\' not in filename for filename in filenames)
    assert all(value == 'C:\\root' or '\\' not in value for value in seen_values)
    messages = [record.message for record in caplog.records]
    assert 'Ignoring: C:/root/skip.py' in messages
    assert any(
        message.startswith('Files to be checked for dead code:') and 'C:/root/pkg/mod.py' in message
        for message in messages
    )
