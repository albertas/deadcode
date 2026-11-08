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


def _end_of_line_content(content_lines: list[bytes], line_number: int) -> int:
    """Returns the length of a line without its trailing line terminator."""
    line = _line_bytes(content_lines, line_number)
    for terminator in (b'\r\n', b'\n', b'\r'):
        if line.endswith(terminator):
            return len(line) - len(terminator)
    return len(line)


def _first_non_whitespace_column(content_lines: list[bytes], line_number: int, start_column: int) -> int | None:
    """Returns the first non-whitespace column at or after ``start_column``."""
    line = _line_bytes(content_lines, line_number)
    end_column = _end_of_line_content(content_lines, line_number)
    for column in range(start_column, end_column):
        if line[column : column + 1] not in (b' ', b'\t'):
            return column
    return None


def _last_non_whitespace_column_before(content_lines: list[bytes], line_number: int, end_column: int) -> int | None:
    """Returns the last non-whitespace column strictly before ``end_column``."""
    line = _line_bytes(content_lines, line_number)
    for column in range(end_column - 1, -1, -1):
        if line[column : column + 1] not in (b' ', b'\t'):
            return column
    return None


def _is_only_whitespace_or_comment(remainder: bytes) -> bool:
    """Returns whether the remainder is whitespace or a trailing comment."""
    stripped_remainder = remainder.strip()
    return not stripped_remainder or stripped_remainder.startswith(b'#')


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

            start_column = node.col_offset
            end_column = node.end_col_offset
            following_column = _first_non_whitespace_column(content_lines, node.end_lineno, end_column)
            if (
                following_column is not None
                and _line_bytes(content_lines, node.end_lineno)[following_column : following_column + 1] == b';'
            ):
                end_column = following_column + 1
                after_separator_column = _first_non_whitespace_column(content_lines, node.end_lineno, end_column)
                if after_separator_column is not None:
                    end_column = after_separator_column
            else:
                preceding_column = _last_non_whitespace_column_before(content_lines, node.lineno, node.col_offset)
                if (
                    preceding_column is not None
                    and _line_bytes(content_lines, node.lineno)[preceding_column : preceding_column + 1] == b';'
                ):
                    start_column = preceding_column

            line_content_end = _end_of_line_content(content_lines, node.end_lineno)
            remainder = _line_bytes(content_lines, node.end_lineno)[end_column:line_content_end]
            if _is_only_whitespace_or_comment(remainder):
                end_column = line_content_end

            import_parts.append(Part(node.lineno, node.end_lineno, start_column, end_column))
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
                    matched_keys.add(key)
                    continue
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
                        matched_keys.add(key)
                        continue
                    if previous_alias.end_lineno != alias.lineno:
                        import_parts.append(
                            Part(comma[0], comma[0], comma[1], _end_of_line_content(content_lines, comma[0]))
                        )
                        import_parts.append(Part(alias.lineno, alias.end_lineno, 0, alias.end_col_offset))
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
