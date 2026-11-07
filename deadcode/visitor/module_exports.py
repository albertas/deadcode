import ast


def collect_module_exports(tree: ast.Module) -> set[str] | None:
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
