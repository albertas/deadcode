import re
from pathlib import Path

import pytest

from deadcode.cli import main

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
README_PATH = REPOSITORY_ROOT / 'README.md'

RULE_CASES: dict[str, tuple[bytes, tuple[str, ...], tuple[str, ...]]] = {
    'DC01': (b'unused_variable = 1\n', ('DC01 Variable',), ()),
    'DC02': (b'def unused_function():\n    pass\n', ('DC02 Function',), ()),
    'DC03': (b'class UnusedClass:\n    pass\n', ('DC03 Class',), ()),
    'DC04': (
        b'class Foo:\n    def bar(self):\n        pass\n\ninstance = Foo()\nprint(instance)\n',
        ('DC04 Method',),
        (),
    ),
    'DC05': (
        b'class Foo:\n    def __init__(self):\n        self.bar = 1\n\ninstance = Foo()\nprint(instance)\n',
        ('DC05 Attribute',),
        (),
    ),
    'DC07': (b'import os\n', ('DC07 Import',), ()),
    'DC08': (
        b'class Foo:\n    @property\n    def bar(self):\n        return 1\n\ninstance = Foo()\nprint(instance)\n',
        ('DC08 Property',),
        (),
    ),
    'DC11': (b'\n                ', ('DC11 Empty file',), ('DC03',)),
    'DC': (
        b'class Foo:  # noqa: DC\n    pass\n\nunused_variable = 1\n',
        ('DC01 Variable',),
        ('DC03',),
    ),
}


def readme_rules_section() -> str:
    readme_text = README_PATH.read_text(encoding='utf-8')
    rules_start = readme_text.index('## Rules')
    rules_end = readme_text.index('## Ignoring checks with noqa comments')
    return readme_text[rules_start:rules_end]


def documented_rule_codes() -> set[str]:
    return set(re.findall(r'^\| (DC\d*)\s*\|', readme_rules_section(), re.MULTILINE))


@pytest.mark.parametrize('code', sorted(RULE_CASES))
def test_documented_rule_is_emitted(code, virtual_file_system):
    file_content, must_contain, must_not_contain = RULE_CASES[code]
    virtual_file_system.files = {'sample.py': file_content}

    output = main(['sample.py', '--no-color'])

    assert isinstance(output, str)
    for fragment in must_contain:
        assert fragment in output
    for fragment in must_not_contain:
        assert fragment not in output


def test_rule_cases_match_readme_table():
    assert set(RULE_CASES) == documented_rule_codes()


def test_planned_rule_codes_are_listed_outside_the_table():
    rules_section = readme_rules_section()
    text_after_table = rules_section[rules_section.index('| DC    |') :]

    for planned_code in ('DC06', 'DC09', 'DC12', 'DC13'):
        assert planned_code in text_after_table
        assert planned_code not in documented_rule_codes()
