import sys
from typing import Optional


def fix_indent(doc: str) -> Optional[str]:
    """Finds indentation of a first line and removes it from all following lines.

    Implemented based on inspect.cleandoc by keeping trailing lines.
    """
    try:
        lines = doc.expandtabs().split('\n')
    except UnicodeError:
        return None
    else:
        # Find minimum indentation of any non-blank lines after first line.
        margin = sys.maxsize
        for line in lines[0:]:
            content = len(line.lstrip())
            if content:
                indent = len(line) - content
                margin = min(margin, indent)
        # Remove indentation.
        if lines:
            lines[0] = lines[0].lstrip()
        if margin < sys.maxsize:
            for i in range(1, len(lines)):
                lines[i] = lines[i][margin:]

        ## Do not remove trailing lines
        # while lines and not lines[-1]:
        #     lines.pop()

        ## Remove any leading blank lines.
        while lines and not lines[0]:
            lines.pop(0)
        return '\n'.join(lines)
