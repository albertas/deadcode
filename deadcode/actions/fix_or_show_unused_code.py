from collections import defaultdict
from difflib import unified_diff
from collections.abc import Iterable
import os

from deadcode.actions.merge_overlaping_file_parts import merge_overlaping_file_parts
from deadcode.actions.remove_file_parts_from_content import remove_file_parts_from_content
from deadcode.data_types import Args, Filename, Part
from deadcode.visitor.code_item import CodeItem
from deadcode.utils.flatten_lists import flatten_list
from deadcode.utils.add_colors_to_diff import add_colors_to_diff
from deadcode.visitor.ignore import _match


def _compute_updated_content(
    filename: Filename,
    file_unused_items: list[CodeItem],
    additional_code_parts_to_remove: dict[Filename, list[Part]],
) -> list[str]:
    file_parts = flatten_list([item.code_parts for item in file_unused_items])
    if additional_code_parts_to_remove and additional_code_parts_to_remove.get(str(filename)):
        file_parts.extend(additional_code_parts_to_remove[str(filename)])

    unused_file_parts = merge_overlaping_file_parts(file_parts)

    with open(filename) as f:
        file_content_lines = f.readlines()

    return remove_file_parts_from_content(file_content_lines, unused_file_parts)


def _emit_for_file(filename: Filename, updated_file_content_lines: list[str], args: Args) -> str | None:
    updated_file_content = ''.join(updated_file_content_lines)
    if updated_file_content.strip():
        if args.dry and ('__all_files__' in args.dry or _match(filename, args.dry)):
            with open(filename, 'r') as f:
                diff = unified_diff(f.readlines(), updated_file_content_lines, fromfile=filename, tofile=filename)
                # TODO: consider printing result instantly to save memory

                # Adding empty line after each diff, because if a file does not have line end
                # in the end of file: the next diff is started at the same line.
                diff_str = ''.join(diff) + '\n'
                if args.no_color:
                    return diff_str
                return add_colors_to_diff(diff_str)
        elif args.fix:
            with open(filename, 'w') as f:
                # TODO: is there a method writelines?
                f.write(updated_file_content)
    else:
        os.remove(filename)
    return None


def fix_or_show_unused_code(
    unused_items: Iterable[CodeItem],
    additional_code_parts_to_remove: dict[Filename, list[Part]],
    args: Args,
) -> str:
    # Reading and writing should be patched in this file.

    # Group unused_names by filenames
    # For each filename find file parts, which have to be fixed.
    # And fix those file parts.
    #
    # TODO: trailing commas, trailing white spaces and empty lines

    filename_to_unused_items = defaultdict(list)
    for unused_item in unused_items:
        filename_to_unused_items[str(unused_item.filename)].append(unused_item)

    result = []

    for filename, file_unused_items in filename_to_unused_items.items():
        updated_file_content_lines = _compute_updated_content(
            filename, file_unused_items, additional_code_parts_to_remove
        )
        emitted = _emit_for_file(filename, updated_file_content_lines, args)
        if emitted is not None:
            result.append(emitted)

    if result:
        return ''.join(result)
    return ''

    # TODO: update this one: solution is to use read and write operations.
    #
    # Solution is to open file for reading and then for writing.
