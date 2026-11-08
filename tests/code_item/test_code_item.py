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


def test_code_item_scoped_name_includes_the_scope():
    # Having
    code_item = CodeItem(name='bar', type_='method', filename=Path('foo.py'), scope='foo.Foo')

    # When
    scoped_name = code_item.scoped_name

    # Then
    assert scoped_name == 'foo.Foo.bar'


def test_code_item_repr_is_the_repr_of_its_name():
    # Having
    code_item = CodeItem(name='Foo', type_='variable', filename=Path('foo.py'))

    # When
    representation = repr(code_item)

    # Then
    assert representation == repr('Foo')


def test_code_item_is_not_equal_to_an_unrelated_object():
    # Having
    code_item = CodeItem(name='Foo', type_='variable', filename=Path('foo.py'))

    # When
    compared_to_object = code_item == object()
    compared_to_integer = code_item == 42

    # Then
    assert compared_to_object is False
    assert compared_to_integer is False
