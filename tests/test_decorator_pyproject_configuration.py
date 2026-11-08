from pathlib import Path

import pytest

from deadcode.cli import main, print_main

NAMES_CONFIGURATION = '[tool.deadcode]\nexclude = [".venv"]\nignore-names-if-decorated-with = ["@app.route"]\n'
BODIES_CONFIGURATION = '[tool.deadcode]\nexclude = [".venv"]\nignore-bodies-if-decorated-with = ["@app.route"]\n'
DEFINITIONS_CONFIGURATION = (
    '[tool.deadcode]\nexclude = [".venv"]\nignore-definitions-if-decorated-with = ["@app.route"]\n'
)

DECORATED_SOURCE = """@app.route("/", methods=["POST"])
def post_tax_adder_customer():
    pass


def unused_helper():
    pass
"""

NESTED_SOURCE = """@app.route("/", methods=["POST"])
def post_tax_adder_customer():
    def body_helper():
        pass


def unused_helper():
    pass
"""

NON_MATCHING_SOURCE = """@app.get("/")
def get_customer():
    pass
"""


def write_project(directory: Path, configuration: str, source: str) -> None:
    (directory / 'pyproject.toml').write_text(configuration, encoding='utf-8')
    (directory / 'service.py').write_text(source, encoding='utf-8')


@pytest.fixture()
def project_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_ignore_names_if_decorated_with_from_pyproject_toml(project_directory: Path) -> None:
    # Having
    write_project(project_directory, NAMES_CONFIGURATION, DECORATED_SOURCE)

    # When
    output = main(['service.py', '--no-color'])

    # Then
    assert output == 'service.py:6:0: DC02 Function `unused_helper` is never used'
    assert 'post_tax_adder_customer' not in output

    # When
    result = print_main(['service.py', '--no-color'])

    # Then
    assert result == 1


def test_ignore_bodies_if_decorated_with_from_pyproject_toml(project_directory: Path) -> None:
    # Having
    write_project(project_directory, BODIES_CONFIGURATION, NESTED_SOURCE)

    # When
    output = main(['service.py', '--no-color'])

    # Then
    assert output == (
        'service.py:2:0: DC02 Function `post_tax_adder_customer` is never used'
        '\nservice.py:7:0: DC02 Function `unused_helper` is never used'
    )
    assert 'body_helper' not in output

    # When
    result = print_main(['service.py', '--no-color'])

    # Then
    assert result == 1


def test_ignore_definitions_if_decorated_with_from_pyproject_toml(project_directory: Path) -> None:
    # Having
    write_project(project_directory, DEFINITIONS_CONFIGURATION, NESTED_SOURCE)

    # When
    output = main(['service.py', '--no-color'])

    # Then
    assert output == 'service.py:7:0: DC02 Function `unused_helper` is never used'
    assert 'post_tax_adder_customer' not in output
    assert 'body_helper' not in output

    # When
    result = print_main(['service.py', '--no-color'])

    # Then
    assert result == 1


def test_non_matching_decorator_is_still_reported(project_directory: Path) -> None:
    # Having
    write_project(project_directory, NAMES_CONFIGURATION, NON_MATCHING_SOURCE)

    # When
    output = main(['service.py', '--no-color'])

    # Then
    assert output is not None
    assert 'Function `get_customer` is never used' in output

    # When
    result = print_main(['service.py', '--no-color'])

    # Then
    assert result == 1
