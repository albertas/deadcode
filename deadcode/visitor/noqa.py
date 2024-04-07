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
    r'# noqa(?::[\s]?(?P<codes>([A-Z]+[0-9]+(?:[,\s]+)?)+))?',
    re.IGNORECASE,
)

NOQA_CODE_MAP = {
    # flake8 F401: module imported but unused.
    'F401': 'DC07',
    # flake8 F841: local variable is assigned to but never used.
    'F841': 'DC01',
    'DC01': 'DC01',
    'DC02': 'DC02',
    'DC03': 'DC03',
    'DC04': 'DC04',
    'DC05': 'DC05',
    'DC06': 'DC06',
    'DC07': 'DC07',
    'DC08': 'DC08',
    'DC09': 'DC09',
    'DC11': 'DC11',
    'DC12': 'DC12',
    'DC13': 'DC13',
    # For backward compatibility
    'DC001': 'DC01',
    'DC002': 'DC02',
    'DC003': 'DC03',
    'DC004': 'DC04',
    'DC005': 'DC05',
    'DC006': 'DC06',
    'DC007': 'DC07',
    'DC008': 'DC08',
    'DC009': 'DC09',
    'DC011': 'DC11',
    'DC012': 'DC12',
    'DC013': 'DC13',
}


def _parse_error_codes(matches_dict: Dict[str, str]) -> List[str]:
    # If no error code is specified, add the line to the "all" category.
    return [c.strip() for c in (matches_dict['codes'] or 'all').split(',')]


def parse_noqa(code: str) -> Dict[str, Set[int]]:
    noqa_lines = defaultdict(set)
    for lineno, line in enumerate(code.split('\n'), start=1):
        match = NOQA_REGEXP.search(line)
        if match:
            for error_code in _parse_error_codes(match.groupdict()):
                error_code = NOQA_CODE_MAP.get(error_code, error_code)
                noqa_lines[error_code].add(lineno)
    return noqa_lines


def ignore_line(noqa_lines: Dict[str, Set[int]], lineno: int, error_code: str) -> bool:
    """Check if the reported line is annotated with "# noqa"."""
    return lineno in noqa_lines[error_code] or lineno in noqa_lines['all']
