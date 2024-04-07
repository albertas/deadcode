from deadcode.actions.merge_overlaping_file_parts import merge_overlaping_file_parts, does_overlap, merge_parts
from deadcode.utils.base_test_case import BaseTestCase


class TestMergeOverlapingFileParts(BaseTestCase):
    def test_no_overlaping_parts(self):
        overlaping_file_parts = [
            # Line, line_end, col, col_end
            (1, 0, 2, 6),
            (3, 0, 5, 6),
        ]
        expected_result = overlaping_file_parts
        non_overlaping_file_parts = merge_overlaping_file_parts(overlaping_file_parts)
        self.assertEqual(non_overlaping_file_parts, expected_result)

    def test_overlaping_lines(self):
        overlaping_file_parts = [
            # Line, line_end, col, col_end
            (1, 2, 0, 6),
            (2, 5, 0, 6),
        ]
        expected_result = [(1, 5, 0, 6)]

        non_overlaping_file_parts = merge_overlaping_file_parts(overlaping_file_parts)

        self.assertEqual(non_overlaping_file_parts, expected_result)


class TestDoesOverlap(BaseTestCase):
    def test_does_overlap(self):
        # # Contains
        self.assertTrue(does_overlap((3, 5, 0, 6), (1, 7, 0, 6)))
        self.assertTrue(does_overlap((1, 7, 0, 6), (3, 5, 0, 6)))

        # # Overlaps
        self.assertTrue(does_overlap((1, 5, 0, 6), (2, 7, 0, 6)))
        self.assertTrue(does_overlap((2, 7, 0, 6), (1, 5, 0, 6)))

        # # Same
        self.assertTrue(does_overlap((2, 7, 0, 6), (2, 7, 0, 6)))

        # Does not overlap
        self.assertFalse(does_overlap((4, 7, 0, 6), (1, 3, 0, 6)))
        self.assertFalse(does_overlap((1, 3, 0, 6), (4, 7, 0, 6)))


class TestMergeParts(BaseTestCase):
    def test_merge_parts(self):
        # # Contains
        self.assertEqual(merge_parts((3, 5, 0, 6), (1, 7, 0, 6)), (1, 7, 0, 6))
        self.assertEqual(merge_parts((1, 7, 0, 6), (3, 5, 0, 6)), (1, 7, 0, 6))

        # # Overlape
        self.assertEqual(merge_parts((1, 5, 0, 6), (2, 7, 0, 6)), (1, 7, 0, 6))
        self.assertEqual(merge_parts((2, 7, 0, 6), (1, 5, 0, 6)), (1, 7, 0, 6))

        # # Same
        self.assertEqual(merge_parts((2, 7, 0, 6), (2, 7, 0, 6)), (2, 7, 0, 6))

        # Does not overlap
        self.assertEqual(merge_parts((4, 7, 0, 6), (1, 3, 0, 6)), None)
        self.assertEqual(merge_parts((1, 3, 0, 6), (4, 7, 0, 6)), None)
