import ast

import pytest

from deadcode.visitor.utils import (
    condition_is_always_false,
    condition_is_always_true,
    get_base_class_names,
    get_decorator_name,
)


@pytest.mark.parametrize(
    ('source', 'expected_name'),
    [
        ('@deco', '@deco'),
        ('@mod.deco', '@mod.deco'),
        ('@a.b.c', '@a.b.c'),
        ('@deco()', '@deco'),
        ('@app.get("/x")', '@app.get'),
        ('@a.b.c.get(1)', '@a.b.c.get'),
        ('@factory()()', '@factory'),
        ('@a.factory()()', '@a.factory'),
        ('@Class().function()', '@Class.function'),
        ('@Class().function', '@Class.function'),
        ('@decorators[0]', '@decorators[0]'),
        ('@a.b[0]', '@a.b[0]'),
        ('@getattr(x, "y")', '@getattr'),
        ('@(lambda f: f)', '@lambda f: f'),
        ('@property', '@property'),
    ],
)
def test_get_decorator_name(source: str, expected_name: str) -> None:
    # When
    decorator = ast.parse(f'{source}\ndef function():\n    pass\n').body[0].decorator_list[0]

    # Then
    assert get_decorator_name(decorator) == expected_name


@pytest.mark.parametrize(
    ('source', 'expected_true', 'expected_false'),
    [
        ('True and True', True, False),
        ('True or False', True, False),
        ('False and True', False, True),
        ('False or False', False, True),
    ],
)
def test_bool_operator_conditions_are_evaluated(source: str, expected_true: bool, expected_false: bool) -> None:
    # Having
    condition = ast.parse(source, mode='eval').body

    # When
    is_always_true = condition_is_always_true(condition)
    is_always_false = condition_is_always_false(condition)

    # Then
    assert is_always_true is expected_true
    assert is_always_false is expected_false


@pytest.mark.parametrize('base', ['factory()', 'Generic[int]'])
def test_get_base_class_names_returns_empty_list_for_non_name_bases(base: str) -> None:
    # Having
    node = ast.parse(f'class A({base}):\n    pass\n').body[0].bases[0]

    # When
    names = get_base_class_names(node)

    # Then
    assert names == []
