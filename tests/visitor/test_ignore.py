import pytest

from deadcode.visitor.ignore import _match


@pytest.mark.parametrize(
    ('name', 'pattern'),
    [
        ('tests\\test_a.py', 'tests/*'),
        ('tests/test_a.py', 'tests\\*'),
        ('tests\\test_a.py', 'tests\\*'),
    ],
)
def test_match_normalizes_separators_in_name_and_pattern(name: str, pattern: str):
    assert _match(name, [pattern]) is True


def test_match_normalizes_separators_when_case_is_insensitive():
    assert _match('tests\\test_a.py', ['tests/*'], case=False) is True
    assert _match('tests/test_a.py', ['tests\\*'], case=False) is True


def test_match_without_separators_matches_identifier():
    assert _match('some_name', ['some_*']) is True


def test_match_returns_false_for_non_matching_path():
    assert _match('tests/test_a.py', ['other/*']) is False
