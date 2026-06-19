import sys


def _find_common_margin(lines: list[str]) -> int:
    """Minimum indentation across non-blank lines; sys.maxsize if none found."""
    margin = sys.maxsize
    for line in lines:
        content = len(line.lstrip())
        if content:
            indent = len(line) - content
            margin = min(margin, indent)
    return margin


def _strip_margin(lines: list[str], margin: int) -> None:
    """De-indent lines[1:] in place, preserving non-space prefix characters."""
    for i in range(1, len(lines)):
        prefix = lines[i][:margin]
        if prefix_without_spaces := prefix.rstrip(' '):
            lines[i] = prefix_without_spaces + lines[i][margin:]
        else:
            lines[i] = lines[i][margin:]


def fix_indent(doc: str) -> str | None:
    """Finds indentation of a first line and removes it from all following lines.

    Implemented based on inspect.cleandoc by keeping trailing lines.
    """
    try:
        lines = doc.expandtabs().splitlines(True)
    except UnicodeError:
        return None
    else:
        # TODO: this method also removed empty lines, which makes exact asserting checking hard.

        margin = _find_common_margin(lines)
        if lines:
            lines[0] = lines[0].lstrip()
        if margin < sys.maxsize:
            _strip_margin(lines, margin)

        ## Do not remove trailing lines
        # while lines and not lines[-1]:
        #     lines.pop()

        ## Remove any leading blank lines.
        while lines and not lines[0]:
            lines.pop(0)
        return ''.join(lines)
