import ast

import pytest

from deadcode.visitor.utils import get_decorator_name


def _decorator_node(source: str) -> ast.AST:
    return ast.parse(f'{source}\ndef function():\n    pass\n').body[0].decorator_list[0]


class TestUtils:
    @pytest.mark.parametrize(
        ('source', 'expected'),
        [
            ('@deco', '@deco'),
            ('@app.get', '@app.get'),
            ('@a.b.c.get', '@a.b.c.get'),
            ('@app.get("/x")', '@app.get'),
            ('@Class().function()', '@function'),
        ],
    )
    def test_get_decorator_name(self, source, expected):
        assert get_decorator_name(_decorator_node(source)) == expected
