"""Tests for list-like options provided through every supported input form."""

from pathlib import Path

import pytest

from deadcode.actions.parse_arguments import parse_arguments


LIST_OPTIONS = (
    'only',
    'exclude',
    'ignore_names',
    'ignore_bodies_of',
    'ignore_bodies_if_decorated_with',
    'ignore_bodies_if_inherits_from',
    'ignore_definitions',
    'ignore_definitions_if_inherits_from',
    'ignore_definitions_if_decorated_with',
    'ignore_if_decorated_with',
    'ignore_if_inherits_from',
    'ignore_names_if_inherits_from',
    'ignore_names_if_decorated_with',
    'ignore_names_in_files',
)


def write_pyproject(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, content: str) -> None:
    (tmp_path / 'pyproject.toml').write_text(f'[tool.deadcode]\n{content}\n')
    monkeypatch.chdir(tmp_path)


@pytest.mark.parametrize('option', LIST_OPTIONS)
def test_list_option_from_single_comma_separated_cli_value(
    option: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    # Having
    write_pyproject(tmp_path, monkeypatch, '')

    # When
    args = parse_arguments(['service.py', f'--{option.replace("_", "-")}=a,b'])

    # Then
    assert getattr(args, option) == ['a', 'b']


@pytest.mark.parametrize('option', LIST_OPTIONS)
def test_list_option_from_multiple_space_separated_cli_values(
    option: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    # Having
    write_pyproject(tmp_path, monkeypatch, '')

    # When
    args = parse_arguments(['service.py', f'--{option.replace("_", "-")}', 'a', 'b'])

    # Then
    assert getattr(args, option) == ['a', 'b']


@pytest.mark.parametrize('option', LIST_OPTIONS)
def test_list_option_from_repeated_cli_values(option: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Having
    write_pyproject(tmp_path, monkeypatch, '')

    # When
    args = parse_arguments(['service.py', f'--{option.replace("_", "-")}=a', f'--{option.replace("_", "-")}=b'])

    # Then
    assert getattr(args, option) == ['a', 'b']


@pytest.mark.parametrize('option', LIST_OPTIONS)
def test_list_option_from_toml_array(option: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Having
    write_pyproject(tmp_path, monkeypatch, f'{option} = ["a", "b"]')

    # When
    args = parse_arguments(['service.py'])

    # Then
    assert getattr(args, option) == ['a', 'b']


@pytest.mark.parametrize('option', LIST_OPTIONS)
def test_list_option_from_toml_scalar_is_wrapped_in_a_list(
    option: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    # Having
    write_pyproject(tmp_path, monkeypatch, f'{option} = "a"')

    # When
    args = parse_arguments(['service.py'])

    # Then
    assert getattr(args, option) == ['a']


@pytest.mark.parametrize('option', ['only', 'exclude', 'ignore_names'])
def test_toml_values_are_appended_after_cli_values(option: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Having
    write_pyproject(tmp_path, monkeypatch, f'{option} = ["from_config.py"]')

    # When
    args = parse_arguments(['service.py', f'--{option.replace("_", "-")}=from_cli.py'])

    # Then
    assert getattr(args, option) == ['from_cli.py', 'from_config.py']


@pytest.mark.parametrize('key', ['ignore-names', 'ignore_names', '--ignore-names'])
def test_list_option_key_spellings_are_normalized(key: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Having
    write_pyproject(tmp_path, monkeypatch, f'{key} = ["UnusedName"]')

    # When
    args = parse_arguments(['service.py'])

    # Then
    assert args.ignore_names == ['UnusedName']
