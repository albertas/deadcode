import re
from typing import List, Optional, TypeVar, Tuple

from deadcode.data_types import Part

T = TypeVar('T')


def list_get(list_: List[T], index: int) -> Optional[T]:
    if len(list_) > index:
        return list_[index]
    return None


def ends_with_semicolon(line: str) -> bool:
    return line.strip().endswith(':')


def indentation_is_not_childs(previous_line: str, current_line: str) -> bool:
    return len(get_indentation(previous_line)) >= len(get_indentation(current_line))


def get_indentation(line: str) -> str:
    return str(re.findall('^\s*', line)[0])


def remove_as_from_end(line: str) -> str:
    if not (line_rstrip := line.rstrip()).endswith('as'):
        return line

    # Is there white spaces before as
    if line_rstrip[:-2] != (line_with_removed_as := line_rstrip[:-2].rstrip()):
        return line_with_removed_as
    return line


def remove_comma_from_begining(line: str) -> str:
    if not line.lstrip().startswith(','):
        return line

    return line.lstrip()[1:].lstrip()


def get_code_parts_for_the_same_line(
    code_parts: List[Tuple[int, int, int, int]], index: int
) -> List[Tuple[int, int, int, int]]:
    """Code parts that start on the same line as the provided one ends. Provides parts in a reversed order."""
    code_parts_for_the_same_line = []
    line = None

    for code_part in code_parts[index:]:
        if line is None:
            line = code_part[1]
        if code_part[0] == line:
            code_parts_for_the_same_line.insert(0, code_part)
        else:
            break
    return code_parts_for_the_same_line


def remove_unused_fragments_from_a_line(line: str, code_parts, index: int):
    """
    line = 'bar as bar_alias,\n'
    #       ....--.....-----..
    # Line is 3.
    # Ranges have to be removed: :4,6:11,16:
    # as alias
    # as bar_alias,  # The two parts were not removed

    # code_parts = [(1, 3, 17, 4), (4, 4, 4, 22)]
    code_parts = [(1, 3, 17, 4), (3, 3, 7, 9), (3, 3, 9, 11), (3, 4, 16, 4)]
    index = 0
    line, increment = remove_unused_fragments_from_a_line(line, code_parts, index)
    print(line)
    print("Received increment", increment)
    print("Received line:", line)
    print("Expected increment", 2)
    print("Expected line:", "as alias")
    """

    # Do I have a line here and can I get the white spaces?

    lineno = code_parts[index][1]

    # Find changes that have to be applied to the line in reverse order.
    code_parts_for_the_same_line = []
    for code_part in code_parts[index:]:
        if code_part[0] == lineno:
            code_parts_for_the_same_line.insert(0, code_part)
        elif code_part[1] == lineno:
            pass
        else:
            break

    # TODO: Remove fragment from the end of the current line
    if (
        code_parts_for_the_same_line
        and code_parts_for_the_same_line[0][0] == lineno
        and code_parts_for_the_same_line[0][1] != lineno
    ):
        from_line, to_line, from_col, to_col, insert_code, insert_condition = code_parts_for_the_same_line[0]
        line = line[:from_col] + '\n'  # re-attach newline so buffered blank lines stay intact
        code_parts_for_the_same_line.pop(0)

    # Remove fragments from the middle of the line.
    index_increment = 0
    for unused_part in code_parts_for_the_same_line:
        from_line, to_line, from_col, to_col, insert_code, insert_condition = unused_part
        if from_line == to_line:
            line = line[:from_col] + line[to_col:]
            index_increment += 1
        else:
            break

    # Remove the begining of the line.
    first_code_part = code_parts[index]
    if first_code_part[0] != first_code_part[1]:
        from_line, to_line, from_col, to_col, insert_code, insert_condition = first_code_part
        line = line[to_col:]
        index_increment += 1

    # if not line.strip():
    #     line = ''

    return line, index_increment


