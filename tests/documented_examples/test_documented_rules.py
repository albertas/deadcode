import re
from pathlib import Path

import pytest

from deadcode.cli import main
from deadcode.constants import ERROR_TYPE_TO_ERROR_CODE

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
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
    'DC06': (b'class Foo:\n    bar = 1\n', ('DC06 Name',), ('DC01',)),
    'DC07': (b'import os\n', ('DC07 Import',), ()),
    'DC08': (
        b'class Foo:\n    @property\n    def bar(self):\n        return 1\n\ninstance = Foo()\nprint(instance)\n',
        ('DC08 Property',),
        (),
    ),
    'DC09': (
        b'if True:\n    print("main")\nelse:\n    print("unreachable")\n',
        ('DC09 Unreachable `else` block',),
        ('DC13',),
    ),
    'DC11': (b'\n                ', ('DC11 Empty file',), ('DC03',)),
    'DC12': (b'# print("Hello world")\n', ('DC12 Commented out code',), ('DC11',)),
    'DC13': (
        b'def foo():\n    return 1\n    print("unreachable")\n',
        ("DC13 unreachable code after 'return'",),
        ('DC09',),
    ),
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
    # Having
    file_content, must_contain, must_not_contain = RULE_CASES[code]
    virtual_file_system.files = {'sample.py': file_content}

    # When
    output = main(['sample.py', '--no-color'])

    # Then
    assert isinstance(output, str)
    for fragment in must_contain:
        assert fragment in output
    for fragment in must_not_contain:
        assert fragment not in output


def test_rule_cases_match_readme_table():
    # Then
    assert set(RULE_CASES) == documented_rule_codes()


def test_every_error_code_is_unique():
    # When
    error_codes = list(ERROR_TYPE_TO_ERROR_CODE.values())

    # Then
    assert len(set(error_codes)) == len(error_codes)
