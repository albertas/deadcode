from deadcode.actions.merge_overlaping_file_parts import merge_overlaping_file_parts, does_overlap, merge_parts


def test_no_overlaping_parts():
    # Having
    overlaping_file_parts = [
        # Line, line_end, col, col_end
        (1, 0, 2, 6),
        (3, 0, 5, 6),
    ]
    expected_result = overlaping_file_parts

    # When
    non_overlaping_file_parts = merge_overlaping_file_parts(overlaping_file_parts)

    # Then
    assert non_overlaping_file_parts == expected_result


def test_overlaping_lines():
    # Having
    overlaping_file_parts = [
        # Line, line_end, col, col_end
        (1, 2, 0, 6),
        (2, 5, 0, 6),
    ]
    expected_result = [(1, 5, 0, 6)]

    # When
    non_overlaping_file_parts = merge_overlaping_file_parts(overlaping_file_parts)

    # Then
    assert non_overlaping_file_parts == expected_result


def test_does_overlap():
    # # Contains

    # Then
    assert does_overlap((3, 5, 0, 6), (1, 7, 0, 6))
    assert does_overlap((1, 7, 0, 6), (3, 5, 0, 6))

    # # Overlaps
    assert does_overlap((1, 5, 0, 6), (2, 7, 0, 6))
    assert does_overlap((2, 7, 0, 6), (1, 5, 0, 6))

    # # Same
    assert does_overlap((2, 7, 0, 6), (2, 7, 0, 6))

    # Does not overlap
    assert not does_overlap((4, 7, 0, 6), (1, 3, 0, 6))
    assert not does_overlap((1, 3, 0, 6), (4, 7, 0, 6))


def test_merge_parts():
    # # Contains

    # Then
    assert merge_parts((3, 5, 0, 6), (1, 7, 0, 6)) == (1, 7, 0, 6)
    assert merge_parts((1, 7, 0, 6), (3, 5, 0, 6)) == (1, 7, 0, 6)

    # # Overlape
    assert merge_parts((1, 5, 0, 6), (2, 7, 0, 6)) == (1, 7, 0, 6)
    assert merge_parts((2, 7, 0, 6), (1, 5, 0, 6)) == (1, 7, 0, 6)

    # # Same
    assert merge_parts((2, 7, 0, 6), (2, 7, 0, 6)) == (2, 7, 0, 6)

    # Does not overlap
    assert merge_parts((4, 7, 0, 6), (1, 3, 0, 6)) is None
    assert merge_parts((1, 3, 0, 6), (4, 7, 0, 6)) is None
