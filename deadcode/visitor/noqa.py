from collections import defaultdict
import re
from typing import Dict, List, Set

NOQA_REGEXP = re.compile(
    # Use the same regex as flake8 does.
    # https://github.com/pycqa/flake8/blob/main/src/flake8/defaults.py
    # We're looking for items that look like this:
    # `# noqa`
    # `# noqa: E123`
    # `# noqa: E123,W451,F921`
    # `# NoQA: E123,W451,F921`
    rb'# noqa(?::[\s]?(?P<codes>([A-Z]+[0-9]+(?:[,\s]+)?)+))?',
    re.IGNORECASE,
)

NOQA_CODE_MAP = {
    # flake8 F401: module imported but unused.
    b'F401': b'DC07',
    # flake8 F841: local variable is assigned to but never used.
    b'F841': b'DC01',
    b'DC01': b'DC01',
    b'DC02': b'DC02',
    b'DC03': b'DC03',
    b'DC04': b'DC04',
    b'DC05': b'DC05',
    b'DC06': b'DC06',
    b'DC07': b'DC07',
    b'DC08': b'DC08',
    b'DC09': b'DC09',
    b'DC11': b'DC11',
    b'DC12': b'DC12',
    b'DC13': b'DC13',
    # For backward compatibility
    b'DC001': b'DC01',
    b'DC002': b'DC02',
    b'DC003': b'DC03',
    b'DC004': b'DC04',
    b'DC005': b'DC05',
    b'DC006': b'DC06',
    b'DC007': b'DC07',
    b'DC008': b'DC08',
    b'DC009': b'DC09',
    b'DC011': b'DC11',
    b'DC012': b'DC12',
    b'DC013': b'DC13',
}


def _parse_error_codes(matches_dict: Dict[str, bytes]) -> List[bytes]:
    # If no error code is specified, add the line to the "all" category.
    return [c.strip() for c in (matches_dict['codes'] or b'all').split(b',')]


def parse_noqa(code: bytes) -> Dict[bytes, Set[int]]:
    noqa_lines = defaultdict(set)
    for lineno, line in enumerate(code.split(b'\n'), start=1):
        match = NOQA_REGEXP.search(line)
        if match:
            for error_code in _parse_error_codes(match.groupdict()):
                error_code = NOQA_CODE_MAP.get(error_code, error_code)
                noqa_lines[error_code].add(lineno)
    return noqa_lines


def ignore_line(noqa_lines: Dict[bytes, Set[int]], lineno: int, error_code: bytes) -> bool:
    """Check if the reported line is annotated with "# noqa"."""
    return lineno in noqa_lines[error_code] or lineno in noqa_lines[b'all']
