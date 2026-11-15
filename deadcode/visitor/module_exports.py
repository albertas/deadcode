from typing import Any, cast

import ast

from deadcode import _native_loader

# Sentinel distinguishing "the native path cannot be used" from a valid native
# ``None`` result (exports unknown).
_NATIVE_FAILED = object()


def collect_module_exports(tree: ast.Module) -> set[str] | None:
    """Return statically known exported names, or None when exports are unknown.

    Dispatch seam for the native module-export collector (D5): when the
    ``deadcode._native`` extension is installed and exposes
    ``collect_module_exports``, the already-parsed tree is traversed in Rust
    (no Rust-side parsing); otherwise — or when the native traversal raises —
    the pure-Python implementation below runs unchanged as the automatic
    fallback. A native ``None`` return is a valid "exports unknown" result,
    not a fallback signal.
    """
    native_result = _native_exports(tree)
    if native_result is _NATIVE_FAILED:
        return _collect_module_exports(tree)
    return cast('set[str] | None', native_result)


def _native_exports(tree: ast.Module) -> Any:
    """Return the native collector's result, or ``_NATIVE_FAILED`` when the
    native module is absent, lacks the collector, or cannot handle the tree."""
    native = _native_loader._native  # noqa: SLF001
    collect = getattr(native, 'collect_module_exports', None) if native is not None else None
    if collect is None:
        return _NATIVE_FAILED
    try:
        return collect(tree)
    except Exception:  # noqa: BLE001
        # The native traversal cannot handle this tree; parity is never lost,
        # only speed.
        return _NATIVE_FAILED


def _collect_module_exports(tree: ast.Module) -> set[str] | None:
    """Return statically known exported names, or None when exports are unknown."""
    has_binding = False
    has_unknown_binding = False
    static_exports: set[str] = set()

    for node in ast.walk(tree):
        if not _binds_special_variable__all__(node):
            continue
        has_binding = True
        if (
            isinstance(node, (ast.Assign, ast.AnnAssign))
            and _is_module_level_statement(tree, node)
            and isinstance(node.value, (ast.List, ast.Tuple))
        ):
            static_exports_for_node = _collect_static_exports(node.value)
            if static_exports_for_node is not None:
                static_exports = static_exports_for_node
                continue
        has_unknown_binding = True

    if has_unknown_binding:
        return None
    if not has_binding:
        return _collect_public_module_level_names(tree)
    return static_exports


def _binds_special_variable__all__(node: ast.AST) -> bool:
    if isinstance(node, ast.Assign):
        return any(_is_special_variable__all__(target) for target in node.targets)
    if isinstance(node, (ast.AnnAssign, ast.AugAssign)):
        return _is_special_variable__all__(node.target)
    return False


def _is_module_level_statement(tree: ast.Module, node: ast.AST) -> bool:
    return any(statement is node for statement in tree.body)


def _is_special_variable__all__(node: ast.AST) -> bool:
    return isinstance(node, ast.Name) and node.id == '__all__'


def _collect_static_exports(node: ast.List | ast.Tuple) -> set[str] | None:
    exports = set()
    for element in node.elts:
        if not isinstance(element, ast.Constant) or not isinstance(element.value, str):
            return None
        exports.add(element.value)
    return exports


def _collect_public_module_level_names(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for statement in tree.body:
        if isinstance(statement, ast.Assign):
            for target in statement.targets:
                names |= _collect_target_names(target)
        elif isinstance(statement, (ast.AnnAssign, ast.AugAssign)):
            names |= _collect_target_names(statement.target)
        elif isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(statement.name)
        elif isinstance(statement, ast.Import):
            for alias in statement.names:
                names.add(alias.asname or alias.name.partition('.')[0])
        elif isinstance(statement, ast.ImportFrom):
            for alias in statement.names:
                if alias.name != '*':
                    names.add(alias.asname or alias.name)
    return {name for name in names if not name.startswith('_')}


def _collect_target_names(node: ast.AST) -> set[str]:
    if isinstance(node, ast.Name):
        return {node.id}
    return set()
