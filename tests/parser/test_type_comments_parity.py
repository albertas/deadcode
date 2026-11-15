"""Type-comment contract parity (D8): with `type_comments=True`, the native
parser must attach `# type:` comments to the same nodes as the running
interpreter — and reject the same sources.

The suite skips cleanly in fallback mode (native module absent), so it passes
both with a pure-Python install and against the native module built with
`maturin develop` (D6).
"""

import ast

import pytest

from deadcode._native_loader import load_native
from deadcode.actions.parse_abstract_syntax_tree import parse_abstract_syntax_tree
from deadcode.data_types import Args

pytestmark = pytest.mark.skipif(load_native() is None, reason='native module not built (fallback mode)')


def dumps(source):
    """Both trees as `ast.dump` strings; a rejected parse reports None.

    Returns a tuple of (reference dump or None, native dump or None).
    """
    native = load_native()
    assert native is not None
    try:
        reference = ast.parse(source, filename='<test>', type_comments=True)
    except SyntaxError:
        reference = None
    try:
        tree = native.parse_module(source.encode(), '<test>', True)
    except native.ParseError:
        tree = None
    return (
        None if reference is None else ast.dump(reference, include_attributes=True),
        None if tree is None else ast.dump(tree, include_attributes=True),
    )


def both_reject(source):
    reference, native_tree = dumps(source)
    assert reference is None, f'expected the reference parse to fail: {source!r}'
    assert native_tree is None, f'expected the native parse to fail: {source!r}'


def ignore_tags(tree):
    return [(ignore.lineno, ignore.tag) for ignore in tree.type_ignores]


def both_agree(source):
    reference, native_tree = dumps(source)
    assert reference is not None, f'expected the reference parse to succeed: {source!r}'
    assert native_tree is not None, f'expected the native parse to succeed: {source!r}'
    assert native_tree == reference


# -- attachment positions ---------------------------------------------------


def test_trailing_comment_attaches_to_the_assignment():
    both_agree('value = 1  # type: int')
    tree = ast.parse('value = 1  # type: int', type_comments=True)
    statement = tree.body[0]
    assert statement.type_comment == 'int'


def test_last_assignment_on_a_multi_statement_line_wins():
    both_agree('first = 1; second = 2  # type: int')
    tree = ast.parse('first = 1; second = 2  # type: int', type_comments=True)
    assert tree.body[0].type_comment is None
    assert tree.body[1].type_comment == 'int'


def test_assignment_inside_a_one_line_suite_attaches():
    both_agree('if True: value = 1  # type: int')
    tree = ast.parse('if True: value = 1  # type: int', type_comments=True)
    assert tree.body[0].body[0].type_comment == 'int'


def test_trailing_comment_extends_the_statement_and_its_parents():
    both_agree('if True: value = 1  # type: int')
    tree = ast.parse('if True: value = 1  # type: int', type_comments=True)
    statement = tree.body[0].body[0]
    assert statement.end_col_offset == len('if True: value = 1  # type: int')
    assert tree.body[0].end_col_offset == statement.end_col_offset


def test_multiline_statement_comment_attaches_on_the_last_line():
    both_agree('value = (\n    1,\n)  # type: int')
    tree = ast.parse('value = (\n    1,\n)  # type: int', type_comments=True)
    assert tree.body[0].type_comment == 'int'
    assert tree.body[0].end_col_offset == len(')  # type: int')


def test_function_definition_trailing_comment():
    both_agree('def run(number):  # type: (int) -> int\n    return number')
    tree = ast.parse('def run(number):  # type: (int) -> int\n    return number', type_comments=True)
    assert tree.body[0].type_comment == '(int) -> int'


def test_function_definition_block_comment():
    for source in (
        'def run(number):\n# type: (int) -> int\n    return number',
        'def run(number):\n    # type: (int) -> int\n    return number',
        'def run(number):\n\n    # type: (int) -> int\n    return number',
    ):
        both_agree(source)
        tree = ast.parse(source, type_comments=True)
        assert tree.body[0].type_comment == '(int) -> int'


def test_async_function_definition_comment():
    both_agree('async def run(number):  # type: (int) -> int\n    return number')


def test_parameter_comment_after_the_comma():
    source = (
        'def run(\n'
        '    first,  # type: int\n'
        '    second=2,  # type: int\n'
        '    *rest,  # type: int\n'
        '    keyword,  # type: int\n'
        '    **options,  # type: int\n'
        '):  # type: (...) -> int\n'
        '    return first'
    )
    both_agree(source)
    tree = ast.parse(source, type_comments=True)
    arguments = tree.body[0].args
    assert arguments.args[0].type_comment == 'int'
    assert arguments.args[1].type_comment == 'int'
    assert arguments.vararg.type_comment == 'int'
    assert arguments.kwonlyargs[0].type_comment == 'int'
    assert arguments.kwarg.type_comment == 'int'


