from typing import List, Optional, Tuple
from deadcode.data_types import Part


def does_include(bigger_part: Part, smaller_part: Part) -> bool:
    line_start_b, line_end_b, col_start_b, col_end_b = bigger_part
    line_start_s, line_end_s, col_start_s, col_end_s = smaller_part

    starts_later = (line_start_b > line_start_s) or ((line_start_b == line_start_s) and (col_start_b >= col_start_s))

    ends_faster = (line_end_b < line_end_s) or ((line_end_b == line_end_b) and (col_end_b <= col_end_s))

    return bool(starts_later and ends_faster)


def sort_parts(bigger_part: Part, smaller_part: Part) -> Tuple[Part, Part]:
    """Returns code part which begins first following by another code part."""
    # TODO: Column should go first (tuple comparison would be possible)
    line_start_b, line_end_b, col_start_b, col_end_b = bigger_part
    line_start_s, line_end_s, col_start_s, col_end_s = smaller_part

    # Pirmo pradžios eilutė ir stulpelis yra pirmiau.
    if (line_start_s < line_start_b) or ((line_start_s == line_start_b) and (col_start_s < col_start_b)):
        return smaller_part, bigger_part
    return bigger_part, smaller_part


def does_overlap(bigger_part: Part, smaller_part: Part) -> bool:
    bigger_part, smaller_part = sort_parts(bigger_part, smaller_part)

    line_start_b, line_end_b, col_start_b, col_end_b = bigger_part
    line_start_s, line_end_s, col_start_s, col_end_s = smaller_part

    # ar pirmo pabaiga perlipa antro pradžia
    return bool((line_end_b > line_start_s) or ((line_end_b == line_start_s) and (col_end_b > col_start_s)))


def merge_parts(p1: Part, p2: Part) -> Optional[Part]:
    p1, p2 = sort_parts(p1, p2)

    line_start1, line_end1, col_start1, col_end1 = p1
    line_start2, line_end2, col_start2, col_end2 = p2

    if (line_end1 > line_start2) or ((line_end1 == line_start2) and (col_end1 > col_start2)):
        line_start = line_start1
        col_start = col_start1
        if line_end1 > line_end2:
            line_end = line_end1
            col_end = col_end1
        elif line_end2 > line_end1:
            line_end = line_end2
            col_end = col_end2
        else:
            line_end = line_end1
            col_end = max(col_end1, col_end2)
        return Part(line_start, line_end, col_start, col_end)

    return None


def merge_overlaping_file_parts(overlaping_file_parts: List[Part]) -> List[Part]:
    # Make algorithm O(n^2) by checking every single part if overlaps

    non_overlaping_file_parts: List[Part] = []
    for p1 in sorted(overlaping_file_parts):
        merged_part = None
        merged_with_index = None
        for j, p2 in enumerate(non_overlaping_file_parts):
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
