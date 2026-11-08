import ast

import pytest

from deadcode.visitor.utils import get_decorator_name


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
    decorator = ast.parse(f'{source}\ndef function():\n    pass\n').body[0].decorator_list[0]
    assert get_decorator_name(decorator) == expected_name
