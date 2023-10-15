from pathlib import Path
from unittest import TestCase

from deadcode.visitor.code_item import CodeItem


class TestCodeItem(TestCase):
    def test_code_item_comparison_with_a_string(self):
        code_item = CodeItem(name="Foo", type_="variable", filename=Path("foo.py"))
        self.assertEqual("Foo", code_item)

    def test_code_item_retrieval_from_dictionary_by_its_name(self):
        dictionary = {}
        code_item = CodeItem(name="Foo", type_="variable", filename=Path("foo.py"))
        dictionary[code_item] = "Some value"
        self.assertEqual(dictionary["Foo"], "Some value")
