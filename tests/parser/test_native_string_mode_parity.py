"""String-mode parity for the native parse entry points (D5 item 4).

The three string-mode `ast.parse` call sites route through `_native_parse`:
commented-out-code candidates (eval, then exec), the type-comment re-parse
in `visit()` (func_type for definitions, eval otherwise) and
annotation-string name collection (eval).

The dispatch is tested against a stub native module so the seam behaves the
same when the real module is absent (fallback mode, D6); the parity matrix
below runs only when the native module is built.
"""

import ast
from types import SimpleNamespace

import pytest

from deadcode._native_loader import load_native
from deadcode.actions import parse_abstract_syntax_tree as seam
from deadcode.actions.parse_abstract_syntax_tree import (  # noqa: PLC2701
    _native_parse,
)
from deadcode.data_types import Args
from deadcode.visitor.dead_code_visitor import DeadCodeVisitor
from deadcode.visitor.utils import collect_names_from_annotation_strings

FILENAME = 'example.py'


class NativeParseError(Exception):
    """Mimics the `ParseError` exception the native module defines."""


def dump(node):
    return ast.dump(node, include_attributes=True)


def seam_parse(source: str, mode: str):
    """`_native_parse` with a rejection reported as None, like the call sites see it."""
    try:
        return _native_parse(mode, source, FILENAME)
    except SyntaxError:
        return None


def reference_parse(source: str, mode: str):
    try:
        return ast.parse(source, filename=FILENAME, mode=mode)
    except SyntaxError:
        return None


# -- dispatch: stub native module -------------------------------------------


def make_native_stub():
    """A stub native module with one recorder per entry point."""
    calls = []

    def make_entry_point(name):
        def entry_point(source, filename):
            calls.append((name, source, filename))
            return f'{name} tree'

        return entry_point

    stub = SimpleNamespace(
        ParseError=NativeParseError,
        **{name: make_entry_point(name) for name in ('parse_expression', 'parse_statement', 'parse_func_type')},
    )
    return stub, calls


@pytest.mark.parametrize(
    ('mode', 'entry_point'),
    [('eval', 'parse_expression'), ('exec', 'parse_statement'), ('func_type', 'parse_func_type')],
)
def test_native_parse_routes_to_the_mode_entry_point(monkeypatch, mode, entry_point):
    stub, calls = make_native_stub()
    monkeypatch.setattr(seam, 'load_native', lambda: stub)

    result = _native_parse(mode, 'source', FILENAME)

    assert result == f'{entry_point} tree'
    assert calls == [(entry_point, 'source', FILENAME)]


@pytest.mark.parametrize('mode', ['eval', 'exec', 'func_type'])
def test_native_parse_rejection_raises_syntax_error(monkeypatch, mode):
    def reject(source, filename):
        raise NativeParseError

    stub = SimpleNamespace(
        ParseError=NativeParseError,
        parse_expression=reject,
        parse_statement=reject,
        parse_func_type=reject,
    )
    monkeypatch.setattr(seam, 'load_native', lambda: stub)

    with pytest.raises(SyntaxError):
        _native_parse(mode, 'source', FILENAME)


SOURCES_PER_MODE = {'eval': '1 + 2', 'exec': 'x = 1', 'func_type': '() -> int'}


@pytest.mark.parametrize('mode', ['eval', 'exec', 'func_type'])
def test_native_give_up_falls_back_to_ast_parse(monkeypatch, mode):
    def give_up(source, filename):
        raise RuntimeError

    stub = SimpleNamespace(
        ParseError=NativeParseError,
        parse_expression=give_up,
        parse_statement=give_up,
        parse_func_type=give_up,
    )
    monkeypatch.setattr(seam, 'load_native', lambda: stub)

    result = _native_parse(mode, SOURCES_PER_MODE[mode], FILENAME)

    assert dump(result) == dump(ast.parse(SOURCES_PER_MODE[mode], mode=mode))


def test_native_give_up_on_unparseable_source_raises_syntax_error(monkeypatch):
    def give_up(source, filename):
        raise RuntimeError

    stub = SimpleNamespace(
        ParseError=NativeParseError,
        parse_expression=give_up,
        parse_statement=give_up,
        parse_func_type=give_up,
    )
    monkeypatch.setattr(seam, 'load_native', lambda: stub)

    with pytest.raises(SyntaxError):
        _native_parse('func_type', 'garbage', FILENAME)


def test_native_module_absent_falls_back_to_ast_parse(monkeypatch):
    monkeypatch.setattr(seam, 'load_native', lambda: None)

    result = _native_parse('eval', '1 + 2', FILENAME)

    assert dump(result) == dump(ast.parse('1 + 2', mode='eval'))


# -- node shapes per mode -----------------------------------------------------


