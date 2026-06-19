from deadcode.actions.remove_file_parts_from_content import (
    remove_file_parts_from_content,
    remove_as_from_end,
    remove_comma_from_begining,
    get_code_parts_for_the_same_line,
)
from deadcode.utils.base_test_case import BaseTestCase
from deadcode.data_types import Part


class TestRemoveFilePartsFromCont(BaseTestCase):
    def test_no_overlaping_parts_from_content(self):
        unused_file_parts = [
            Part(1, 1, 18, 23),
            Part(1, 1, 27, 40),
        ]

        content_lines = ['from file1 import foo, eggs, bar as spam']
        expected_content_lines = ['from file1 import eggs']

        updated_content_lines = remove_file_parts_from_content(content_lines, unused_file_parts)
        self.assertEqual(updated_content_lines, expected_content_lines)


class TestRemoveAsFromEnd(BaseTestCase):
    def test_line_not_ending_with_as_is_returned_unchanged(self):
        assert remove_as_from_end('from a import b') == 'from a import b'

    def test_as_with_preceding_whitespace_is_stripped(self):
        assert remove_as_from_end('import foo as') == 'import foo'

    def test_word_ending_in_as_without_space_is_kept(self):
        assert remove_as_from_end('alias') == 'alias'


class TestRemoveCommaFromBegining(BaseTestCase):
    def test_line_without_leading_comma_is_returned_unchanged(self):
        assert remove_comma_from_begining('foo') == 'foo'

    def test_leading_comma_and_surrounding_space_are_removed(self):
        assert remove_comma_from_begining(', foo') == 'foo'


class TestGetCodePartsForTheSameLine(BaseTestCase):
    def test_collects_parts_ending_on_same_line_in_reverse_until_break(self):
        parts = [
            (3, 3, 0, 5, None, None),
            (3, 3, 6, 9, None, None),
            (4, 4, 0, 2, None, None),  # different line -> break
        ]
        result = get_code_parts_for_the_same_line(parts, 0)
        assert result == [(3, 3, 6, 9, None, None), (3, 3, 0, 5, None, None)]
