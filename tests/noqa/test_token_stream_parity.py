"""Parity tests for the merged comment/noqa token stream (spec D10).

`parse_noqa` without tokens applies `NOQA_REGEXP` to every raw line. With a
precomputed token stream, lines carrying a `tokenize.COMMENT` token are matched
against that token's `#`-prefixed comment text only, and lines without a comment
token fall back to the raw line. These tests pin the token-stream derivation
against the untokenized behaviour.
"""

import io
import tokenize
from pathlib import Path

from deadcode.data_types import Args
from deadcode.visitor import noqa
from deadcode.visitor.dead_code_visitor import DeadCodeVisitor


def tokenize_source(code: bytes) -> list[tokenize.TokenInfo] | None:
    """Tokenize the way DeadCodeVisitor does; `None` on tokenisation failure."""
    try:
        return list(tokenize.tokenize(io.BytesIO(code).readline))
    except (tokenize.TokenError, IndentationError):
        return None


def assert_noqa_parity(code: bytes) -> None:
    assert noqa.parse_noqa(code, tokenize_source(code)) == noqa.parse_noqa(code)


def test_trailing_noqa_comment_parity():
    # Having
    code = b'import os  # noqa: F401\nprint(os)\n'

    # When / Then: both derivations agree, and the token-stream one maps the code.
    assert_noqa_parity(code)
    assert noqa.parse_noqa(code, tokenize_source(code)) == {b'DC07': {1}}


def test_comment_only_lines_parity():
    assert_noqa_parity(b'# noqa: DC01\nvalue = 1  # noqa: DC02\n# plain comment\n')


def test_noqa_without_codes_parity():
    assert_noqa_parity(b'instance = "labas"  # noqa\n')


def test_file_without_comments_parity():
    # Having
    code = b'value = 1\nother = 2\nresult = value + other\n'

    # When / Then: no comment tokens, no raw matches, both results empty.
    assert_noqa_parity(code)
    assert noqa.parse_noqa(code, tokenize_source(code)) == {}


def test_in_string_noqa_without_comment_token_parity():
    # Having: `# noqa` inside a string literal on a line with no real comment.
    code = b'warning = "# noqa: F401"\n'

    # When / Then: no COMMENT token, so the raw-line fallback matches in both.
    assert_noqa_parity(code)
    assert noqa.parse_noqa(code, tokenize_source(code)) == {b'DC07': {1}}


def test_in_string_noqa_with_trailing_comment_pins_d10_divergence():
    # Having: `# noqa` inside a string on a line that also carries a trailing
    # comment — the only divergence candidate recorded in D10.
    code = b'value = "# noqa: F401"  # trailing comment\n'

    # Then: the raw-line derivation suppresses the line; the token-stream
    # derivation matches the comment text (`# trailing comment`) only.
    assert noqa.parse_noqa(code) == {b'DC07': {1}}
    assert noqa.parse_noqa(code, tokenize_source(code)) == {}


def test_multiline_string_noqa_parity():
    # Having: `# noqa` inside a triple-quoted string — those lines carry no
    # COMMENT token, so both derivations match the raw lines.
    assert_noqa_parity(b'text = """\n# noqa: DC01\n"""\n')


def test_tokenization_failure_keeps_raw_line_result():
    # Having: a mismatched dedent makes tokenize fail with an IndentationError,
    # but the noqa marker on earlier lines must survive via the raw-line path.
    code = b'def f():\n    return 1  # noqa: DC01\n  broken_dedent = 2\n'
    assert tokenize_source(code) is None

    # Then: passing no tokens keeps the untokenized result byte-for-byte.
    assert noqa.parse_noqa(code, None) == noqa.parse_noqa(code) == {b'DC01': {2}}


def test_tokenization_failure_collects_no_commented_out_code():
    # Having: a visitor whose file tokenisation failed contributes no comment
    # tokens, so commented-out-code collection stays empty (old error path).
    visitor = DeadCodeVisitor(filenames=[], args=Args())
    visitor.filename = 'broken.py'

    # When
    visitor._collect_commented_out_code(b'print("Keep")\n  pass\n', [])  # noqa: SLF001

    # Then
    assert visitor.commented_out_code == []


def test_commented_out_code_with_token_stream_matches_untokenized():
    # Having
    visitor_tokenized = DeadCodeVisitor(filenames=[], args=Args())
    visitor_tokenized.filename = 'commented.py'
    visitor_tokenized.noqa_lines = noqa.parse_noqa(
        b'# print("Hello world")\n', tokenize_source(b'# print("Hello world")\n')
    )

    visitor_untokenized = DeadCodeVisitor(filenames=[], args=Args())
    visitor_untokenized.filename = 'commented.py'
    visitor_untokenized.noqa_lines = noqa.parse_noqa(b'# print("Hello world")\n')

    # When
    code = b'# print("Hello world")\n'
    comment_tokens = [token for token in tokenize_source(code) if token.type == tokenize.COMMENT]
    visitor_tokenized._collect_commented_out_code(code, comment_tokens)  # noqa: SLF001
    visitor_untokenized._collect_commented_out_code(code, comment_tokens)  # noqa: SLF001

    # Then: same commented-out-code finding from the shared token stream.
    assert len(visitor_tokenized.commented_out_code) == len(visitor_untokenized.commented_out_code) == 1
    assert visitor_tokenized.commented_out_code[0].name == visitor_untokenized.commented_out_code[0].name


def test_real_corpus_files_parity():
    """A sample of real repository fixture files agrees under both derivations."""
    files_dir = Path(__file__).parents[1] / 'files'
    samples = [
        files_dir / 'classes.py',
        files_dir / 'variables.py',
        files_dir / 'django' / 'models.py',
        files_dir / 'django' / 'settings.py',
        files_dir / 'fastapi_features' / 'routes' / 'items.py',
        files_dir / 'fastapi_dependency_injection' / 'security.py',
    ]
    for path in samples:
        code = path.read_bytes()
        assert_noqa_parity(code)
