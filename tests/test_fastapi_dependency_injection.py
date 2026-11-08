import re
import shutil

from pathlib import Path

import pytest

from deadcode.cli import main, print_main

DEPENDENCY_INJECTION_FIXTURE_DIRECTORY = Path(__file__).parent / 'files' / 'fastapi_dependency_injection'

DOCUMENTED_CONFIGURATION = """[tool.deadcode]
ignore-names-if-decorated-with = ["@app.*", "@router.*"]
ignore-bodies-if-inherits-from = ["BaseModel"]
"""

FINDING_PATTERN = re.compile(r'^(?P<path>.+):\d+:\d+: (?P<code>DC\d+) \w+ `(?P<name>[^`]+)` is never used$')


def _findings(output: str | None) -> set[tuple[str, str, str]]:
    assert output is not None
    findings = set()
    for line in output.splitlines():
        match = FINDING_PATTERN.match(line)
        assert match is not None, line
        findings.add((match.group('path'), match.group('code'), match.group('name')))
    return findings


@pytest.fixture()
def project_directory(tmp_path, monkeypatch) -> Path:
    monkeypatch.chdir(tmp_path)
    shutil.copytree(DEPENDENCY_INJECTION_FIXTURE_DIRECTORY, tmp_path / 'project')
    (tmp_path / 'pyproject.toml').write_text(DOCUMENTED_CONFIGURATION)
    return tmp_path


def test_all_dependency_injection_forms_are_supported(project_directory: Path) -> None:
    assert _findings(main(['project', '--no-color'])) == {
        ('project/dependencies.py', 'DC02', 'unused_dependency'),
    }
    assert print_main(['project', '--no-color']) == 1


def test_dependency_injection_providers_are_not_reported(project_directory: Path) -> None:
    output = main(['project', '--no-color'])

    assert output is not None
    for provider in (
        'Settings',
        'get_settings',
        'Pagination',
        'RequestId',
        'request_id',
        'get_database',
        'get_client',
        'get_optional_user',
        'get_current_user',
        'get_basic_user',
        'require_admin',
        'verify_api_key',
        'oauth2_scheme',
        'basic_scheme',
        'api_key_scheme',
    ):
        assert provider not in output
