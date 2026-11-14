"""Loader for the optional Rust acceleration module.

The native extension lives in the private ``deadcode._native`` module and is
only present in installs that explicitly built it with maturin. Default
installs (editable, CI, the universal fallback wheel) contain no compiled
module, so every accelerated path must keep its pure-Python implementation as
the automatic fallback. Dispatch sites consult the module-level ``_native``
value populated once at import time; tests exercise both branches through
``load_native``.
"""

from __future__ import annotations

from typing import Any

_native: Any | None = None


def load_native() -> Any | None:
    """Return the ``deadcode._native`` extension module, or ``None`` when it is not installed."""
    try:
        from deadcode import _native  # type: ignore[attr-defined]  # noqa: PLC0415
    except ImportError:
        return None
    return _native


_native = load_native()
