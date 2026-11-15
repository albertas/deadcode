import sys
from types import ModuleType

import deadcode._native_loader as native_loader


def test_load_native_returns_none_when_extension_module_is_absent(monkeypatch):
    monkeypatch.delitem(sys.modules, 'deadcode._native', raising=False)
    assert native_loader.load_native() is None


def test_module_level_native_is_none_in_fallback_install():
    assert native_loader._native is None  # noqa: SLF001


def test_load_native_returns_injected_stub_module(monkeypatch):
    stub = ModuleType('deadcode._native')
    stub.crate_version = lambda: '2.6.3'  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, 'deadcode._native', stub)
    assert native_loader.load_native() is stub


def test_load_native_import_error_from_stub_is_treated_as_missing(monkeypatch):
    monkeypatch.setitem(sys.modules, 'deadcode._native', None)
    assert native_loader.load_native() is None
