from types import ModuleType

_native: ModuleType | None
try:
    from deadcode import _native  # type: ignore[attr-defined, no-redef]
except ImportError:  # The native module is optional: dev installs are native-free (D6).
    _native = None


def load_native() -> ModuleType | None:
    """Return the native `deadcode._native` module, or None when it is not built.

    The import attempt happens once at module import time; every dispatch site
    only consults the already-resolved binding.
    """
    return _native
