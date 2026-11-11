"""Tests for positional paths and every supported argument-source route."""

from pathlib import Path
import sys

import pytest

from deadcode.actions.parse_arguments import parse_arguments
from deadcode.cli import main


def write_pyproject(tmp_path: Path, content: str) -> None:
    (tmp_path / 'pyproject.toml').write_text(f'[tool.deadcode]\n{content}\n')


def test_single_positional_path_is_preserved(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Having
    monkeypatch.chdir(tmp_path)

    # When
    args = parse_arguments(['service.py'])

    # Then
    assert args.paths == ['service.py']


def test_multiple_positional_paths_preserve_order(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Having
    monkeypatch.chdir(tmp_path)

    # When
    args = parse_arguments(['first.py', 'second.py'])

    # Then
    assert args.paths == ['first.py', 'second.py']


def test_positional_paths_are_not_comma_split(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Having
    monkeypatch.chdir(tmp_path)

    # When
    args = parse_arguments(['a,b', 'c'])

    # Then
    assert args.paths == ['a,b', 'c']


def test_toml_array_paths_extend_cli_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Having
    write_pyproject(tmp_path, 'paths = ["from_config.py"]')
    monkeypatch.chdir(tmp_path)

    # When
    args = parse_arguments(['from_cli.py'])

    # Then
    assert args.paths == ['from_cli.py', 'from_config.py']


def test_toml_scalar_path_is_extended_as_one_element(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Having
    write_pyproject(tmp_path, 'paths = "from_config.py"')
    monkeypatch.chdir(tmp_path)

    # When
    args = parse_arguments(['from_cli.py'])

    # Then
    assert args.paths == ['from_cli.py', 'from_config.py']


@pytest.mark.parametrize('function_args', [None, []])
def test_empty_function_args_fall_back_to_sys_argv(
    function_args: list[str] | None, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    # Having
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, 'argv', ['deadcode', 'from_argv.py', '--fix'])

    # When
    args = parse_arguments(function_args)

    # Then
    assert args.paths == ['from_argv.py']
    assert args.fix is True


def test_non_empty_function_args_ignore_sys_argv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Having
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, 'argv', ['deadcode', 'from_argv.py', '--fix'])

    # When
    args = parse_arguments(['from_function.py'])

    # Then
    assert args.paths == ['from_function.py']
    assert args.fix is False


def test_cli_exclude_and_configured_exclude_are_merged_end_to_end(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Having
    (tmp_path / 'service.py').write_text('unused_service = 1\n')
    (tmp_path / 'unused.py').write_text('unused_cli_excluded = 1\n')
    (tmp_path / 'other.py').write_text('unused_config_excluded = 1\n')
    write_pyproject(tmp_path, 'exclude = ["other.py"]')
    monkeypatch.chdir(tmp_path)

    # When
    result = main(['.', '--exclude=unused.py', '--no-color'])

    # Then
    assert result is not None
    assert 'service.py' in result
    assert 'unused.py' not in result
    assert 'other.py' not in result
