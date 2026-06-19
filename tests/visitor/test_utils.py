import ast
from pathlib import Path
from unittest import TestCase

from deadcode.visitor.utils import (
    _safe_eval,
    get_decorator_name,
    LoggingList,
    LoggingSet,
)
from deadcode.visitor.code_item import CodeItem


def _expr(source):
    return ast.parse(source, mode='eval').body


class TestSafeEval(TestCase):
    def test_boolop_and(self):
        assert _safe_eval(_expr('True and False'), True) is False  # lines 23-25

    def test_boolop_or(self):
        assert _safe_eval(_expr('False or True'), False) is True  # lines 23-24, 27

    def test_unary_not(self):
        assert _safe_eval(_expr('not False'), True) is True  # lines 28-29

    def test_unevaluatable_name_returns_default(self):
        assert _safe_eval(_expr('undefined_name'), True) is True  # literal_eval ValueError -> line 34/35


class TestGetDecoratorName(TestCase):
    def _decorator(self, source):
        return ast.parse(source).body[0].decorator_list[0]

    def test_plain_name(self):
        assert get_decorator_name(self._decorator('@deco\ndef f(): pass')) == '@deco'

    def test_attribute_chain(self):
        assert get_decorator_name(self._decorator('@a.b.c\ndef f(): pass')) == '@a.b.c'  # lines 58-62

    def test_call_decorator(self):
        assert get_decorator_name(self._decorator('@deco(1)\ndef f(): pass')) == '@deco'  # lines 55-56


class TestLoggingCollections(TestCase):
    def test_logging_list_append_in_verbose_mode(self):
        collection = LoggingList('function', verbose=True)
        collection.append(CodeItem(name='x', type_='function', filename=Path('f.py')))  # line 73
        assert collection == ['x']

    def test_logging_set_add_in_verbose_mode(self):
        names = LoggingSet('name', verbose=True)
        names.add('x')  # line 85
        assert 'x' in names
