from deadcode.actions.merge_overlaping_file_parts import (
    merge_overlaping_file_parts,
    does_overlap,
    merge_parts,
    does_include,
)
from deadcode.utils.base_test_case import BaseTestCase


class TestMergeOverlapingFileParts(BaseTestCase):
    def test_no_overlaping_parts(self):
        overlaping_file_parts = [
            # Line, line_end, col, col_end
            (1, 0, 2, 6, None, None),
            (3, 0, 5, 6, None, None),
        ]
        expected_result = overlaping_file_parts
        non_overlaping_file_parts = merge_overlaping_file_parts(overlaping_file_parts)
        self.assertEqual(non_overlaping_file_parts, expected_result)

    def test_overlaping_lines(self):
        overlaping_file_parts = [
            # Line, line_end, col, col_end
            (1, 2, 0, 6, None, None),
            (2, 5, 0, 6, None, None),
        ]
        expected_result = [(1, 5, 0, 6, None, None)]

        non_overlaping_file_parts = merge_overlaping_file_parts(overlaping_file_parts)

        self.assertEqual(non_overlaping_file_parts, expected_result)

    def test_overlaping_parts_in_the_same_line(self):
        # TODO: fix this test.
        overlaping_file_parts = [
            (1, 1, 18, 21, None, None),
            (1, 1, 29, 40, None, None),
            (1, 1, 18, 23, None, None),
            (1, 1, 27, 40, None, None),
        ]

        expected_result = [
            (1, 1, 18, 23, None, None),
            (1, 1, 27, 40, None, None),
        ]

        non_overlaping_file_parts = merge_overlaping_file_parts(overlaping_file_parts)

        self.assertEqual(non_overlaping_file_parts, expected_result)

    # TODO: generate tests with all the combinations for same and different lines.

    # TODO: swap line_end with col_start to be able to simply sort and get correct ordering by start position.
    def test_merge_overlaping_file_parts_with_multiple_parts_on_the_same_line(self):
        parts = [
            (1, 3, 17, 4, None, None),
            (2, 2, 4, 20, None, None),
            (3, 5, 20, 2, None, None),
            (4, 4, 4, 22, None, None),
        ]
        expected_merged_parts = [
            # (1, 3, 17, 4),
            # (4, 4, 4, 22),
            (1, 3, 17, 4, None, None),
            (3, 5, 20, 2, None, None),
        ]
        self.assertEqual(merge_overlaping_file_parts(parts), expected_merged_parts)

        # # Order input differently
        # parts = [
        #     (2, 2, 4, 20),
        #     (4, 4, 4, 22),
        #     (1, 3, 17, 4),
        #     (3, 5, 20, 2),
        # ]
        # expected_merged_parts = [
        #     (1, 3, 17, 4),
        #     (4, 4, 4, 22),
        # ]
        # self.assertEqual(
        #     merge_overlaping_file_parts(parts),
        #     expected_merged_parts
        # )


class TestDoesOverlap(BaseTestCase):
    def test_does_overlap(self):
        # # Contains
        self.assertTrue(does_overlap((3, 5, 0, 6, None, None), (1, 7, 0, 6, None, None)))
        self.assertTrue(does_overlap((1, 7, 0, 6, None, None), (3, 5, 0, 6, None, None)))

        # # Overlaps
        self.assertTrue(does_overlap((1, 5, 0, 6, None, None), (2, 7, 0, 6, None, None)))
        self.assertTrue(does_overlap((2, 7, 0, 6, None, None), (1, 5, 0, 6, None, None)))

        # # Same
        self.assertTrue(does_overlap((2, 7, 0, 6, None, None), (2, 7, 0, 6, None, None)))

        # Does not overlap
        self.assertFalse(does_overlap((4, 7, 0, 6, None, None), (1, 3, 0, 6, None, None)))
        self.assertFalse(does_overlap((1, 3, 0, 6, None, None), (4, 7, 0, 6, None, None)))

        # # Same with code to insert
        self.assertTrue(does_overlap((2, 7, 0, 6, 'pass', None), (2, 7, 0, 6, None, None)))


