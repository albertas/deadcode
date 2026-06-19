from pathlib import Path
from unittest import TestCase

from deadcode.visitor.code_item import CodeItem


class TestCodeItem(TestCase):
    def test_code_item_comparison_with_a_string(self):
        code_item = CodeItem(name='Foo', type_='variable', filename=Path('foo.py'))
        self.assertEqual('Foo', code_item)

    def test_code_item_retrieval_from_dictionary_by_its_name(self):
        dictionary = {}
        code_item = CodeItem(name='Foo', type_='variable', filename=Path('foo.py'))
        dictionary[code_item] = 'Some value'
        self.assertEqual(dictionary['Foo'], 'Some value')

    def test_scoped_name(self):
        code_item = CodeItem(name='bar', type_='variable', filename=Path('f.py'), scope='mod.Foo')
        self.assertEqual(code_item.scoped_name, 'mod.Foo.bar')  # line 91

    def test_repr_is_the_name(self):
        code_item = CodeItem(name='bar', type_='variable', filename=Path('f.py'))
        self.assertEqual(repr(code_item), "'bar'")  # line 129

    def test_eq_with_unrelated_type_is_false(self):
        code_item = CodeItem(name='bar', type_='variable', filename=Path('f.py'))
        self.assertNotEqual(code_item, 123)  # line 137 (returns False)
