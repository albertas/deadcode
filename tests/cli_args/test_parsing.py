"""
These tests should test command line value conversion into internal Args instance.
"""

import sys
from unittest.mock import MagicMock

import pytest

from deadcode.actions.parse_arguments import parse_arguments


@pytest.fixture
def tomllib_load_mock(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    mock = MagicMock(
        return_value={
            'tool': {
                'deadcode': {
                    'exclude': [],
                    'ignore_names': [],
                    'ignore_names_in_files': [],
                }
            }
        }
    )
    monkeypatch.setattr('deadcode.actions.parse_arguments.tomllib.load', mock)
    return mock


def test_calling_with_one_paths_argument(tomllib_load_mock: MagicMock):
    # Having
    options = '.'

    # When
    args = parse_arguments(options.split())

    # Then
    assert args.paths == ['.']
    assert args.exclude == []
    assert args.ignore_names == []
    assert args.ignore_names_in_files == []


def test_calling_with_several_paths_argument(tomllib_load_mock: MagicMock):
    # Having
    options = '. tests'

    # When
    args = parse_arguments(options.split())

    # Then
    assert args.paths == ['.', 'tests']
    assert args.exclude == []
    assert args.ignore_names == []
    assert args.ignore_names_in_files == []


def test_calling_with_exclude(tomllib_load_mock: MagicMock):
    # Having
    options = '. --exclude=tests,venv'

    # When
    args = parse_arguments(options.split())

    # Then
    assert args.paths == ['.']
    assert args.exclude == ['tests', 'venv']
    assert args.ignore_names == []
    assert args.ignore_names_in_files == []


def test_calling_with_several_exclude_options(tomllib_load_mock: MagicMock):
    # Having
    options = '. --exclude=tests,venv --exclude=migrations'

    # When
    args = parse_arguments(options.split())

    # Then
    assert args.paths == ['.']
    assert args.exclude == ['tests', 'venv', 'migrations']
    assert args.ignore_names == []
    assert args.ignore_names_in_files == []


def test_calling_with_no_color_option(tomllib_load_mock: MagicMock):
    # Having
    options = '. --no-color'

    # When
    args = parse_arguments(options.split())

    # Then
    assert args.paths == ['.']
    assert args.no_color is True


def test_ignore_names_and_ignore_files_command_line_argument_parsing(tomllib_load_mock: MagicMock):
    # Having
    options = '. --ignore-names-in-files=tests,venv --ignore-names=BaseTestCase,lambda_handler'

    # When
    args = parse_arguments(options.split())

    # Then
    assert args.paths == ['.']
    assert args.exclude == []
    assert args.ignore_names == ['BaseTestCase', 'lambda_handler']
    assert args.ignore_names_in_files == ['tests', 'venv']


def test_verbose_flag_is_on_using_long_name(tomllib_load_mock: MagicMock):
    # Having
    options = '--verbose .'

    # When
    args = parse_arguments(options.split())

    # Then
    assert args.verbose is True
    assert args.paths == ['.']


def test_verbose_flag_is_on_using_short_name(tomllib_load_mock: MagicMock):
    # Having
    options = '. -v'

    # When
    args = parse_arguments(options.split())

    # Then
    assert args.paths == ['.']
    assert args.verbose is True


def test_calling_with_fix(tomllib_load_mock: MagicMock):
    # Having
    options = '. --fix'

    # When
    args = parse_arguments(options.split())

    # Then
    assert args.paths == ['.']
    assert args.dry is False
    assert args.fix is True


def test_calling_with_dry(tomllib_load_mock: MagicMock):
    # Having
    options = '. --dry --verbose'

    # When
    args = parse_arguments(options.split())

    # Then
    assert args.paths == ['.']
    assert args.dry is True
    assert args.only == []
    assert args.verbose is True
    assert args.fix is False


def test_calling_with_fix_and_dry(tomllib_load_mock: MagicMock):
    # Having
    options = '. --dry --fix'

    # When
    args = parse_arguments(options.split())

    # Then
    assert args.dry is True
    assert args.fix is False
    assert args.only == []


def test_calling_with_dry_and_single_only_filename(tomllib_load_mock: MagicMock):
    # Having
    options = '. --dry --only foo.py --fix'

    # When
    args = parse_arguments(options.split())

    # Then
    assert args.paths == ['.']
    assert args.dry is True
    assert args.only == ['foo.py']
    assert args.fix is False


def test_scalar_configuration_value_is_treated_as_one_pattern(monkeypatch: pytest.MonkeyPatch):
    # Having
    mock = MagicMock(return_value={'tool': {'deadcode': {'ignore_names_if_inherits_from': 'Base'}}})
    monkeypatch.setattr('deadcode.actions.parse_arguments.tomllib.load', mock)

    # When
    args = parse_arguments(['foo.py'])

    # Then
    assert args.ignore_names_if_inherits_from == ['Base']


def test_scalar_decorator_configuration_is_one_pattern(monkeypatch: pytest.MonkeyPatch):
    # Having
    mock = MagicMock(return_value={'tool': {'deadcode': {'ignore_names_if_decorated_with': '@app.route'}}})
    monkeypatch.setattr('deadcode.actions.parse_arguments.tomllib.load', mock)

    # When
    args = parse_arguments(['foo.py'])

    # Then
    assert args.ignore_names_if_decorated_with == ['@app.route']


def test_calling_with_two_dry_filenames(tomllib_load_mock: MagicMock):
    # Having
    options = '. --fix --dry --only foo.py bar.py'

    # When
    args = parse_arguments(options.split())

    # Then
    assert args.paths == ['.']
    assert args.only == ['foo.py', 'bar.py']
    assert args.fix is False
    assert args.dry is True


def test_sys_argv_used_when_no_arguments_provided(monkeypatch: pytest.MonkeyPatch, tomllib_load_mock: MagicMock):
    # Having
    monkeypatch.setattr(sys, 'argv', ['deadcode', 'foo.py', '--count'])

    # When
    args = parse_arguments(None)

    # Then
    assert args.paths == ['foo.py']
    assert args.count is True


def test_boolean_pyproject_setting_enables_flag(tmp_path, monkeypatch: pytest.MonkeyPatch):
    # Having
    (tmp_path / 'pyproject.toml').write_text('[tool.deadcode]\nfix = true\ncount = true\n')
    monkeypatch.chdir(tmp_path)

    # When
    args = parse_arguments(['foo.py'])

    # Then
    assert args.fix is True
    assert args.count is True


def test_unknown_pyproject_setting_is_ignored(tmp_path, monkeypatch: pytest.MonkeyPatch):
    # Having
    (tmp_path / 'pyproject.toml').write_text('[tool.deadcode]\nunknown_setting = true\n')
    monkeypatch.chdir(tmp_path)

    # When
    args = parse_arguments(['foo.py'])

    # Then
    assert args.paths == ['foo.py']