@pytest.mark.parametrize(
    ('mode', 'source', 'expected_class'),
    [
        ('eval', '1 + 2', ast.Expression),
        ('exec', 'value = 1', ast.Module),
        ('func_type', '(int) -> int', ast.FunctionType),
    ],
)
def test_each_mode_returns_the_reference_node_shape(mode, source, expected_class):
    result = _native_parse(mode, source, FILENAME)

    assert isinstance(result, expected_class)
    assert dump(result) == dump(ast.parse(source, mode=mode))


# -- call-site behaviour ------------------------------------------------------


def test_commented_out_code_items_are_produced_from_the_rewired_sites(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b'print("Keep")\n# print("Hello world")\n# x = 1\n# just text\n',
    }

    visitor = DeadCodeVisitor(['foo.py'], Args())
    visitor.visit_abstract_syntax_trees()

    items = visitor.commented_out_code
    assert [(item.name, item.name_line, item.code_parts) for item in items] == [
        ('print("Hello world")', 2, [(2, 2, 0, 22)]),
        ('x = 1', 3, [(3, 3, 0, 7)]),
    ]


def test_comment_candidates_keep_their_eval_then_exec_contract(virtual_file_system):
    # A bare constant or name parses as an expression and is not commented-out
    # code; a statement that only parses in exec mode is.
    virtual_file_system.files = {
        'foo.py': b'# some_name\n# 1 + 1\n# value = 1\n',
    }

    visitor = DeadCodeVisitor(['foo.py'], Args())
    visitor.visit_abstract_syntax_trees()

    assert [item.name for item in visitor.commented_out_code] == ['value = 1']


def test_annotation_string_names_are_collected_to_depth_ten():
    def chain(depth):
        if depth == 0:
            return 'N'
        return f'A{depth} + ' + repr(chain(depth - 1))

    annotation = ast.parse(chain(11), mode='eval').body
    names = collect_names_from_annotation_strings(annotation)

    assert names == {f'A{level}' for level in range(1, 11)}


def test_annotation_string_names_stop_at_the_depth_limit():
    def chain(depth):
        if depth == 0:
            return 'N'
        return f'A{depth} + ' + repr(chain(depth - 1))

    annotation = ast.parse(chain(10), mode='eval').body
    names = collect_names_from_annotation_strings(annotation)

    # The innermost level is reachable when the chain fits the limit.
    assert 'N' in names
    assert 'A10' not in names


def test_def_type_comment_reparse_keeps_the_referenced_definitions(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': (
            b'class Handler:\n'
            b'    pass\n'
            b'\n'
            b'\n'
            b'class Result:\n'
            b'    pass\n'
            b'\n'
            b'\n'
            b'def typed(value):\n'
            b'    # type: (Handler) -> Result\n'
            b'    return value\n'
            b'\n'
            b'\n'
            b'typed(1)\n'
        ),
    }

    visitor = DeadCodeVisitor(['foo.py'], Args())
    visitor.visit_abstract_syntax_trees()

    names = {item.name for item in visitor.get_unused_code_items()}
    assert 'Handler' not in names
    assert 'Result' not in names


# -- parity matrix (native mode only) -----------------------------------------

requires_native = pytest.mark.skipif(load_native() is None, reason='native module not built (fallback mode)')

