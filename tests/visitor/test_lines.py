import ast
from unittest import TestCase

from deadcode.visitor.lines import get_first_line_number, get_last_line_number


class TestLineNumbers(TestCase):
    def test_first_line_number_uses_first_decorator(self):
        node = ast.parse('@deco\ndef f():\n    pass').body[0]
        assert get_first_line_number(node) == 1  # lines 79-81

    def test_last_line_number_handles_children_without_lineno(self):
        # comprehension nodes lack lineno -> AttributeError branch (lines 64-65)
        node = ast.parse('[x for x in y]', mode='eval').body
        assert isinstance(get_last_line_number(node), int)
