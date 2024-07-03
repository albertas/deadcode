import re
from typing import List, Optional, TypeVar

from deadcode.data_types import Part

T = TypeVar('T')


def list_get(list_: List[T], index: int) -> Optional[T]:
    if len(list_) > index:
        return list_[index]
    return None


def ends_with_semicolon(line: bytes) -> bool:
    return line.strip().endswith(b':')


def indentation_is_not_childs(previous_line: bytes, current_line: bytes) -> bool:
    return len(get_indentation(previous_line)) >= len(get_indentation(current_line))


def get_indentation(line: bytes) -> bytes:
    return bytes(re.findall(b'^\\s*', line)[0])


def remove_as_from_end(line: bytes) -> bytes:
    if not (line_rstrip := line.rstrip()).endswith(b'as'):
        return line

    # Is there white spaces before as
    if line_rstrip[:-2] != (line_with_removed_as := line_rstrip[:-2].rstrip()):
        return line_with_removed_as
    return line


def remove_comma_from_begining(line: bytes) -> bytes:
    if not line.lstrip().startswith(b','):
        return line

    return line.lstrip()[1:].lstrip()


def remove_file_parts_from_content(content_lines: List[bytes], unused_file_parts: List[Part]) -> List[bytes]:
    """ """
    # How should move through the lines of content?
    updated_content_lines = []

    # TODO: iterate by line and crop that line if needed.
    unused_part_index = 0

    previous_non_removed_line = b''
    was_block_removed = False
    next_line_after_removed_block = None
    indentation_of_first_removed_line = b''
    empty_lines_in_a_row_list: List[bytes] = []
    empty_lines_before_removed_block_list: List[bytes] = []

    for current_lineno, line in enumerate(content_lines, start=1):
        from_line, to_line, from_col, to_col = 0, 0, 0, 0
        if unused_part := list_get(unused_file_parts, unused_part_index):
            from_line, to_line, from_col, to_col = unused_part

        # Skip lines, which have to be ignored.
        if current_lineno > from_line and current_lineno < to_line:
            continue

        # Is it first line, which have to be ignored?
        elif current_lineno == from_line:
            indentation_of_first_removed_line = get_indentation(line)

            if from_line == to_line:
                # TODO: this check is a workaround for an assignment expression.
                # Clean-ups have to be applied based on removable expression type.
                if (line[:from_col] + line[to_col:]).strip().startswith(b'='):
                    line = line[:from_col]
                else:
                    # TODO: should apply `as` removal rule only for particular expression type only
                    # as well as comma removal.
                    line = remove_as_from_end(line[:from_col]) + remove_comma_from_begining(line[to_col:])

                unused_part_index += 1

                if not line.strip():
                    empty_lines_before_removed_block_list, empty_lines_in_a_row_list = (
                        empty_lines_in_a_row_list,
                        empty_lines_before_removed_block_list,
                    )

                    was_block_removed = True
            else:
                line = line[:from_col]

            if line.strip() and not line.startswith(b'#'):
                previous_non_removed_line = line
                updated_content_lines.append(line)

        # Is it last line, from the block, which have to be ignored?
        elif current_lineno == to_line:
            line = line[to_col:]

            # Remove trailing comma, if we have removed something.
            # TODO: this should be applied only for specific expression types only.
            if line.lstrip().startswith(b','):
                line = line.lstrip()[1:].lstrip()

            unused_part_index += 1
            # TODO: Add tests for case, when comments are added at the start or end of the removed block
            if line.strip() and not line.startswith(b'#'):
                updated_content_lines.append(line)

            empty_lines_before_removed_block_list, empty_lines_in_a_row_list = (
                empty_lines_in_a_row_list,
                empty_lines_before_removed_block_list,
            )
            was_block_removed = True

        # Do not remove the line
        else:
            if not line.strip():
                empty_lines_in_a_row_list.append(line)
                continue

                # if was_block_removed:  # These lines will be added when first non-empty line is found
                #     continue
            elif not was_block_removed:
                updated_content_lines.extend(empty_lines_in_a_row_list)
                empty_lines_in_a_row_list.clear()

            else:
                # Add pass if needed - if its a file end we should also check if pass have to be added.
                next_line_after_removed_block = line

                if ends_with_semicolon(previous_non_removed_line):
                    if indentation_is_not_childs(
                        previous_line=previous_non_removed_line, current_line=next_line_after_removed_block
                    ):
                        updated_content_lines.append(indentation_of_first_removed_line + b'pass\n')

                    # Add empty lines
                    if indentation_is_not_childs(
                        previous_line=previous_non_removed_line, current_line=next_line_after_removed_block
                    ):
                        # Add lines after
                        updated_content_lines.extend(empty_lines_in_a_row_list)
                        empty_lines_in_a_row_list.clear()
                        empty_lines_before_removed_block_list.clear()
                    else:
                        updated_content_lines.extend(empty_lines_before_removed_block_list)
                        empty_lines_before_removed_block_list.clear()
                        empty_lines_in_a_row_list.clear()

                else:
                    updated_content_lines.extend(empty_lines_before_removed_block_list)
                    empty_lines_before_removed_block_list.clear()
                    empty_lines_in_a_row_list.clear()

            was_block_removed = False
            previous_non_removed_line = line
            updated_content_lines.append(line)

    if was_block_removed:
        if ends_with_semicolon(previous_non_removed_line):
            updated_content_lines.append(indentation_of_first_removed_line + b'pass\n')

    return updated_content_lines
