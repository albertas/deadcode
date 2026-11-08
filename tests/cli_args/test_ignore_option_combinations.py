from unittest.mock import MagicMock

import pytest

from deadcode.cli import main


@pytest.fixture
def pyproject_config_mock(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    mock = MagicMock(
        return_value={
            'tool': {
                'deadcode': {
                    'ignore_definitions': ['ConfigIgnored'],
                }
            }
        }
    )
    monkeypatch.setattr('deadcode.actions.parse_arguments.tomllib.load', mock)
    return mock


def test_two_options_match_the_same_item(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                @deco
                class Decorated:
                    value = 1

                    def method(self):
                        return 2
                """
    }

    # When
    unused_names = main(
        [
            'foo.py',
            '--no-color',
            '--ignore-definitions-if-decorated-with=@deco',
            '--ignore-bodies-of=Decorated',
        ]
    )

    # Then
    assert unused_names is None


def test_body_option_nested_inside_definitions_option_changes_nothing(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                class Outer:
                    class Inner:
                        value = 1


                class Reported:
                    pass
                """
    }

    # When
    outer_only = main(['foo.py', '--no-color', '--ignore-definitions=Outer'])
    outer_and_inner = main(['foo.py', '--no-color', '--ignore-definitions=Outer', '--ignore-bodies-of=Inner'])

    # Then
    assert outer_only == ('foo.py:6:0: DC03 Class `Reported` is never used')
    assert outer_and_inner == outer_only


def test_pyproject_config_and_command_line_values_are_united(virtual_file_system, pyproject_config_mock):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                class ConfigIgnored:
                    pass


                class CommandLineIgnored:
                    pass
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--ignore-definitions=CommandLineIgnored'])

    # Then
    assert unused_names is None


def test_fix_and_dry_make_no_change_for_ignored_definition(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                class IgnoredClass:
                    value = 1
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--ignore-definitions=IgnoredClass', '--fix', '--dry'])

    # Then
    assert unused_names is None
    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                class IgnoredClass:
                    value = 1
                """
        }
    )