class TestMergeParts(BaseTestCase):
    def test_merge_parts(self):
        # # Contains
        self.assertEqual(merge_parts((3, 5, 0, 6, None, None), (1, 7, 0, 6, None, None)), (1, 7, 0, 6, None, None))
        self.assertEqual(merge_parts((1, 7, 0, 6, None, None), (3, 5, 0, 6, None, None)), (1, 7, 0, 6, None, None))

        # # Overlap
        self.assertEqual(merge_parts((1, 5, 0, 6, None, None), (2, 7, 0, 6, None, None)), (1, 7, 0, 6, None, None))
        self.assertEqual(merge_parts((2, 7, 0, 6, None, None), (1, 5, 0, 6, None, None)), (1, 7, 0, 6, None, None))

        # # Same
        self.assertEqual(merge_parts((2, 7, 0, 6, None, None), (2, 7, 0, 6, None, None)), (2, 7, 0, 6, None, None))

        # Does not overlap
        self.assertEqual(merge_parts((4, 7, 0, 6, None, None), (1, 3, 0, 6, None, None)), None)
        self.assertEqual(merge_parts((1, 3, 0, 6, None, None), (4, 7, 0, 6, None, None)), None)

    def test_merge_parts_with_code(self):
        # # Contains
        self.assertEqual(merge_parts((3, 5, 0, 6, 'pass', None), (1, 7, 0, 6, None, None)), (1, 7, 0, 6, None, None))
        self.assertEqual(merge_parts((1, 7, 0, 6, None, None), (3, 5, 0, 6, 'pass', None)), (1, 7, 0, 6, None, None))

        ## Overlap
        self.assertEqual(merge_parts((1, 5, 0, 6, 'pass', None), (2, 7, 0, 6, None, None)), (1, 7, 0, 6, 'pass', None))
        self.assertEqual(merge_parts((2, 7, 0, 6, None, None), (1, 5, 0, 6, 'pass', None)), (1, 7, 0, 6, 'pass', None))

        ## Same
        self.assertEqual(
            merge_parts((2, 7, 0, 6, 'pass', None), (2, 7, 0, 6, 'pass', None)), (2, 7, 0, 6, 'pass', None)
        )

        # Does not overlap
        self.assertEqual(merge_parts((4, 7, 0, 6, 'pass', None), (1, 3, 0, 6, None, None)), None)
        self.assertEqual(merge_parts((1, 3, 0, 6, None, None), (4, 7, 0, 6, 'pass', None)), None)

    def test_merge_parts_dropping_code_to_insert_when_symbol_before_code_to_insert_is_removed(self):
        # Compare overlapping Rows
        ## Contains
        self.assertEqual(merge_parts((3, 5, 0, 6, 'pass', None), (1, 7, 0, 6, None, None)), (1, 7, 0, 6, None, None))
        self.assertEqual(merge_parts((1, 7, 0, 6, None, None), (3, 5, 0, 6, 'pass', None)), (1, 7, 0, 6, None, None))

        self.assertEqual(merge_parts((3, 5, 0, 6, None, None), (1, 7, 0, 6, 'pass', None)), (1, 7, 0, 6, 'pass', None))
        self.assertEqual(merge_parts((1, 7, 0, 6, 'pass', None), (3, 5, 0, 6, None, None)), (1, 7, 0, 6, 'pass', None))

        ## Overlap
        self.assertEqual(merge_parts((1, 5, 0, 6, 'pass', None), (2, 7, 0, 6, None, None)), (1, 7, 0, 6, 'pass', None))
        self.assertEqual(merge_parts((2, 7, 0, 6, None, None), (1, 5, 0, 6, 'pass', None)), (1, 7, 0, 6, 'pass', None))

        self.assertEqual(merge_parts((1, 5, 0, 6, None, None), (2, 7, 0, 6, 'pass', None)), (1, 7, 0, 6, None, None))
        self.assertEqual(merge_parts((2, 7, 0, 6, 'pass', None), (1, 5, 0, 6, None, None)), (1, 7, 0, 6, None, None))

        ## Same
        self.assertEqual(
            merge_parts((2, 7, 0, 6, 'pass', None), (2, 7, 0, 6, 'pass', None)), (2, 7, 0, 6, 'pass', None)
        )

        ## Does not overlap
        self.assertEqual(merge_parts((4, 7, 0, 6, 'pass', None), (1, 3, 0, 6, None, None)), None)
        self.assertEqual(merge_parts((1, 3, 0, 6, None, None), (4, 7, 0, 6, 'pass', None)), None)

        self.assertEqual(merge_parts((4, 7, 0, 6, None, None), (1, 3, 0, 6, 'pass', None)), None)
        self.assertEqual(merge_parts((1, 3, 0, 6, 'pass', None), (4, 7, 0, 6, None, None)), None)

        # Compare overlapping Columns
        ## Contains
        self.assertEqual(merge_parts((1, 1, 3, 5, 'pass', None), (1, 1, 1, 7, None, None)), (1, 1, 1, 7, None, None))
        self.assertEqual(merge_parts((1, 1, 1, 7, None, None), (1, 1, 3, 5, 'pass', None)), (1, 1, 1, 7, None, None))

        self.assertEqual(merge_parts((1, 1, 3, 5, None, None), (1, 1, 1, 7, 'pass', None)), (1, 1, 1, 7, 'pass', None))
        self.assertEqual(merge_parts((1, 1, 1, 7, 'pass', None), (1, 1, 3, 5, None, None)), (1, 1, 1, 7, 'pass', None))

        ## Overlap
        self.assertEqual(merge_parts((1, 1, 1, 5, 'pass', None), (1, 1, 2, 7, None, None)), (1, 1, 1, 7, 'pass', None))
        self.assertEqual(merge_parts((1, 1, 2, 7, None, None), (1, 1, 1, 5, 'pass', None)), (1, 1, 1, 7, 'pass', None))

        self.assertEqual(merge_parts((1, 1, 1, 5, None, None), (1, 1, 2, 7, 'pass', None)), (1, 1, 1, 7, None, None))
        self.assertEqual(merge_parts((1, 1, 2, 7, 'pass', None), (1, 1, 1, 5, None, None)), (1, 1, 1, 7, None, None))

        ## Same
        self.assertEqual(
            merge_parts((1, 1, 2, 7, 'pass', None), (1, 1, 2, 7, 'pass', None)), (1, 1, 2, 7, 'pass', None)
        )

        ## Does not overlap
        self.assertEqual(merge_parts((1, 1, 4, 7, 'pass', None), (1, 1, 1, 3, None, None)), None)
        self.assertEqual(merge_parts((1, 1, 1, 3, None, None), (1, 1, 4, 7, 'pass', None)), None)

        self.assertEqual(merge_parts((1, 1, 4, 7, None, None), (1, 1, 1, 3, 'pass', None)), None)
        self.assertEqual(merge_parts((1, 1, 1, 3, 'pass', None), (1, 1, 4, 7, None, None)), None)

    # # TODO: add additional tests that for insert_parts testing when merging different intervals.


class TestMergeBranches(BaseTestCase):
    def test_does_include_returns_true_when_contained(self):
        # bigger starts later and ends faster -> contained
        assert does_include((3, 5, 0, 6, None, None), (1, 7, 0, 6, None, None)) is True

    def test_contained_part_is_dropped_during_merge(self):
        # (1,5) is contained in (1,10): break + drop path
        parts = [(1, 10, 0, 6, None, None), (1, 5, 0, 6, None, None)]
        assert merge_overlaping_file_parts(parts) == [(1, 10, 0, 6, None, None)]

    def test_merge_picks_second_insert_code_at_same_start(self):
        # same start, p1 insert falsy -> insert_code = p2's
        assert merge_parts((2, 7, 0, 6, None, None), (2, 7, 0, 6, 'pass', None)) == (2, 7, 0, 6, 'pass', None)
