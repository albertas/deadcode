"""Dispatch tests for the native comment/`noqa` scan (spec slice 6).

The Rust scanner's behavioural parity is verified against the real corpus by
the benchmark parity harness; these tests pin the dispatch seam itself: the
native result flows through the wrapper unchanged, and every unavailable-native
condition falls back to the pure-Python `tokenize` path.
"""

import tokenize
from types import ModuleType

from deadcode import _native_loader
from deadcode.data_types import Args
from deadcode.visitor import noqa
from deadcode.visitor.dead_code_visitor import DeadCodeVisitor

CODE = b'import os  # noqa: F401\nprint(os)\n'


def _install_native_stub(monkeypatch, scan_comments) -> ModuleType:
    stub = ModuleType('deadcode._native')
    if scan_comments is not None:
        stub.scan_comments = scan_comments  # type: ignore[attr-defined]
    monkeypatch.setattr(_native_loader, '_native', stub)
    return stub


def test_native_scan_result_flows_through_unchanged(monkeypatch):
    # Having: a native scanner returning a marker result that real scanning of
    # the input could never produce.
    calls: list[bytes] = []

    def fake_scan(code: bytes):
        calls.append(code)
        return ([(1, 7, '# marker comment')], {b'DC01': {99}})

    _install_native_stub(monkeypatch, fake_scan)

    # When
    comment_tokens, noqa_lines = noqa.scan_comments_and_noqa(b'x = 1\n# placeholder\n')

    # Then: the code reached the native scanner and its results pass through.
    assert calls == [b'x = 1\n# placeholder\n']
    assert noqa_lines == {b'DC01': {99}}
    assert len(comment_tokens) == 1
    token = comment_tokens[0]
    assert token.type == tokenize.COMMENT
    assert token.string == '# marker comment'
    assert token.start == (1, 7)
    assert token.end == (1, 7 + len(token.string))


def test_native_result_map_keeps_defaultdict_contract(monkeypatch):
    # The native map is a plain dict; ignore_line must be able to create the
    # missing entries of any error code without KeyError (parse_noqa contract).
    _install_native_stub(monkeypatch, lambda _code: ([], {}))

    _, noqa_lines = noqa.scan_comments_and_noqa(CODE)

    assert noqa_lines[b'DC12'] == set()


def test_native_comment_tokens_feed_commented_out_code(monkeypatch):
    # Having: a native scanner that reports a commented-out-code token.
    _install_native_stub(
        monkeypatch,
        lambda _code: ([(1, 0, '# print("Hello world")')], {}),
    )
    visitor = DeadCodeVisitor(filenames=[], args=Args())
    visitor.filename = 'native_commented.py'

    # When
    code = b'# print("Hello world")\n'
    comment_tokens, noqa_lines = noqa.scan_comments_and_noqa(code)
    visitor.noqa_lines = noqa_lines
    visitor._collect_commented_out_code(code, comment_tokens)  # noqa: SLF001

    # Then: the native token produces the same finding as the Python scanner.
    assert len(visitor.commented_out_code) == 1
    assert visitor.commented_out_code[0].name == 'print("Hello world")'


def test_visitor_dispatches_through_native_scan(virtual_file_system, monkeypatch):
    # Having: a virtual file analysed end-to-end while the native scan is active.
    def fake_scan(_code: bytes):
        return ([(2, 0, '# print("Hello world")')], {})

    _install_native_stub(monkeypatch, fake_scan)
    virtual_file_system.files = {'native_module.py': b'x = 1\n# print("Hello world")\n'}

    # When
    visitor = DeadCodeVisitor(filenames=['native_module.py'], args=Args())
    visitor.visit_abstract_syntax_trees()

    # Then
    assert len(visitor.commented_out_code) == 1
    assert visitor.commented_out_code[0].name == 'print("Hello world")'


def test_python_fallback_runs_without_native_module(monkeypatch):
    monkeypatch.setattr(_native_loader, '_native', None)

    comment_tokens, noqa_lines = noqa.scan_comments_and_noqa(CODE)

    assert noqa_lines == {b'DC07': {1}}
    assert [token.string for token in comment_tokens] == ['# noqa: F401']


def test_fallback_when_native_module_lacks_scanner(monkeypatch):
    _install_native_stub(monkeypatch, None)

    comment_tokens, noqa_lines = noqa.scan_comments_and_noqa(CODE)

    assert noqa_lines == {b'DC07': {1}}
    assert [token.string for token in comment_tokens] == ['# noqa: F401']


def test_fallback_when_native_scan_cannot_guarantee_parity(monkeypatch):
    # The native scanner returns None when the encoding cannot be replicated;
    # the wrapper must then fall back to the Python implementation.
    _install_native_stub(monkeypatch, lambda _code: None)

    comment_tokens, noqa_lines = noqa.scan_comments_and_noqa(CODE)

    assert noqa_lines == {b'DC07': {1}}
    assert [token.string for token in comment_tokens] == ['# noqa: F401']


def test_fallback_tokenization_failure_yields_raw_line_map(monkeypatch):
    monkeypatch.setattr(_native_loader, '_native', None)
    code = b'def f():\n    return 1  # noqa: DC01\n  broken_dedent = 2\n'

    comment_tokens, noqa_lines = noqa.scan_comments_and_noqa(code)

    assert comment_tokens == []
    assert noqa_lines == {b'DC01': {2}}


def test_in_string_noqa_divergence_survives_dispatch(monkeypatch):
    # The D10 divergence candidate is pinned through the dispatch wrapper too:
    # an in-string `# noqa` on a commented line is suppressed only via the
    # comment text, not the raw line.
    _install_native_stub(
        monkeypatch,
        lambda _code: ([(1, 24, '# trailing comment')], {}),
    )

    _, noqa_lines = noqa.scan_comments_and_noqa(b'value = "# noqa: F401"  # trailing comment\n')

    assert noqa_lines == {}
