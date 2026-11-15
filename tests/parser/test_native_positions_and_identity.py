"""Dedicated assertions for the Q2 contracts the parity dump test exercises
only indirectly:

1. Positions are byte-based and identical to the reference tree: every node of
   the native tree, walked in the same order, carries the same
   (lineno, col_offset, end_lineno, end_col_offset) tuple as the tree the
   running interpreter's `ast.parse` produces.
2. Object identity: the tree is a single connected object graph — the target
   the visitor visits through `ast.iter_fields` is the very object stored in
   `statement.targets[0]` (and `statement.target` for
   AnnAssign/AugAssign), so the visitor's identity-based
   `_get_assignment_removal_node` logic works unchanged.

The suite skips cleanly in fallback mode (native module absent).
"""

import ast
from pathlib import Path

import pytest

from deadcode._native_loader import load_native

FIXTURES = sorted((Path(__file__).parent / 'fixtures').glob('*.py'))


def native_is_available():
    return load_native() is not None


pytestmark = pytest.mark.skipif(not native_is_available(), reason='native module not built (fallback mode)')


@pytest.mark.parametrize('fixture', FIXTURES, ids=lambda fixture: fixture.name)
def test_positions_are_byte_based_and_match_the_reference(fixture):
    native = load_native()
    assert native is not None

    source = fixture.read_bytes()
    filename = str(fixture)

    native_tree = native.parse_module(source, filename, True)
    reference_tree = ast.parse(source, filename=filename, type_comments=True)

    native_nodes = list(ast.walk(native_tree))
    reference_nodes = list(ast.walk(reference_tree))
    assert len(native_nodes) == len(reference_nodes)

    for native_node, reference_node in zip(native_nodes, reference_nodes, strict=False):
        assert type(native_node) is type(reference_node)
        for attribute in ('lineno', 'col_offset', 'end_lineno', 'end_col_offset'):
            assert getattr(native_node, attribute, None) == getattr(reference_node, attribute, None), (
                f'{fixture.name}: {type(native_node).__name__}.{attribute} diverges'
            )
        # The byte-based columns are the decoded-text byte offsets CPython
        # reports: a column must never exceed the byte length of its line.
        # (`TypeIgnore` nodes carry a line but no column, like CPython's.)
        if hasattr(native_node, 'col_offset'):
            line = source.splitlines()[native_node.lineno - 1]
            assert native_node.col_offset <= len(line)


@pytest.mark.parametrize('fixture', FIXTURES, ids=lambda fixture: fixture.name)
def test_assignment_targets_are_the_visited_objects(fixture):
    native = load_native()
    assert native is not None

    tree = native.parse_module(fixture.read_bytes(), str(fixture), True)

    for statement in ast.walk(tree):
        if isinstance(statement, ast.Assign):
            visited = dict(ast.iter_fields(statement))['targets'][0]
            assert visited is statement.targets[0]
        elif isinstance(statement, (ast.AnnAssign, ast.AugAssign)):
            visited = dict(ast.iter_fields(statement))['target']
            assert visited is statement.target


@pytest.mark.parametrize('fixture', FIXTURES, ids=lambda fixture: fixture.name)
def test_tree_mutation_is_visible_through_the_visited_path(fixture):
    """Mutating a target through the visitor's access path must be visible on
    the node itself: the converter emits no duplicated target objects."""
    native = load_native()
    assert native is not None

    tree = native.parse_module(fixture.read_bytes(), str(fixture), True)

    assignments = [node for node in ast.walk(tree) if isinstance(node, ast.Assign)]
    if not assignments:
        pytest.skip('fixture has no ast.Assign statements')

    statement = assignments[0]
    target = statement.targets[0]
    target.inherits_from = object()
    assert any(node is target and hasattr(node, 'inherits_from') for node in ast.walk(statement))
