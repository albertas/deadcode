"""Dispatch tests pinning that AST traversal stays in Python (spec slice 8).

The D6 decision for the third hot-path candidate was NOT to port the AST
traversal: profiling cleared the time-share threshold but the throwaway pyo3
prototype measured well below the required 1.5x on the hot path, because every
node access across the FFI boundary stays bound-bound on the Python AST tree.
These tests pin that outcome at the dispatch seam: the native module exposes no
traversal entry point, and the visitor's findings are byte-identical whether or
not a native module shaped exactly like the shipped extension is installed.
"""

import inspect
from types import ModuleType

from deadcode import _native_loader
from deadcode.cli import main
from deadcode.data_types import Args
from deadcode.visitor import dead_code_visitor
from deadcode.visitor.dead_code_visitor import DeadCodeVisitor

FILES = {
    'foo.py': b"""
        __all__ = ['exported']
        exported = 1
        hidden = 2
    """,
    'bar.py': b"""
        from foo import *
        print(exported)
        # print("Hello world")
    """,
}

NATIVE_FUNCTION_NAMES = ('crate_version', 'scan_comments', 'collect_module_exports')
TRAVERSAL_ENTRY_POINT_NAMES = (
    'traverse',
    'traverse_tree',
    'visit_tree',
    'walk_tree',
    'collect_dead_code',
)


def _install_shipped_shape_stub(monkeypatch) -> ModuleType:
    """Install a native stub exposing exactly the shipped extension surface."""
    stub = ModuleType('deadcode._native')

    def crate_version() -> str:
        return '0.0.0'

    def scan_comments(_code: bytes):
        return None

    def collect_module_exports(_tree: object):
        return None

    stub.crate_version = crate_version  # type: ignore[attr-defined]
    stub.scan_comments = scan_comments  # type: ignore[attr-defined]
    stub.collect_module_exports = collect_module_exports  # type: ignore[attr-defined]
    monkeypatch.setattr(_native_loader, '_native', stub)
    return stub


def test_native_module_exposes_no_traversal_entry_point(monkeypatch):
    stub = _install_shipped_shape_stub(monkeypatch)

    for name in TRAVERSAL_ENTRY_POINT_NAMES:
        assert not hasattr(stub, name), f'unexpected native traversal entry point {name}'


def test_traversal_visits_the_same_nodes_with_and_without_native(monkeypatch, virtual_file_system):
    visits: list[str] = []
    original_visit = DeadCodeVisitor.visit

    def counting_visit(self: DeadCodeVisitor, node: object) -> None:
        visits.append(type(node).__name__)
        original_visit(self, node)

    virtual_file_system.files = FILES
    monkeypatch.setattr(_native_loader, '_native', None)
    monkeypatch.setattr(DeadCodeVisitor, 'visit', counting_visit)
    without_native = main(['foo.py', 'bar.py', '--no-color'])
    node_types_without_native = list(visits)

    visits.clear()
    _install_shipped_shape_stub(monkeypatch)
    with_native = main(['foo.py', 'bar.py', '--no-color'])

    assert node_types_without_native == visits
    assert with_native == without_native
    assert 'Module' in node_types_without_native
    assert 'Assign' in node_types_without_native
    assert 'ImportFrom' in node_types_without_native


def test_findings_are_identical_with_and_without_native(monkeypatch, virtual_file_system):
    virtual_file_system.files = FILES

    monkeypatch.setattr(_native_loader, '_native', None)
    without_native = main(['foo.py', 'bar.py', '--no-color'])

    _install_shipped_shape_stub(monkeypatch)
    with_native = main(['foo.py', 'bar.py', '--no-color'])

    assert with_native == without_native
    assert without_native == ('bar.py:3:0: DC12 Commented out code\nfoo.py:3:0: DC01 Variable `hidden` is never used')


def test_visitor_module_keeps_no_traversal_dispatch_wrapper(monkeypatch, virtual_file_system):
    # The two shipped native seams live in dedicated wrappers; the traversal
    # must have none, so no attribute of the visitor module consults a native
    # traversal entry point.
    stub = _install_shipped_shape_stub(monkeypatch)
    traversal_calls: list[str] = []
    for name in NATIVE_FUNCTION_NAMES:
        original = getattr(stub, name)

        def spying(*args: object, _name: str = name, _original: object = original, **kwargs: object) -> object:
            traversal_calls.append(_name)
            return _original(*args, **kwargs)  # type: ignore[operator]

        monkeypatch.setattr(stub, name, spying)

    virtual_file_system.files = {'traversal.py': b'x = 1\n'}
    visitor = DeadCodeVisitor(filenames=['traversal.py'], args=Args())
    visitor._parse_all_modules()  # noqa: SLF001

    # The parse path may consult scan seams but never a traversal entry point.
    assert all(name in NATIVE_FUNCTION_NAMES for name in traversal_calls)
    assert not any('traverse' in name or 'visit' in name for name in traversal_calls)


def test_dead_code_visitor_source_has_no_native_traversal_reference():
    source = inspect.getsource(dead_code_visitor)

    assert 'traverse_tree' not in source
    assert 'visit_tree' not in source
    assert '_native.traverse' not in source
