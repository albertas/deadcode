from pathlib import Path
from unittest import TestCase

from deadcode.utils.nested_scopes import NestedScope
from deadcode.visitor.code_item import CodeItem


class TestNestedScope(TestCase):
    def test_add_ignores_code_item_without_scope(self):
        scope = NestedScope()
        item = CodeItem(name='x', type_='variable', filename=Path('f.py'))  # scope defaults to None
        assert scope.add(item) is None  # lines 23-24
