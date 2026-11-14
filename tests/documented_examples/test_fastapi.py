import re
import shutil

from pathlib import Path

from deadcode.cli import main, print_main

FIXTURE_DIRECTORY = Path(__file__).resolve().parents[1] / 'files' / 'fastapi'
FEATURES_FIXTURE_DIRECTORY = Path(__file__).resolve().parents[1] / 'files' / 'fastapi_features'

DOCUMENTED_CONFIGURATION = """[tool.deadcode]
ignore-names-if-decorated-with = ["@app.*", "@router.*"]
ignore-bodies-if-inherits-from = ["BaseModel"]
"""

FEATURES_CONFIGURATION = """[tool.deadcode]
ignore-names-if-decorated-with = ["@app.*", "@router.*", "@admin_router.*"]
ignore-names = ["dispatch"]
ignore-bodies-if-inherits-from = ["BaseModel"]
"""

FINDING_PATTERN = re.compile(r'^(?P<path>.+):\d+:\d+: (?P<code>DC\d+) \w+ `(?P<name>[^`]+)` is never used$')


def _copy_fixture(tmp_path: Path, fixture_directory: Path = FIXTURE_DIRECTORY) -> None:
    shutil.copytree(fixture_directory, tmp_path / 'project')


def _findings(output: str | None) -> set[tuple[str, str, str]]:
    assert output is not None
    findings = set()
    for line in output.splitlines():
        match = FINDING_PATTERN.match(line)
        assert match is not None, line
        findings.add((match.group('path'), match.group('code'), match.group('name')))
    return findings


def test_fastapi_fixture_without_configuration(project_directory: Path) -> None:
    # Having
    _copy_fixture(project_directory)

    # Then
    # The findings cascade: `on_startup` is dead and is the only caller of
    # `log_startup`, whose body is the only user of `SETTING`; `read_me` is dead
    # and is the only user of the `User` import; `read_user` is dead and its
    # default argument is the only user of `get_current_user` and both `Depends`
    # imports.
    assert main(['project', '--no-color']) == (
        'project/dependencies.py:1:20: DC07 Import `Depends` is never used'
        '\nproject/dependencies.py:4:0: DC02 Function `get_current_user` is never used'
        '\nproject/dependencies.py:8:0: DC02 Function `unused_dependency` is never used'
        '\nproject/main.py:3:19: DC07 Import `User` is never used'
        '\nproject/main.py:9:0: DC01 Variable `SETTING` is never used'
        '\nproject/main.py:12:0: DC02 Function `log_startup` is never used'
        '\nproject/main.py:24:0: DC02 Function `on_startup` is never used'
        '\nproject/main.py:29:0: DC02 Function `read_me` is never used'
        '\nproject/main.py:33:0: DC01 Variable `UNUSED_SETTING` is never used'
        '\nproject/main.py:36:0: DC02 Function `unused_handler` is never used'
        '\nproject/models.py:5:4: DC06 Name `name` is never used'
        '\nproject/models.py:6:4: DC06 Name `email` is never used'
        '\nproject/models.py:9:0: DC03 Class `UnusedModel` is never used'
        '\nproject/models.py:10:4: DC06 Name `value` is never used'
        '\nproject/routes/users.py:1:31: DC07 Import `Depends` is never used'
        '\nproject/routes/users.py:3:25: DC07 Import `get_current_user` is never used'
        '\nproject/routes/users.py:10:0: DC02 Function `read_user` is never used'
        '\nproject/routes/users.py:15:0: DC02 Function `create_user` is never used'
        '\nproject/routes/users.py:19:0: DC02 Function `dead_route_helper` is never used'
    )

    # When
    result = print_main(['project', '--no-color'])

    # Then
    assert result == 1


def test_fastapi_fixture_with_documented_configuration(project_directory: Path) -> None:
    # Having
    _copy_fixture(project_directory)
    (project_directory / 'pyproject.toml').write_text(DOCUMENTED_CONFIGURATION)

    # Then
    assert main(['project', '--no-color']) == (
        'project/dependencies.py:8:0: DC02 Function `unused_dependency` is never used'
        '\nproject/main.py:33:0: DC01 Variable `UNUSED_SETTING` is never used'
        '\nproject/main.py:36:0: DC02 Function `unused_handler` is never used'
        '\nproject/models.py:9:0: DC03 Class `UnusedModel` is never used'
        '\nproject/routes/users.py:19:0: DC02 Function `dead_route_helper` is never used'
    )

    # When
    result = print_main(['project', '--no-color'])

    # Then
    assert result == 1


def test_fastapi_common_use_cases_with_documented_configuration(project_directory: Path) -> None:
    # Having
    _copy_fixture(project_directory, FEATURES_FIXTURE_DIRECTORY)
    (project_directory / 'pyproject.toml').write_text(FEATURES_CONFIGURATION)

    # Then
    # The `Item` import is a cascade finding: `unused_handler` is dead and its
    # parameter annotation is the import's only usage.
    assert _findings(main(['project', '--no-color'])) == {
        ('project/errors.py', 'DC03', 'UnusedError'),
        ('project/main.py', 'DC02', 'current_user_name'),
        ('project/main.py', 'DC02', 'unused_handler'),
        ('project/main.py', 'DC07', 'Item'),
        ('project/models.py', 'DC03', 'UnusedModel'),
        ('project/routes/items.py', 'DC02', 'dead_route_helper'),
    }

    # When
    result = print_main(['project', '--no-color'])

    # Then
    assert result == 1
