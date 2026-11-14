"""Dispatch tests for the native module-export collector (spec slice 7).

The Rust traversal's behavioural parity is verified against the real corpus by
the benchmark parity harness; these tests pin the dispatch seam itself: the
native result flows through the wrapper unchanged, a native ``None`` is a
valid "exports unknown" result, and every unavailable-native condition falls
back to the pure-Python implementation.
"""

import ast
from types import ModuleType

from deadcode import _native_loader
from deadcode.visitor import module_exports
from deadcode.visitor.module_exports import collect_module_exports

TREE = ast.parse('__all__ = ["a", "b"]\n')
PUBLIC_TREE = ast.parse('def api():\n    pass\n\n_secret = 1\n')
UNKNOWN_TREE = ast.parse('__all__ = list(["a"])\n')


def _install_native_stub(monkeypatch, collect_module_exports_native) -> ModuleType:
    stub = ModuleType('deadcode._native')
    if collect_module_exports_native is not None:
        stub.collect_module_exports = collect_module_exports_native  # type: ignore[attr-defined]
    monkeypatch.setattr(_native_loader, '_native', stub)
    return stub


def test_native_result_flows_through_unchanged(monkeypatch):
    # Having: a native collector returning a marker result that real traversal
    # of the input could never produce.
    calls: list[ast.Module] = []

    def fake_collect(tree: ast.Module):
        calls.append(tree)
        return {'marker_export'}

    _install_native_stub(monkeypatch, fake_collect)

    # When
    exports = collect_module_exports(TREE)

    # Then: the tree reached the native collector and its result passes through.
    assert calls == [TREE]
    assert exports == {'marker_export'}


def test_native_none_is_exports_unknown_not_fallback(monkeypatch):
    # The native collector returns None when __all__ is bound non-statically;
    # that is the correct result and must not trigger the Python fallback.
    def fake_collect(_tree: ast.Module):
        return None

    _install_native_stub(monkeypatch, fake_collect)

    assert collect_module_exports(TREE) is None


def test_python_fallback_runs_without_native_module(monkeypatch):
    monkeypatch.setattr(_native_loader, '_native', None)

    assert collect_module_exports(TREE) == {'a', 'b'}
    assert collect_module_exports(PUBLIC_TREE) == {'api'}
    assert collect_module_exports(UNKNOWN_TREE) is None


def test_fallback_when_native_module_lacks_collector(monkeypatch):
    _install_native_stub(monkeypatch, None)

    assert collect_module_exports(TREE) == {'a', 'b'}


def test_fallback_when_native_traversal_raises(monkeypatch):
    failure = RuntimeError('unexpected tree shape')

    def raising_collect(_tree: ast.Module):
        raise failure

    _install_native_stub(monkeypatch, raising_collect)

    assert collect_module_exports(TREE) == {'a', 'b'}
    assert collect_module_exports(PUBLIC_TREE) == {'api'}
    assert collect_module_exports(UNKNOWN_TREE) is None


def test_python_implementation_matches_native_contract(monkeypatch):
    # Without a native module the wrapper must reach the unchanged pure-Python
    # implementation for every result shape of the contract.
    monkeypatch.setattr(_native_loader, '_native', None)
    aug_tree = ast.parse('__all__ = ["a"]\n__all__ += ["b"]\n')
    dotted_tree = ast.parse('import os.path\nimport json as j\nfrom x import y\n')

    assert module_exports._collect_module_exports(TREE) == {'a', 'b'}  # noqa: SLF001
    assert module_exports._collect_module_exports(PUBLIC_TREE) == {'api'}  # noqa: SLF001
    assert module_exports._collect_module_exports(UNKNOWN_TREE) is None  # noqa: SLF001
    assert module_exports._collect_module_exports(aug_tree) is None  # noqa: SLF001
    assert module_exports._collect_module_exports(dotted_tree) == {'os', 'j', 'y'}  # noqa: SLF001