def remove_file_parts_from_content(content_lines: List[str], unused_file_parts: List[Part]) -> List[str]:
    """ """
    # How should move through the lines of content?
    updated_content_lines = []

    # TODO: iterate by line and crop that line if needed.
    unused_part_index = 0

    previous_non_removed_line = ''
    has_block_started = False
    was_block_removed = False  # A block is a chunk of code spanning multiple rows.
    next_line_after_removed_block = None
    indentation_of_first_removed_line = ''
    empty_lines_in_a_row_list: List[str] = []
    empty_lines_before_removed_block_list: List[str] = []

    # This method should be implemented not as a loop, but with a generator method, which is get next line.
    # We should operate in streams of symbols, not lines, since multiple code parts might be per line.
    # One code part might start, another might end - everything within the same line.
    # We should track symobl indexes.
    # This class could be rewritten as a class with inner state and helper methods like get next line.

    # TODO: implement it.
    # Decision is to have a method, which removes all uneeded parts from this line.

    for current_lineno, line in enumerate(content_lines, start=1):
        print(
            f'{current_lineno}. "\033[32m{line}\033[0m" is being processed. {has_block_started=}, {was_block_removed=}'
        )

        from_line, to_line, from_col, to_col = 0, 0, 0, 0
        if unused_part := list_get(unused_file_parts, unused_part_index):
            from_line, to_line, from_col, to_col, insert_code, insert_condition = unused_part
            print(
                f'{current_lineno}. Code part to remove {from_line=}, {to_line=}, {from_col=}, {to_col=}, {insert_code=}, {insert_condition=}'
            )

        # Skip lines, which have to be ignored.
        if current_lineno > from_line and current_lineno < to_line:
            print(f'{current_lineno}. Skipping line.')
            continue

        # Is it first line, which have to be ignored?
        elif current_lineno == from_line:
            indentation_of_first_removed_line = get_indentation(line)
            print(f'{current_lineno}. "{indentation_of_first_removed_line}" is line indentation.')

            if from_line == to_line:
                # It would be great to use helper methods here.

                # TODO: Multiple code parts could be on the same line.
                # Should iterate here and clean the line accordingly..

                # For the line end is the same. The line cannot put to use until whole line fragments got used.
                # > Lets do it here.

                line, index_increment = remove_unused_fragments_from_a_line(line, unused_file_parts, unused_part_index)

                print(f'{current_lineno}. Modification is in the same line. Updated line: "{line}".')
                unused_part_index += index_increment

                # for unused_part in get_code_parts_for_the_same_line(unused_file_parts, unused_part_index):
                #     from_line, to_line, from_col, to_col = unused_part
                #
                #     # TODO: the problem is that the code part might be multiline.
                #     if from_line == to_line:
                #         line = line[:from_col] + line[to_col:]
                #
                #         # The cursor moves: how to get only needed chunks?
                #         # How to clean it up? Reverse iteration is usually a solution.
                #
                #         # TODO: >>>>: Lets ensure that as is removed, comma is removed and assignment cleanup is resolved properly.
                #         # Removing the workarounds for now.
                #
                #         # # TODO: this check is a workaround for an assignment expression.
                #         # # Clean-ups have to be applied based on removable expression type.
                #         # if (line[:from_col] + line[to_col:]).strip().startswith('='):
                #         #     line = line[:from_col]  # Keeping only the indentation
                #         # else:
                #         #     # TODO: should apply `as` removal rule only for particular expression type only
                #         #     # as well as comma removal.
                #         #     line = remove_as_from_end(line[:from_col]) + remove_comma_from_begining(line[to_col:])
                #
                #         unused_part_index += 1
                #     else:
                #         break

                if insert_code:
                    line += insert_code

                if not line.strip():
                    empty_lines_before_removed_block_list, empty_lines_in_a_row_list = (
                        empty_lines_in_a_row_list,
                        empty_lines_before_removed_block_list,
                    )
                    print(f'{current_lineno}. Line "{line=}" is not empty setting: {was_block_removed=}.')
                    was_block_removed = True

            if from_line != to_line:
                line = line[:from_col]
                if insert_code:
                    line += insert_code
                has_block_started = not line.strip()
                print(
                    f'{current_lineno}. Modification is in different lines. Updated line: "{line}". {has_block_started=}'
                )

            if line.strip() and not line.startswith('#'):
                print(
                    f'{current_lineno}. Line has content: "{previous_non_removed_line=}", Adding line to content "{line}"'
                )
                previous_non_removed_line = line
                updated_content_lines.append(line)

        # Is it last line, from the block, which have to be ignored?
        elif current_lineno == to_line:
            # line = line[to_col:]

            line, index_increment = remove_unused_fragments_from_a_line(line, unused_file_parts, unused_part_index)
            # unused_parts = get_code_parts_for_the_same_line(unused_file_parts, unused_part_index)

            # Remove newline symbols after removing code block, because removing code block yields additional empty line
            if not line.strip():
                line = ''

            print(f'{current_lineno}. Line is the end of removable block: updated line "{line}"')

            unused_part_index += index_increment

            # TODO: detect if another code part is there which has to be processed.

            # if len(unused_parts) == 1:
            #     line = line[to_col:]

            #     # TODO: Treat multiple fragments of the same line.
            #     # for unused_part in get_code_parts_for_the_same_line(unused_file_parts, unused_part_index):
            #     #     from_line, to_line, from_col, to_col = unused_part
            #     #     line = line[:from_col] + line[to_col:]

            #     # Remove trailing comma, if we have removed something.
            #     # TODO: this should be applied only for specific expression types only.
            #     # if line.lstrip().startswith(','):
            #     #     line = line.lstrip()[1:].lstrip()

            #     # What can I do here?
            #     # Parts are overlapping.
            #     unused_part_index += 1
            # else:
            #     for unused_part in unused_parts:
            #         pass

            # TODO: Add tests for case, when comments are added at the start or end of the removed block
            if (line.strip() and not line.startswith('#')) or (
                updated_content_lines and not updated_content_lines[-1].endswith('\n')
            ):
                print(f'{current_lineno}. Adding line to the result "{line=}"')
                updated_content_lines.append(line)

            else:
                if line:
                    print(f'{current_lineno}. Adding line to empty_lines_in_a_row_list "{line}"')
                    empty_lines_in_a_row_list.append(line)

            # TODO: The issue here was that the line was not empty and after removal it became empty.
            # I would love to preserve only lines that were initially empty.

            # TODO: I love it.
            # TODO: Remove white spaces till the end of line after removing code part.
            # TODO: When detecting unused code part: check for white spaces at the end of line.
            # TODO: When code item is removed - I have to remove white spaces from the line.
            # TODO: solution: check if the remaining line is empty: if yes remove it.
            # TODO: Check if the remaining line consits only of the whitespaces and remove it completely.
            # TODO: conclusion: was_block_removed flag is not working properly. The block_was_removed, but the flag was truned off too early.
            # TODO: Investigate why and how was_block_removed flag should work.

            # Was this swap executed?
            print(f'{current_lineno}. Swapping empty_lines_beofre_removed_block_list with empty_lines_in_a_row_list')
            empty_lines_before_removed_block_list, empty_lines_in_a_row_list = (
                empty_lines_in_a_row_list,
                empty_lines_before_removed_block_list,
            )
            # Here block is not always removed.

            # This should only apply if block ended with :
            # if previous_non_removed_line.rstrip().endswith(':'):

            # Actually not whole block was removed only its part.
            # Not all lines were removed.
            # Should

            # TODO: how to detect a way to find out if only part of the block was removed.
            # Should have an additional flag, which tracks this information.
            if has_block_started:  # Has started and ended
                was_block_removed = True
                print(f'{current_lineno}. {has_block_started=} and line non empty, hence {was_block_removed=}')
            has_block_started = False
            print(f'{current_lineno}. Setting {has_block_started=}')

        # Do not remove the line
        else:
            if not line.strip():
                if was_block_removed:  # These lines will be added when first non-empty line is found
                    print(f'{current_lineno}. Block was removed, ignoring empty line.')
                    continue

                print(f'{current_lineno}. Line is empty, adding it to {empty_lines_in_a_row_list=}')
                empty_lines_in_a_row_list.append(line)
                continue

            elif not was_block_removed:
                print(f'{current_lineno}. not {was_block_removed=} hence adding "{line}" to result')
                updated_content_lines.extend(empty_lines_in_a_row_list)
                empty_lines_in_a_row_list.clear()

            else:
                print(f'{current_lineno}. {was_block_removed=} hence updating empty lines')
                # Add pass if needed - if its a file end we should also check if pass have to be added.
                next_line_after_removed_block = line

                if ends_with_semicolon(previous_non_removed_line):
                    print(f'{current_lineno}. Previous line ends with :')
                    if indentation_is_not_childs(
                        previous_line=previous_non_removed_line, current_line=next_line_after_removed_block
                    ):
                        print(f'{current_lineno}. Previous line ends with :')
                        # TODO: Why pass is here?
                        updated_content_lines.append(f'{indentation_of_first_removed_line}pass\n')

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

            print(f'Set \033[31mwas_block_removed = False\033[0m for {current_lineno} line {line}')
            was_block_removed = False
            previous_non_removed_line = line
            updated_content_lines.append(line)

        print(current_lineno, '~', line, f'{was_block_removed=}', end='')

    if was_block_removed:
        if ends_with_semicolon(previous_non_removed_line):
            updated_content_lines.append(f'{indentation_of_first_removed_line}pass\n')

    # # Add empty line to the end of file if it is not present
    # if updated_content_lines and not updated_content_lines[-1].endswith('\n'):
    #     updated_content_lines.append('\n')

    return updated_content_lines
