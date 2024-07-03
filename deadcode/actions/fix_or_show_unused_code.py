from collections import defaultdict
from difflib import diff_bytes, unified_diff
from typing import Iterable
import os

from deadcode.actions.merge_overlaping_file_parts import merge_overlaping_file_parts
from deadcode.actions.remove_file_parts_from_content import remove_file_parts_from_content
from deadcode.data_types import Args
from deadcode.visitor.code_item import CodeItem
from deadcode.utils.flatten_lists import flatten_list
from deadcode.utils.add_colors_to_diff import add_colors_to_diff
from deadcode.visitor.ignore import _match


def fix_or_show_unused_code(unused_items: Iterable[CodeItem], args: Args) -> str:
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
        file_parts = flatten_list([item.code_parts for item in file_unused_items])

        unused_file_parts = merge_overlaping_file_parts(file_parts)

        with open(filename, 'rb') as f:
            file_content_lines = f.readlines()

        updated_file_content_lines = remove_file_parts_from_content(file_content_lines, unused_file_parts)
        updated_file_content = b''.join(updated_file_content_lines)
        if updated_file_content.strip():
            if args.dry and ('__all_files__' in args.dry or _match(filename, args.dry)):
                with open(filename, 'rb') as f:
                    filename_bytes = filename.encode()
                    diff = diff_bytes(unified_diff, f.readlines(), updated_file_content_lines,
                                      fromfile=filename_bytes, tofile=filename_bytes)
                    # TODO: consider printing result instantly to save memory
                    result_chunk = b''.join(diff)
                    if args.no_color:
                        result.append(result_chunk)
                    else:
                        result.append(add_colors_to_diff(result_chunk))

            elif args.fix:
                with open(filename, 'wb') as f:
                    # TODO: is there a method writelines?
                    f.write(updated_file_content)
        else:
            os.remove(filename)

    if result:
        return b'\n'.join(result).decode()
    return ''

    # TODO: update this one: solution is to use read and write operations.
    #
    # Solution is to open file for reading and then for writing.
