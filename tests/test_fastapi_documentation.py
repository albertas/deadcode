import re
import shutil

from pathlib import Path

import pytest

from deadcode.cli import main
from test_fastapi import DOCUMENTED_CONFIGURATION

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
FASTAPI_DOCUMENTATION_PATH = REPOSITORY_ROOT / 'docs' / 'fastapi.md'
FIXTURE_DIRECTORY = REPOSITORY_ROOT / 'tests' / 'files' / 'fastapi'

FENCED_BLOCK_PATTERN = re.compile(r'```(toml|text)\n(.*?)```', flags=re.DOTALL)


def fenced_blocks(language: str) -> list[str]:
    documentation = FASTAPI_DOCUMENTATION_PATH.read_text(encoding='utf-8')
    return [
        content.strip('\n')
        for block_language, content in FENCED_BLOCK_PATTERN.findall(documentation)
        if block_language == language
    ]


@pytest.fixture()
def project_directory(tmp_path, monkeypatch) -> Path:
    monkeypatch.chdir(tmp_path)
    shutil.copytree(FIXTURE_DIRECTORY, tmp_path / 'project')
    return tmp_path


def test_fastapi_page_documents_the_recommended_configuration():
    # When
    configuration_blocks = fenced_blocks('toml')

    # Then
    assert configuration_blocks == [DOCUMENTED_CONFIGURATION.strip('\n')]


def test_fastapi_page_documents_two_expected_outputs():
    # When
    expected_outputs = fenced_blocks('text')

    # Then
    assert len(expected_outputs) == 2


def test_without_configuration_matches_documented_output(project_directory: Path):
    # Having
    expected_output = fenced_blocks('text')[0]

    # When
    output = main(['project', '--no-color'])

    # Then
    assert output == expected_output


def test_recommended_configuration_matches_documented_output(project_directory: Path):
    # Having
    (project_directory / 'pyproject.toml').write_text(DOCUMENTED_CONFIGURATION)
    expected_output = fenced_blocks('text')[1]

    # When
    output = main(['project', '--no-color'])

    # Then
    assert output == expected_output
