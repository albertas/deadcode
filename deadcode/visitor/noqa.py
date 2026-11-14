from collections import defaultdict
import io
import re
import tokenize

from deadcode import _native_loader

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


def _parse_error_codes(matches_dict: dict[str, bytes]) -> list[bytes]:
    # If no error code is specified, add the line to the "all" category.
    return [c.strip() for c in (matches_dict['codes'] or b'all').split(b',')]


def parse_noqa(code: bytes, tokens: list[tokenize.TokenInfo] | None = None) -> dict[bytes, set[int]]:
    """Derive the `# noqa` suppression map from ``code``.

    Without ``tokens`` the regex is applied to every raw line, byte-for-byte as
    before. With a precomputed token stream (D10): lines carrying a
    ``tokenize.COMMENT`` token are matched against that token's `#`-prefixed
    comment text only; lines without a comment token fall back to the raw line.
    Pass ``tokens=None`` when tokenisation failed to keep the raw-line result.
    """
    noqa_lines: dict[bytes, set[int]] = defaultdict(set)
    if tokens is None:
        for lineno, line in enumerate(code.split(b'\n'), start=1):
            _match_noqa_line(noqa_lines, lineno, line)
        return noqa_lines

    commented_lines = {token.start[0] for token in tokens if token.type == tokenize.COMMENT}
    for lineno, line in enumerate(code.split(b'\n'), start=1):
        if lineno not in commented_lines:
            _match_noqa_line(noqa_lines, lineno, line)
    encoding = tokens[0].string if tokens and tokens[0].type == tokenize.ENCODING else 'utf-8'
    for token in tokens:
        if token.type == tokenize.COMMENT:
            # Comment tokens are decoded strings; re-encoding with the stream's
            # detected encoding restores the file bytes losslessly.
            _match_noqa_line(noqa_lines, token.start[0], token.string.encode(encoding))
    return noqa_lines


def _match_noqa_line(noqa_lines: dict[bytes, set[int]], lineno: int, line: bytes) -> None:
    match = NOQA_REGEXP.search(line)
    if match:
        for error_code in _parse_error_codes(match.groupdict()):
            error_code = NOQA_CODE_MAP.get(error_code, error_code)
            noqa_lines[error_code].add(lineno)


def ignore_line(noqa_lines: dict[bytes, set[int]], lineno: int, error_code: bytes) -> bool:
    """Check if the reported line is annotated with "# noqa"."""
    return lineno in noqa_lines[error_code] or lineno in noqa_lines[b'all']


def scan_comments_and_noqa(code: bytes) -> tuple[list[tokenize.TokenInfo], dict[bytes, set[int]]]:
    """One pass over ``code`` collecting COMMENT tokens and the `# noqa` map.

    Dispatch seam for the native comment/noqa scanner (D5): when the
    ``deadcode._native`` extension is installed and exposes ``scan_comments``,
    both results are produced from the raw file bytes in Rust; otherwise (or
    when the native scanner cannot guarantee parity and returns ``None``) the
    pure-Python ``tokenize`` pass and ``parse_noqa`` run unchanged as the
    automatic fallback.
    """
    native = _native_loader._native  # noqa: SLF001
    scan = getattr(native, 'scan_comments', None) if native is not None else None
    if scan is not None:
        native_result = scan(code)
        if native_result is not None:
            comments, native_noqa_lines = native_result
            comment_tokens = [
                tokenize.TokenInfo(
                    tokenize.COMMENT,
                    text,
                    (lineno, column),
                    (lineno, column + len(text)),
                    '',
                )
                for lineno, column, text in comments
            ]
            # parse_noqa returns a defaultdict; keep that contract so
            # ignore_line can create missing entries without KeyError.
            return comment_tokens, defaultdict(set, native_noqa_lines)

    try:
        tokens = list(tokenize.tokenize(io.BytesIO(code).readline))
    except (tokenize.TokenError, IndentationError):
        tokens = None
    noqa_lines = parse_noqa(code, tokens)
    if tokens is None:
        return [], noqa_lines
    return [token for token in tokens if token.type == tokenize.COMMENT], noqa_lines
