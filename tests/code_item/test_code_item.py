from pathlib import Path

from deadcode.visitor.code_item import CodeItem


def test_code_item_comparison_with_a_string():
    # When
    code_item = CodeItem(name='Foo', type_='variable', filename=Path('foo.py'))

    # Then
    assert code_item == 'Foo'


def test_code_item_retrieval_from_dictionary_by_its_name():
    # Having
    dictionary = {}

    # When
    code_item = CodeItem(name='Foo', type_='variable', filename=Path('foo.py'))
    dictionary[code_item] = 'Some value'

    # Then
    assert dictionary['Foo'] == 'Some value'
