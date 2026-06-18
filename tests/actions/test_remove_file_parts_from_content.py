from deadcode.actions.remove_file_parts_from_content import remove_file_parts_from_content
from deadcode.utils.base_test_case import BaseTestCase
from deadcode.data_types import Part


class TestRemoveFilePartsFromCont(BaseTestCase):
    def test_no_overlaping_parts_from_content(self):
        unused_file_parts = [
            Part(1, 1, 18, 23),
            Part(1, 1, 27, 40),
        ]

        content_lines = ["from file1 import foo, eggs, bar as spam"]
        expected_content_lines = ["from file1 import eggs"]

        updated_content_lines = remove_file_parts_from_content(content_lines, unused_file_parts)
        self.assertEqual(updated_content_lines, expected_content_lines)