def test_parameter_comment_before_the_parenthesis():
    both_agree('def run(first, second  # type: int\n): pass')
    tree = ast.parse('def run(first, second  # type: int\n): pass', type_comments=True)
    assert tree.body[0].args.args[1].type_comment == 'int'


def test_parameter_comment_without_trailing_comma():
    both_agree('def run(first  # type: int\n): pass')
    tree = ast.parse('def run(first  # type: int\n): pass', type_comments=True)
    assert tree.body[0].args.args[0].type_comment == 'int'


def test_parameter_comment_attaches_to_the_last_parameter_on_the_line():
    both_agree('def run(first, second,  # type: int\n): pass')
    tree = ast.parse('def run(first, second,  # type: int\n): pass', type_comments=True)
    assert tree.body[0].args.args[0].type_comment is None
    assert tree.body[0].args.args[1].type_comment == 'int'


def test_comment_on_its_own_line_inside_the_parameter_list():
    both_agree('def run(first,\n    # type: int\n    second): pass')
    tree = ast.parse('def run(first,\n    # type: int\n    second): pass', type_comments=True)
    assert tree.body[0].args.args[0].type_comment == 'int'


def test_for_and_with_colon_comments():
    for source in (
        'for item in iterable:  # type: int\n    total = item',
        'with open("f") as handle:  # type: int\n    data = handle',
        'async for item in iterable:  # type: int\n    total = item',
        'async with open("f") as handle:  # type: int\n    data = handle',
    ):
        both_agree(source)


# -- `# type: ignore` collection --------------------------------------------


def test_trailing_ignore_comment_becomes_a_type_ignore_node():
    both_agree('value = 1  # type: ignore')
    tree = ast.parse('value = 1  # type: ignore', type_comments=True)
    assert ignore_tags(tree) == [(1, '')]


def test_standalone_ignore_comment_keeps_the_newline_in_the_tag():
    both_agree('# type: ignore\nvalue = 1')
    tree = ast.parse('# type: ignore\nvalue = 1', type_comments=True)
    assert ignore_tags(tree) == [(1, '\n')]


def test_ignore_codes_and_trailing_whitespace_are_kept_in_the_tag():
    for source, tag in (
        ('value = 1  # type: ignore[unused]', '[unused]'),
        ('value = 1  # type: ignore   ', '   '),
        ('# type: ignore[unused]\nvalue = 1', '[unused]\n'),
    ):
        both_agree(source)
        tree = ast.parse(source, type_comments=True)
        assert ignore_tags(tree) == [(1, tag)]


def test_ignores_inside_blocks_and_parameter_lists():
    for source, tag in (
        ('if True:\n    pass  # type: ignore', ''),
        ('def run(first,\n    # type: ignore\n    second): pass', '\n'),
    ):
        both_agree(source)
        tree = ast.parse(source, type_comments=True)
        assert len(tree.type_ignores) == 1
        assert ignore_tags(tree)[0][1] == tag


def test_word_following_ignore_is_not_a_type_ignore():
    both_agree('value = 1  # type: ignored')
    tree = ast.parse('value = 1  # type: ignored', type_comments=True)
    assert tree.type_ignores == []
    assert tree.body[0].type_comment == 'ignored'


# -- rejections: exactly the sources CPython rejects -------------------------


def test_rejections():
    for source in (
        # Standalone non-ignore comment.
        'value = 1\n# type: int\nother = 2',
        # Statements other than Assign do not take a trailing type comment.
        'import os  # type: int',
        'value += 1  # type: int',
        'value: int = 1  # type: int',
        'for item in iterable: pass  # type: int',
        'class A:  # type: int\n    pass',
        'if True: pass  # type: int',
        # Comment inside brackets that are not a parameter list.
        'value = [1,  # type: int\n2]',
        'print(1,  # type: int\n2)',
        'def run(first=print(1,  # type: int\n2)): pass',
        # Parameter-list positions with no owning parameter.
        'def run(  # type: int\n    first): pass',
        'def run(first, /,  # type: int\n    second): pass',
        'def run(*,  # type: int\n    second): pass',
        'def run(*,  # type: int\nsecond): pass',
        # Two type comments on one definition.
        'def run():  # type: a\n    # type: b\n    pass',
        # Comment after a completed statement (not the Assign rule's slot).
        'def run(): pass  # type: (int) -> int',
        'value = 1; pass  # type: int',
    ):
        both_reject(source)


def test_rejected_parse_uses_the_failure_contract():
    """The native parse rejection maps to the D7 path in the Python seam."""
    args = Args(count=True)
    tree = parse_abstract_syntax_tree(b'value = 1\n# type: int\nother = 2\n', args, 'file.py')
    assert ast.dump(tree) == ast.dump(ast.Module(body=[], type_ignores=[]))
