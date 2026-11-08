import shutil

from pathlib import Path

import pytest

from deadcode.cli import main, print_main

FIXTURE_DIRECTORY = Path(__file__).parent / 'files' / 'fastapi'

DOCUMENTED_CONFIGURATION = """[tool.deadcode]
ignore-names-if-decorated-with = ["@app.*", "@router.*"]
ignore-bodies-if-inherits-from = ["BaseModel"]
"""


def _copy_fixture(tmp_path: Path) -> None:
    shutil.copytree(FIXTURE_DIRECTORY, tmp_path / 'project')


@pytest.fixture()
def project_directory(tmp_path, monkeypatch) -> Path:
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_fastapi_fixture_without_configuration(project_directory: Path) -> None:
    _copy_fixture(project_directory)

    assert main(['project', '--no-color']) == (
        'project/dependencies.py:8:0: DC02 Function `unused_dependency` is never used'
        '\nproject/main.py:24:0: DC02 Function `on_startup` is never used'
        '\nproject/main.py:29:0: DC02 Function `read_me` is never used'
        '\nproject/main.py:33:0: DC01 Variable `UNUSED_SETTING` is never used'
        '\nproject/main.py:36:0: DC02 Function `unused_handler` is never used'
        '\nproject/models.py:5:4: DC01 Variable `name` is never used'
        '\nproject/models.py:6:4: DC01 Variable `email` is never used'
        '\nproject/models.py:9:0: DC03 Class `UnusedModel` is never used'
        '\nproject/models.py:10:4: DC01 Variable `value` is never used'
        '\nproject/routes/users.py:10:0: DC02 Function `read_user` is never used'
        '\nproject/routes/users.py:15:0: DC02 Function `create_user` is never used'
        '\nproject/routes/users.py:19:0: DC02 Function `dead_route_helper` is never used'
    )
    assert print_main(['project', '--no-color']) == 1


def test_fastapi_fixture_with_documented_configuration(project_directory: Path) -> None:
    _copy_fixture(project_directory)
    (project_directory / 'pyproject.toml').write_text(DOCUMENTED_CONFIGURATION)

    assert main(['project', '--no-color']) == (
        'project/dependencies.py:8:0: DC02 Function `unused_dependency` is never used'
        '\nproject/main.py:33:0: DC01 Variable `UNUSED_SETTING` is never used'
        '\nproject/main.py:36:0: DC02 Function `unused_handler` is never used'
        '\nproject/models.py:9:0: DC03 Class `UnusedModel` is never used'
        '\nproject/routes/users.py:19:0: DC02 Function `dead_route_helper` is never used'
    )
    assert print_main(['project', '--no-color']) == 1
