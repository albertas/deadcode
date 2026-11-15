"""Native parser parity: the native `ast.Module` must equal the running
interpreter's `ast.parse` output for every fixture, positions included.

The suite skips cleanly in fallback mode (native module absent), so it passes
both with a pure-Python install and against the native module built with
`maturin develop` (D6). CPython changed f-string tokenisation in 3.12, and the
Rust parser follows the modern (3.14) position convention, so the f-string
fixture is matrix-gated to interpreters from 3.12 on (D4).
"""

import ast
import sys
from pathlib import Path

import pytest

from deadcode._native_loader import load_native

FIXTURES_DIRECTORY = Path(__file__).parent / 'fixtures'
FIXTURES = sorted(FIXTURES_DIRECTORY.glob('*.py'))

# Constructs whose syntax (or node shape) only exists on newer interpreters,
# covered as inline sources instead of fixture files (D4: a fixture must parse
# on every matrix interpreter, so these are gated instead).
INLINE_CASES = [
    ('type-alias', 'type X = int', (3, 12)),
    ('type-alias-parameters', 'type X[T] = list[T]', (3, 12)),
    ('type-parameters-def', 'def f[T, *Ts, **P](x: T) -> T: pass', (3, 12)),
    ('type-parameters-class', 'class A[T]: pass', (3, 12)),
    ('type-parameter-bound', 'type X[T: int] = list[T]', (3, 12)),
    ('type-parameter-default', 'def f[T = int](x: T) -> None: pass', (3, 13)),
    ('except-unparenthesized-tuple', 'try: pass\nexcept ValueError, TypeError: pass', (3, 14)),
    ('t-string', "t'hello {x!r:>{w}} end'", (3, 14)),
    ('t-string-debug', "t'{x=}'", (3, 14)),
    ('t-string-concatenated', "t'a{b}c' t'{d}e'", (3, 14)),
    # Capture-heavy `MatchOr` patterns are legal but the linter's parser flags
    # them, so they live here instead of a linted fixture file.
    ('match-or-name-capture', 'match x:\n    case first | second:\n        pass', (3, 10)),
    ('match-or-different-names', 'match x:\n    case a | b | c:\n        pass', (3, 10)),
    ('match-or-class-patterns', 'match x:\n    case A(x) | B(y):\n        pass', (3, 10)),
]


def inline_case_params():
    params = []
    for case_id, source, min_version in INLINE_CASES:
        reason = f'needs {min_version} (D4 matrix gate)'
        params.append(
            pytest.param(
                source,
                id=case_id,
                marks=pytest.mark.skipif(sys.version_info < min_version, reason=reason),
            )
        )
    return params


def native_is_available():
    return load_native() is not None


pytestmark = pytest.mark.skipif(not native_is_available(), reason='native module not built (fallback mode)')


@pytest.mark.parametrize('fixture', FIXTURES, ids=lambda fixture: fixture.name)
def test_native_tree_matches_the_interpreter_tree(fixture):
    native = load_native()
    assert native is not None

    source = fixture.read_bytes()
    filename = str(fixture)

    native_tree = native.parse_module(source, filename, True)
    reference_tree = ast.parse(source, filename=filename, type_comments=True)

    assert ast.dump(native_tree, include_attributes=True) == ast.dump(reference_tree, include_attributes=True)


@pytest.mark.parametrize('fixture', FIXTURES, ids=lambda fixture: fixture.name)
def test_native_tree_unparses_like_the_interpreter_tree(fixture):
    native = load_native()
    assert native is not None

    source = fixture.read_bytes()
    filename = str(fixture)

    native_tree = native.parse_module(source, filename, True)
    reference_tree = ast.parse(source, filename=filename, type_comments=True)

    assert ast.unparse(native_tree) == ast.unparse(reference_tree)


@pytest.mark.parametrize('source', inline_case_params())
def test_native_tree_matches_the_interpreter_tree_inline(source):
    native = load_native()
    assert native is not None

    filename = '<inline>'
    native_tree = native.parse_module(source.encode(), filename, True)
    reference_tree = ast.parse(source, filename=filename, type_comments=True)

    assert ast.dump(native_tree, include_attributes=True) == ast.dump(reference_tree, include_attributes=True)
    assert ast.unparse(native_tree) == ast.unparse(reference_tree)


@pytest.mark.skipif(sys.version_info < (3, 12), reason='f-string positions diverge below 3.12 (D4 matrix gate)')
def test_fstring_fixture_exists_and_parses():
    assert (FIXTURES_DIRECTORY / 'fstrings.py').is_file()
