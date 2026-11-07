import ast

from collections.abc import Iterable

from deadcode.data_types import Part
from deadcode.utils.flatten_lists import flatten_list
from deadcode.visitor.code_item import CodeItem

ImportAliasKey = tuple[str, int | None, int | None]


def get_import_alias_key(alias: ast.alias) -> ImportAliasKey:
    """Returns the key that identifies an import alias in reported findings."""
    return alias.asname or alias.name.partition('.')[0], alias.lineno, alias.col_offset


def _line_bytes(content_lines: list[bytes], line_number: int) -> bytes:
    if 1 <= line_number <= len(content_lines):
        return content_lines[line_number - 1]
    return b''


def _find_byte(content_lines: list[bytes], line_number: int, start_col: int, end_col: int, needle: bytes) -> int | None:
    position = _line_bytes(content_lines, line_number).find(needle, start_col, end_col)
    if position == -1:
        return None
    return position


def _find_comma_between(
    content_lines: list[bytes], start: tuple[int, int], end: tuple[int, int]
) -> tuple[int, int] | None:
    """Returns the position of the first comma between two source positions."""
    start_line, start_col = start
    end_line, end_col = end

    for line_number in range(start_line, end_line + 1):
        line = _line_bytes(content_lines, line_number)
        if line_number == start_line and line_number == end_line:
            position = _find_byte(content_lines, line_number, start_col, end_col, b',')
        elif line_number == start_line:
            position = _find_byte(content_lines, line_number, start_col, len(line), b',')
        elif line_number == end_line:
            position = _find_byte(content_lines, line_number, 0, end_col, b',')
        else:
            position = _find_byte(content_lines, line_number, 0, len(line), b',')

        if position is not None:
            return line_number, position

    return None


def _end_of_whitespace_after_comma(content_lines: list[bytes], comma: tuple[int, int]) -> int:
    line = _line_bytes(content_lines, comma[0])
    end_col = comma[1] + 1
    while end_col < len(line) and line[end_col : end_col + 1] in (b' ', b'\t'):
        end_col += 1
    return end_col


def get_unused_import_parts(content: bytes, unused_import_items: Iterable[CodeItem]) -> list[Part]:
    """Returns code parts to remove for unused import findings.

    When every non-wildcard alias of an import statement is unused, the whole
    statement is returned as a single part. Otherwise each unused alias is
    returned together with one adjacent comma, so the remaining aliases keep
    valid comma placement.
    """
    unused_import_items = list(unused_import_items)
    fallback_parts = flatten_list([item.code_parts for item in unused_import_items])
    removable_keys = {(item.name, item.name_line, item.name_column) for item in unused_import_items}

    try:
        tree = ast.parse(content)
    except SyntaxError:
        return fallback_parts

    content_lines = content.splitlines(keepends=True)
    import_parts: list[Part] = []
    matched_keys: set[ImportAliasKey] = set()

    for node in ast.walk(tree):
        if not isinstance(node, (ast.Import, ast.ImportFrom)):
            continue

        # A wildcard alias is never removable.
        aliases = [alias for alias in node.names if alias.name != '*']
        if not aliases:
            continue

        alias_keys = [get_import_alias_key(alias) for alias in aliases]

        if all(key in removable_keys for key in alias_keys):
            if node.end_lineno is None or node.end_col_offset is None:
                continue
            import_parts.append(Part(node.lineno, node.end_lineno, node.col_offset, node.end_col_offset))
            matched_keys.update(alias_keys)
            continue

        for index, alias in enumerate(aliases):
            key = alias_keys[index]
            if key not in removable_keys or alias.end_lineno is None or alias.end_col_offset is None:
                continue

            if index + 1 < len(aliases):
                next_alias = aliases[index + 1]
                comma = _find_comma_between(
                    content_lines,
                    (alias.end_lineno, alias.end_col_offset),
                    (next_alias.lineno, next_alias.col_offset),
                )
                if comma is None:
                    import_parts.append(Part(alias.lineno, alias.end_lineno, alias.col_offset, alias.end_col_offset))
                else:
                    end_col = _end_of_whitespace_after_comma(content_lines, comma)
                    import_parts.append(Part(alias.lineno, comma[0], alias.col_offset, end_col))
            else:
                previous_alias = aliases[index - 1]
                if previous_alias.end_lineno is None or previous_alias.end_col_offset is None:
                    import_parts.append(Part(alias.lineno, alias.end_lineno, alias.col_offset, alias.end_col_offset))
                else:
                    comma = _find_comma_between(
                        content_lines,
                        (previous_alias.end_lineno, previous_alias.end_col_offset),
                        (alias.lineno, alias.col_offset),
                    )
                    if comma is None:
                        import_parts.append(
                            Part(alias.lineno, alias.end_lineno, alias.col_offset, alias.end_col_offset)
                        )
                    else:
                        import_parts.append(Part(comma[0], alias.end_lineno, comma[1], alias.end_col_offset))

            matched_keys.add(key)

    remaining_fallback_parts = [
        part
        for item in unused_import_items
        if (item.name, item.name_line, item.name_column) not in matched_keys
        for part in item.code_parts
    ]

    return list(dict.fromkeys(import_parts + remaining_fallback_parts))
