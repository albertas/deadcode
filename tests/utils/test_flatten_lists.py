from unittest import TestCase

from deadcode.utils.flatten_lists import flatten_list, flatten_lists_of_comma_separated_values


class TestFlattenLists(TestCase):
    def test_flatten_list_of_none_is_empty(self):
        assert flatten_list(None) == []  # line 17-18

    def test_flatten_list_concatenates(self):
        assert flatten_list([['a'], ['b', 'c']]) == ['a', 'b', 'c']

    def test_flatten_comma_separated(self):
        assert flatten_lists_of_comma_separated_values([['a,b']]) == ['a', 'b']
