# Visitor Layer

This document describes Deadcode's AST traversal machinery: parsing, the custom visitor pattern, scope tracking, and noqa comment support. See [Architecture](architecture.md) for the pipeline context and [Unused detection & ignoring](unused-detection-and-ignoring.md) for how items are filtered. See [index.md](index.md) for the full guide.

## Parsing Python Files

`parse_abstract_syntax_tree(content: str, filename: str) -> ast.Module` (`actions/parse_abstract_syntax_tree.py`) parses Python source code using `ast.parse(content, filename, type_comments=True)`. If parsing fails (e.g., syntax error), it returns an empty `ast.Module(body=[], type_ignores=[])` object, allowing analysis to continue on valid files in a mixed codebase.

## AST Visitor Initialization

`FindUnusedCodeVisitor.visit_abstract_syntax_trees()` (`visitor/find_unused_code_visitor.py:98-153`) loops over all filenames to analyze, performing per-file setup:

1. Sets `self.scope_parts = [module_name]` to track the module scope
2. Calls `noqa.parse_noqa(file_content_lines)` to extract noqa comments
3. Parses the file via `parse_abstract_syntax_tree`
4. Stores `self.file_content_lines` for later line-number calculations
5. Calls `self.visit(ast_root_node)` to traverse the tree

For empty, non-dunder files, a `CodeItem(type_='unused_file')` is created (`visitor/find_unused_code_visitor.py:146-153`).

## Custom Visitor Dispatch

`FindUnusedCodeVisitor` overrides the standard `visit()` method to insert custom logic before and after child traversal (`visitor/find_unused_code_visitor.py:506-587`):

1. Attaches `node.inherits_from` via helper `get_inherits_from()`
2. Computes decorator names (if any) and checks `ignore_definitions` gate: if the node's name, inheritance, or decorators match patterns, sets `self.should_ignore_new_definitions = True` and proceeds (`:519-528`)
3. Dispatches to `visit_<NodeType>()` for pre-children processing (e.g., `visit_ClassDef`, `visit_FunctionDef`)
4. **Scope push** for `ClassDef`, `FunctionDef`, `AsyncFunctionDef` (`:540-541`)
5. Checks `ignore_bodies_if_inherits_from` gate after scope push for class bodies (`:547-550`)
6. Recurses into child nodes via `ast.iter_fields` and `_handle_ast_list`
7. Dispatches to `visit_<NodeType>_after_visiting_child_nodes()` for post-children processing
8. **Scope pop** and resets `self.should_ignore_new_definitions` (`:582-587`)

This pattern ensures scope state is consistent and ignore rules are evaluated at the right point in traversal.

### Handling New Python Syntax

New AST node types introduced in Python 3.12+ (e.g., `ast.TypeAlias`, `ast.MatchAs`, PEP 695 `type_params`) are walked via the generic recursion even if no specialized `visit_<NodeType>()` method exists. This means most new constructs "just work" for name tracking without requiring explicit visitor methods. Specialized handling (e.g., `visit_TypeAlias` or `visit_TypeVar`) is only added when a test proves a false positive or false negative. The suite includes version-gated tests for match/case statements, walrus operators, type aliases, and PEP 695 generics to ensure correct handling across Python versions.

## Defined-Name Collectors

Definitions are recorded by calling `_define()` (`visitor/find_unused_code_visitor.py:274-328`), which creates a `CodeItem`, determines visibility, and either marks it used (if ignored) or appends it to the appropriate `defined_*` list.

Key visit methods that call `_define()` use correct AST node types:

- **`visit_FunctionDef(node: ast.FunctionDef | ast.AsyncFunctionDef)` / `visit_AsyncFunctionDef(node: ast.AsyncFunctionDef)`** — classify as property, method, or function based on context
- **`visit_ClassDef(node: ast.ClassDef)`** — collect class definitions
- **`visit_Import(node: ast.Import)` / `visit_ImportFrom(node: ast.ImportFrom)`** — collect imports via `_add_aliases()`, skipping `__future__` imports; note that `visit_ImportFrom` correctly takes `ast.ImportFrom` (not `ast.Import`)
- **`visit_Name(node: ast.Name)` Store/Param** — collect variable definitions (assignment or function parameter)
- **`visit_Attribute(node: ast.Attribute)` Store** — collect attribute assignments

The `_define()` call builds a `CodeItem` with one or more `Part`s (using `lines.get_first_line_number()` and `lines.get_last_line_number()` from `visitor/lines.py`), registers it in scope via `self.scopes.add()`, evaluates the `ignored()` predicate, and either marks it used or appends to `defined_*`. Position attributes (`lineno`, `col_offset`, `end_lineno`, `end_col_offset`) are accessed on AST nodes via `typing.cast` where the static type is `ast.AST` but the runtime value is a position-bearing statement or expression (e.g., `cast('ast.stmt', node).lineno`).

