from deadcode.data_types import Part


def does_include(bigger_part: Part, smaller_part: Part) -> bool:
    line_start_b, line_end_b, col_start_b, col_end_b, _insert_code_b, _insert_condition_b = bigger_part
    line_start_s, line_end_s, col_start_s, col_end_s, _insert_code_s, _insert_condition_s = smaller_part

    starts_later = (line_start_b > line_start_s) or ((line_start_b == line_start_s) and (col_start_b >= col_start_s))

    ends_faster = (line_end_b < line_end_s) or ((line_end_b == line_end_b) and (col_end_b <= col_end_s))

    return bool(starts_later and ends_faster)


def sort_parts(bigger_part: Part, smaller_part: Part) -> tuple[Part, Part]:
    """Returns code part which begins first following by another code part."""
    # TODO: Column should go first (tuple comparison would be possible)
    line_start_b, _line_end_b, col_start_b, _col_end_b, _insert_code_b, _insert_condition_b = bigger_part
    line_start_s, _line_end_s, col_start_s, _col_end_s, _insert_code_s, _insert_condition_s = smaller_part

    # Pirmo pradžios eilutė ir stulpelis yra pirmiau.
    if (line_start_s < line_start_b) or ((line_start_s == line_start_b) and (col_start_s < col_start_b)):
        return smaller_part, bigger_part
    return bigger_part, smaller_part


def does_overlap(bigger_part: Part, smaller_part: Part) -> bool:
    # TODO: those are not bigger/smaller - start first, start second
    bigger_part, smaller_part = sort_parts(bigger_part, smaller_part)

    _line_start_b, line_end_b, _col_start_b, col_end_b, _insert_code_b, _insert_condition_b = bigger_part
    line_start_s, _line_end_s, col_start_s, _col_end_s, _insert_code_s, _insert_condition_s = smaller_part

    # ar pirmo pabaiga perlipa antro pradžia
    return bool((line_end_b > line_start_s) or ((line_end_b == line_start_s) and (col_end_b > col_start_s)))


def merge_parts(p1: Part, p2: Part) -> Part | None:
    """Merge code parts that have to be removed"""
    p1, p2 = sort_parts(p1, p2)

    line_start1, line_end1, col_start1, col_end1, insert_code1, insert_condition_1 = p1
    line_start2, line_end2, col_start2, col_end2, insert_code2, insert_condition_2 = p2

    if (line_end1 > line_start2) or ((line_end1 == line_start2) and (col_end1 > col_start2)):
        line_start = line_start1
        col_start = col_start1
        insert_code = None
        if line_end1 > line_end2:
            line_end = line_end1
            col_end = col_end1
            # Which fragment starts first.
            # insert_code = insert_code1
        elif line_end2 > line_end1:
            line_end = line_end2
            col_end = col_end2
            # Which fragment starts first.
            # insert_code = insert_code2
        else:
            line_end = line_end1
            col_end = max(col_end1, col_end2)

        p1_starts_first = (line_start1 < line_start2) or ((line_start1 == line_start2) and (col_start1 < col_start2))
        starts_at_the_same_place = (line_start1 == line_start2) and (col_start1 == col_start2)
        if p1_starts_first:
            insert_code = insert_code1
            insert_contition = insert_condition_1
        elif starts_at_the_same_place:
            if insert_code1:
                insert_code = insert_code1
                insert_contition = insert_condition_1
            else:
                insert_code = insert_code2
                insert_contition = insert_condition_2
        else:
            insert_code = insert_code2
            insert_contition = insert_condition_2

        # TODO: improve merging of code1 and code2
        # TODO: choose insert code based on col
        # which col is higher
        # insert_code = insert_code1 or insert_code2

        return Part(line_start, line_end, col_start, col_end, insert_code, insert_contition)

    return None


def merge_overlaping_file_parts(overlaping_file_parts: list[Part]) -> list[Part]:
    # Make algorithm O(n^2) by checking every single part if overlaps

    non_overlaping_file_parts: list[Part] = []

    # NOTE: Sorting by beginning and size (starting first and larger go first):
    sorted_overlaping_file_parts = sorted(overlaping_file_parts, key=lambda x: (x[0], x[2], -x[1], -x[3]))

    for p1 in sorted_overlaping_file_parts:
        # for p1 in sorted(overlaping_file_parts):
        merged_part = None
        merged_with_index = None
        for j, p2 in enumerate(non_overlaping_file_parts):
            # Is p1 inside p2
            if does_include(p2, p1):
                break

            if does_overlap(p2, p1):
                merged_part = merge_parts(p2, p1)
                merged_with_index = j
                break
        else:
            non_overlaping_file_parts.append(p1)

        if merged_part and merged_with_index is not None:
            non_overlaping_file_parts.pop(merged_with_index)
            non_overlaping_file_parts.append(merged_part)

    return non_overlaping_file_parts