PARITY_CASES = {
    'eval': [
        'x',
        '1+2',
        'x.attr[0]',
        'f(x)',
        '(lambda: 0)',
        'x if y else z',
        'not x',
        '-x',
        "'str'",
        "b'x'",
        "f'{x}'",
        "t'{x}'",
        "f'{x=}'",
        "f'{x!r}'",
        "f'{x:{w}}'",
        '[x for x in y]',
        '{x: y for x in y}',
        '(x := 1)',
        '*x',
        'x,',
        'None,',
        'x;',
        'x = 1',
        'import x',
        'del x',
        'yield',
        'await x',
        'x # c',
        'x\n',
        'x\n\n',
        'x\n\n\n',
        '\nx',
        '\n\nx',
        '\n x',
        ' x',
        '\tx',
        '\n\tx',
        '  x',
        '\x0cx',
        '\x0c x',
        '',
        '\n',
        '# c',
        '# c\nx',
        'x\n# c',
        'x\n\n# c',
        'x[',
        "f'{",
        '(x',
        'a b',
        '\ufeffx',
        'x  # noqa',
        'x @ y',
        'x ** -1',
        '(x)',
        '((x))',
        '()',
        '(,)',
        'x@',
        "'a' 'b'",
        '0x1f',
        '1_000',
        '1j',
        '3.14',
        'True',
        'None',
        '...',
        'x[1:2:3]',
        'x[y]',
        'list[int]',
        'Optional[Model]',
        "'Model'",
        "dict[str, 'Inner']",
        "'a' if b else 'c'",
    ],
    'exec': [
        'x = 1',
        'a; b',
        'def f():\n    pass',
        'if x:\n    pass',
        'import x\nimport y',
        'from x import y',
        'import os  # type: int',
        'x = 1\n\n\n',
        '',
        '\n\n',
        '# only comment',
        '  x = 1',
        '\tx = 1',
        '\n  x = 1',
        '\n\nx = 1\n\n',
        'return 1',
        'yield 1',
        'a\n\nb',
        'class A:\n    pass',
        'try:\n    pass\nexcept:\n    pass',
        'try:\n    pass\nexcept* Exception:\n    pass',
        'with x:\n    pass',
        'for i in x:\n    pass',
        'for i in x:\n    pass\nelse:\n    pass',
        'while x:\n    pass',
        'del x',
        'global x',
        'nonlocal x',
        'assert x',
        'raise',
        'pass',
        'break',
        'continue',
        'x := 1',
        'match x:\n    case 1:\n        pass',
        'match x:\n    case _:\n        pass',
        'async def f():\n    pass',
        'def f() -> int:\n    pass',
        'type X = int',
        'x: int = 1',
        'if True: pass',
        'if x: pass; pass',
        "f'{x'",
        'x[',
        'a b',
        '\ufeffx = 1',
        'x = 1 # c',
        'x = 1\n# c',
        'from x import *',
        'print(1, 2)',
        'x = ',
        '= 1',
        '1 + 1',
    ],
    'func_type': [
        '() -> None',
        '(int) -> str',
        '(int, str) -> bool',
        '(*args) -> None',
        '(**kwargs) -> None',
        '(int, *args) -> None',
        '(*args, **kwargs) -> None',
        '(int, *args, **kwargs) -> None',
        '(...) -> None',
        '(int) ->\nstr',
        '  ()  ->  None  ',
        '()->None',
        '(a b) -> None',
        '(int,) -> None',
        '(,) -> None',
        '-> None',
        '(int) ->',
        '',
        'None',
        'int',
        '(*, int) -> None',
        '(**kwargs, int) -> None',
        '(*int) -> None',
        '(**int) -> None',
        '(int) -> *str',
        '(() ) -> None',
        '(*args, int, **kw) -> None',
        '(int)->None',
        '(*) -> None',
        '(**kw, **kw2) -> None',
        '(*a, *b) -> None',
        '(int * 3) -> None',
        '(int ** 2) -> None',
        '(**f(1)) -> None',
        '(*[1, 2]) -> None',
        '(*x.y) -> None',
        '((yield)) -> None',
        '(yield) -> None',
        '(x := 1) -> None',
        ' (int) -> str',
        '(int,\n str) -> bool',
        '(int\n) -> None',
        '(int) -> None,',
        '(int) -> None # c',
        '(int) -> str  ',
        '\t(int) -> str',
        '(int ,) -> None',
        '(int) -> ((int))',
        '(a[0]) -> None',
        '(Optional[int], Dict[str, int]) -> None',
        "(int) -> 'Name'",
        '(Callable[[int], str]) -> None',
        '(int, str, bool, float) -> None',
        '(*args: int, **kwargs: int) -> None',
        '(int) -> None\n',
        '(int) -> None\n# c',
        '(int) -> None\nx = 1',
        '\ufeff(int) -> None',
        '(int) -> None\x0c',
        '\x0c(int) -> None',
        '\x0c x',
        '( ** int) -> None',
        '( * int) -> None',
        '(int)  ->  None',
        '()\n-> None',
        '(int)\n-> None',
        '(int) ->None',
        '(int)-> None',
        '(  ) -> None',
        '(int) -> ()',
        '() -> ()',
        '(int) -> (int\n)',
        '(int) -> f(\n1)',
        '(int) -> {1: 2}',
        "(int, 1, 'x') -> None",
        '(*, ) -> None',
        '(**, int) -> None',
        '(int, *, **kw) -> None',
        '(int) -> str; x',
        '(int)\n\n-> None',
        '(int, ,) -> None',
        '(int, str,) -> None',
        '(  int  ) -> None',
        '(int) -> (  None  )',
        '(int) -> None  # type: ignore',
        '(\n) -> None',
        '(int) -> None, x',
        '(int) -> x, y',
        '(int) -> (x, y)',
        '(int) -> ()x',
    ],
}


@requires_native
@pytest.mark.parametrize('mode', ['eval', 'exec', 'func_type'])
def test_native_string_modes_agree_with_the_running_interpreter(mode):
    for source in PARITY_CASES[mode]:
        reference = reference_parse(source, mode)
        parsed = seam_parse(source, mode)
        if reference is None:
            assert parsed is None, f'native accepted what the reference rejects: {source!r}'
        else:
            assert parsed is not None, f'native rejected what the reference accepts: {source!r}'
            assert dump(parsed) == dump(reference), f'trees differ for: {source!r}'
