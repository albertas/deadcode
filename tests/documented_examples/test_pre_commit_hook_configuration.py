import re

from pathlib import Path

import yaml

import deadcode

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
HOOKS_PATH = REPOSITORY_ROOT / '.pre-commit-hooks.yaml'
README_PATH = REPOSITORY_ROOT / 'README.md'

REPOSITORY_URL = 'https://github.com/albertas/deadcode'


def load_hook_definition() -> dict:
    hooks = yaml.safe_load(HOOKS_PATH.read_text(encoding='utf-8'))
    return hooks[0]


def load_readme_pre_commit_configuration() -> dict:
    readme_text = README_PATH.read_text(encoding='utf-8')
    section_start = readme_text.index('## Pre-commit hook')
    section_end = readme_text.index('## Command line options', section_start)
    section = readme_text[section_start:section_end]
    snippet = re.search(r'```[a-zA-Z]*\n(.*?)```', section, flags=re.DOTALL)
    assert snippet is not None
    return yaml.safe_load(snippet.group(1))


def test_hook_entry_point_configuration():
    # When
    hook = load_hook_definition()

    # Then
    assert hook['id'] == 'deadcode'
    assert hook['entry'] == 'deadcode'
    assert hook['language'] == 'python'
    assert hook['types'] == ['python']


def test_hook_execution_configuration():
    # When
    hook = load_hook_definition()

    # Then
    assert hook['exclude'] == '^tests/'
    assert hook['require_serial'] is True
    assert hook['minimum_pre_commit_version'] == '2.9.2'


def test_readme_snippet_uses_repository_and_hook_id():
    # When
    repository = load_readme_pre_commit_configuration()['repos'][0]

    # Then
    assert repository['repo'] == REPOSITORY_URL
    assert repository['hooks'][0]['id'] == 'deadcode'


def test_readme_snippet_pins_the_current_version():
    # When
    repository = load_readme_pre_commit_configuration()['repos'][0]

    # Then
    assert repository['rev'] == f'v{deadcode.__version__}'
