import sys
from typing import Optional, TypeVar

T = TypeVar('T')

def fix_indent(doc: T) -> Optional[T]:
    """Finds indentation of a first line and removes it from all following lines.

    Implemented based on inspect.cleandoc by keeping trailing lines.
    """
    if isinstance(doc, bytes):
        try:
            byte_lines = doc.expandtabs().split(b'\n')
        except UnicodeError:
            return None
        else:
            # Find minimum indentation of any non-blank lines after first line.
            margin = sys.maxsize
            for byte_line in byte_lines[0:]:
                content = len(byte_line.lstrip())
                if content:
                    indent = len(byte_line) - content
                    margin = min(margin, indent)
            # Remove indentation.
            if byte_lines:
                byte_lines[0] = byte_lines[0].lstrip()
            if margin < sys.maxsize:
                for i in range(1, len(byte_lines)):
                    byte_lines[i] = byte_lines[i][margin:]

            ## Do not remove trailing lines
            # while lines and not lines[-1]:
            #     lines.pop()

            ## Remove any leading blank lines.
            while byte_lines and not byte_lines[0]:
                byte_lines.pop(0)
            return b'\n'.join(byte_lines)  # type: ignore

    if isinstance(doc, str):
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
            return '\n'.join(lines)  # type: ignore

    return None