## Used-Name Collectors

Uses are recorded by calling `add_used_name(name)` (`visitor/find_unused_code_visitor.py:88-96`), which tracks any reference to a name across all files.

Key visit methods that call `add_used_name()` use correctly-typed AST node parameters:

- **`visit_Name(node: ast.Name)` Load/Del** — any reference to or deletion of a name
- **`visit_Attribute(node: ast.Attribute)` Load** — attribute access (e.g., `obj.attr`)
- **`visit_Call(node: ast.Call)`** — special handling for `getattr(obj, name)`, `hasattr(obj, name)`, and `str.format(**locals())`; for string arguments, checks with `isinstance(node, ast.Constant) and isinstance(node.value, str)` to extract the name from the string
- **`visit_BinOp(node: ast.BinOp)`** — special handling for `"%(name)s" % locals()` patterns; string matching via `isinstance(node.left, ast.Constant) and isinstance(node.left.value, str)` (not the deprecated `ast.Str` / `.s` API)
- **`visit_Assign(node: ast.Assign)`, `visit_AugAssign(node: ast.AugAssign)`, `visit_AnnAssign(node: ast.AnnAssign)`** — if assigning to `__all__`, all string constants in the list/value are marked used via `isinstance(elt, ast.Constant) and isinstance(elt.value, str)` checks. This supports all three forms:
  - `__all__ = ['exported_name']` (plain assignment)
  - `__all__ += ['exported_name']` (augmented assignment)
  - `__all__: list = ['exported_name']` (annotated assignment)
- **`visit_MatchClass(node)`** — pattern matching with classes marks class names used (kept untyped per pre-existing design)

## Scope Tracking

Scope is maintained as `scope_parts: List[str]` (`visitor/find_unused_code_visitor.py:73`), a stack of identifier names. The `scope` property joins this stack with `.` (`:85-86`), e.g., `"OuterClass.inner_method"`.

Internally, scope is backed by `NestedScope` (`utils/nested_scopes.py:6`), which manages scope creation and lookup.

## Noqa Comments

`noqa.parse_noqa(file_content_lines)` (`visitor/noqa.py:54-62`) extracts flake8-style noqa comments, supporting all whitespace patterns:

- `#noqa` (no space)
- `# noqa` (one space, traditional)
- `#  noqa` (multiple spaces)
- `# noqa: DC01, DC07` (with specific codes)

The regex pattern (`NOQA_REGEXP`, `noqa.py:4-14`) matches `#\s*noqa` (hash followed by optional whitespace) followed by optional codes. Codes can be in any case (lowercase, uppercase, or mixed like `dc07` or `DC01`), and are normalized to uppercase before lookup via `NOQA_CODE_MAP` (`noqa.py:16-46`):

- `F401` → `DC07` (unused-import)
- `F841` → `DC01` (unused-variable)
- `dc07` → `DC07` (lowercase codes are uppercased before map lookup)
- bare `# noqa` → `'all'` (ignore all checks on this line)

`ignore_line(line_number, error_code)` (`noqa.py:65-67`) checks whether a given line has a noqa directive for a code, and is invoked in `_define()` (`find_unused_code_visitor.py:299`). If the item matches an ignore rule, it is added to `used_names` (treated as used, removing it from the unused output).

The `ERROR_CODES` dict in `ignore.py:23-36` maps error names to codes for cross-referencing noqa directives and warnings.

## Built-in Ignore Predicates

The `ignore.py` module provides default predicates that classify items to ignore:

- **`_ignore_class(filename, class_name)`** (`:73-74`) — ignores test classes (name contains "Test") in test files
- **`_ignore_import(filename, import_name)`** (`:77-83`) — ignores star imports and imports in `__init__.py`
- **`_ignore_function(filename, function_name)`** (`:86-87`) — ignores test functions (`test_*`, pytest setup/teardown) in test files
- **`_ignore_method(filename, method_name)`** (`:91-93`) — ignores special methods (dunder names) and test methods
- **`_ignore_variable(filename, varname)`** (`:96-105`) — ignores `_` (throwaway), `_x` (private), and `__x__` (special variables)
- **`_is_test_file(filename)`** (`:58-63`) — uses glob patterns to identify test files: `*/test/*`, `*/tests/*`, `*test.py`, `*[-_]test.py`

Additionally, `IGNORED_VARIABLE_NAMES = {'object', 'self'}` (`ignore.py:9`) are always treated as used (never reported as unused).

## Summary

The visitor layer orchestrates a two-phase analysis:

1. **First pass (FindUnusedCodeVisitor)**: Traverses ASTs, recording definitions with scope context and type, and tracking all name uses.
2. **Apply ignore rules**: Items are either marked used (and filtered) or remain in the unused set, forming the input to the fix stage.

Details on how "unused" is determined appear in [Unused detection & ignoring](unused-detection-and-ignoring.md).
