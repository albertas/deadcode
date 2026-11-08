import re
from pathlib import Path

import pytest

from deadcode.actions.parse_arguments import parse_arguments

README_PATH = Path(__file__).resolve().parents[2] / 'README.md'

OPTIONS_SECTION_START = '## Command line options'
OPTIONS_SECTION_END = '### Decorator matching'


def _readme_section() -> str:
    readme_text = README_PATH.read_text(encoding='utf-8')
    start = readme_text.index(OPTIONS_SECTION_START)
    end = readme_text.index(OPTIONS_SECTION_END, start)
    return readme_text[start:end]


def documented_options() -> dict[str, str]:
    """Maps every long option documented in the README table to its meaning cell."""
    options: dict[str, str] = {}
    for line in _readme_section().splitlines():
        if not line.startswith('|'):
            continue
        option_tokens = re.findall(r'`(-[^`]+)`', line)
        if not option_tokens:
            continue
        long_option = max(option_tokens, key=len)
        cells = line.split('|')
        options[long_option] = cells[3].strip()
    return options


def _normalise(text: str) -> str:
    return ' '.join(text.replace('`', '').split())


@pytest.mark.parametrize('option', sorted(documented_options()))
def test_documented_option_is_accepted(option, monkeypatch, tmp_path):
    # Having
    monkeypatch.chdir(tmp_path)

    # When
    args = parse_arguments(['sample.py', option])

    # Then
    assert hasattr(args, option.lstrip('-').replace('-', '_'))


def test_documented_options_appear_in_help(monkeypatch, tmp_path, capsys):
    # Having
    monkeypatch.setenv('COLUMNS', '300')
    monkeypatch.chdir(tmp_path)

    # When
    with pytest.raises(SystemExit):
        parse_arguments(['--help'])

    help_output = capsys.readouterr().out

    # Then
    for option in documented_options():
        assert option in help_output


@pytest.mark.parametrize('option', ['--dry', '--only', '--ignore-names'])
def test_help_text_matches_readme_meaning(option, monkeypatch, tmp_path, capsys):
    # Having
    monkeypatch.setenv('COLUMNS', '300')
    monkeypatch.chdir(tmp_path)

    # When
    with pytest.raises(SystemExit):
        parse_arguments(['--help'])

    help_output = _normalise(capsys.readouterr().out)
    readme_meaning = _normalise(documented_options()[option])

    # Then
    assert readme_meaning in help_output
