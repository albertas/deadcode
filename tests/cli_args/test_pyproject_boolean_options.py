"""Tests for boolean options provided through pyproject.toml."""

from pathlib import Path
import sys

import pytest

from deadcode.actions.parse_arguments import parse_arguments
from deadcode.cli import print_main


BOOLEAN_OPTIONS = ('fix', 'dry', 'no_color', 'quiet', 'count', 'verbose', 'version')

CLI_FLAGS = {
    'fix': '--fix',
    'dry': '--dry',
    'no_color': '--no-color',
    'quiet': '--quiet',
    'count': '--count',
    'verbose': '--verbose',
    'version': '--version',
}


def write_pyproject(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, content: str) -> None:
    (tmp_path / 'pyproject.toml').write_text(f'[tool.deadcode]\n{content}\n')
    monkeypatch.chdir(tmp_path)


@pytest.mark.parametrize('option', BOOLEAN_OPTIONS)
def test_boolean_option_enabled_from_pyproject(option: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Having
    write_pyproject(tmp_path, monkeypatch, f'{option} = true')

    # When
    args = parse_arguments(['service.py'])

    # Then
    assert getattr(args, option) is True


@pytest.mark.parametrize('option', BOOLEAN_OPTIONS)
def test_boolean_option_disabled_from_pyproject(option: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Having
    write_pyproject(tmp_path, monkeypatch, f'{option} = false')

    # When
    args = parse_arguments(['service.py'])

    # Then
    assert getattr(args, option) is False


@pytest.mark.parametrize('option', BOOLEAN_OPTIONS)
def test_disabled_pyproject_boolean_does_not_cancel_cli_flag(
    option: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    # Having
    write_pyproject(tmp_path, monkeypatch, f'{option} = false')

    # When
    args = parse_arguments(['service.py', CLI_FLAGS[option]])

    # Then
    assert getattr(args, option) is True


@pytest.mark.parametrize('option', BOOLEAN_OPTIONS)
def test_enabled_pyproject_boolean_keeps_cli_flag(option: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Having
    write_pyproject(tmp_path, monkeypatch, f'{option} = true')

    # When
    args = parse_arguments(['service.py', CLI_FLAGS[option]])

    # Then
    assert getattr(args, option) is True


@pytest.mark.parametrize('key', ['fix', '--fix'])
def test_pyproject_boolean_key_spellings(key: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Having
    write_pyproject(tmp_path, monkeypatch, f'{key} = true')

    # When
    args = parse_arguments(['service.py'])

    # Then
    assert args.fix is True


def test_configured_dry_disables_configured_fix(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Having
    write_pyproject(tmp_path, monkeypatch, 'dry = true\nfix = true')

    # When
    args = parse_arguments(['service.py'])

    # Then
    assert args.dry is True
    assert args.fix is False


def test_configured_fix_changes_observable_cli_behavior(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Having
    service = tmp_path / 'service.py'
    service.write_text('import os\n\n\nprint("hello")\n')
    write_pyproject(tmp_path, monkeypatch, 'fix = true')
    monkeypatch.setattr(sys, 'argv', ['deadcode', 'service.py'])

    # When
    exit_status = print_main(['service.py', '--no-color'])

    # Then
    assert exit_status == 1
    assert service.read_text() == 'print("hello")\n'
