# Visitor Layer

This document describes Deadcode's AST traversal machinery: parsing, the custom visitor pattern, scope tracking, and noqa comment support. See [Architecture](architecture.md) for the pipeline context and [Unused detection & ignoring](unused-detection-and-ignoring.md) for how items are filtered. See [index.md](index.md) for the full guide.

## Parsing Python Files

`parse_abstract_syntax_tree(content: str, filename: str) -> ast.Module` (`actions/parse_abstract_syntax_tree.py:6-13`) parses Python source code using `ast.parse(content, filename, type_comments=True)`. If parsing fails (e.g., syntax error), it returns an empty `ast.Module()` object, allowing analysis to continue on valid files in a mixed codebase.

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
2. Checks `ignore_definitions` gate: if the node's name matches, sets `self.should_ignore_new_definitions = True` and proceeds (`:519-528`)
3. Dispatches to `visit_<NodeType>()` for pre-children processing (e.g., `visit_ClassDef`, `visit_FunctionDef`)
4. **Scope push** for `ClassDef`, `FunctionDef`, `AsyncFunctionDef` (`:540-541`)
5. Checks `ignore_bodies_if_inherits_from` gate after scope push for class bodies (`:547-550`)
6. Recurses into child nodes via `ast.iter_fields` and `_handle_ast_list`
7. Dispatches to `visit_<NodeType>_after_visiting_child_nodes()` for post-children processing
8. **Scope pop** and resets `self.should_ignore_new_definitions` (`:582-587`)

This pattern ensures scope state is consistent and ignore rules are evaluated at the right point in traversal.

## Defined-Name Collectors

Definitions are recorded by calling `_define()` (`visitor/find_unused_code_visitor.py:274-328`), which creates a `CodeItem`, determines visibility, and either marks it used (if ignored) or appends it to the appropriate `defined_*` list.

Key visit methods that call `_define()`:

- **`visit_FunctionDef` / `visit_AsyncFunctionDef`** (`:342-453`) — classify as property, method, or function based on context
- **`visit_ClassDef`** (`:426-432`) — collect class definitions
- **`visit_Import` / `visit_ImportFrom`** (`:461-471`, `:212-237`) — collect imports via `_add_aliases()`, skipping `__future__` imports
- **`visit_Name` Store/Param** (`:485-489`) — collect variable definitions (assignment or function parameter)
- **`visit_Attribute` Store** (`:345-349`) — collect attribute assignments

The `_define()` call builds a `CodeItem` with one or more `Part`s (using `lines.get_first_line_number()` and `lines.get_last_line_number()` from `visitor/lines.py:41-82`), registers it in scope via `self.scopes.add()`, evaluates the `ignored()` predicate, and either marks it used or appends to `defined_*`.

## Used-Name Collectors

Uses are recorded by calling `add_used_name(name)` (`visitor/find_unused_code_visitor.py:88-96`), which tracks any reference to a name across all files.

Key visit methods that call `add_used_name()`:

- **`visit_Name` Load/Del** (`:487`) — any reference to or deletion of a name
- **`visit_Attribute` Load** (`:349`) — attribute access (e.g., `obj.attr`)
- **`visit_Call`** (`:360-378`) — special handling for `getattr(obj, name)`, `hasattr(obj, name)`, and `str.format(**locals())`; the name inside the string is marked used
- **`visit_BinOp`** (`:351-358`) — special handling for `"%(name)s" % locals()` patterns
- **`visit_Assign`** (`:491-496`) — if assigning to `__all__`, all names in the list are marked used
- **`visit_MatchClass`** (`:502-504`) — pattern matching with classes marks class names used

## Scope Tracking

Scope is maintained as `scope_parts: List[str]` (`visitor/find_unused_code_visitor.py:73`), a stack of identifier names. The `scope` property joins this stack with `.` (`:85-86`), e.g., `"OuterClass.inner_method"`.

Internally, scope is backed by `NestedScope` (`utils/nested_scopes.py:6`), which manages scope creation and lookup.

## Noqa Comments

`noqa.parse_noqa(file_content_lines)` (`visitor/noqa.py:5-15, :55-63`) extracts flake8-style `# noqa: DC01, DC07` comments using a regex pattern (`NOQA_REGEXP`). Codes are normalized via `NOQA_CODE_MAP` (`noqa.py:17-47`), mapping legacy codes like `F401` (unused import) to `DC07`:

- `F401` → `DC07` (unused-import)
- `F841` → `DC01` (unused-variable)
- bare `# noqa` → `'all'` (ignore all checks on this line)

`ignore_line(line_number, error_code)` (`noqa.py:66-68`) checks whether a given line has a noqa directive for a code, and is invoked in `_define()` (`find_unused_code_visitor.py:299`). If the item matches an ignore rule, it is added to `used_names` (treated as used, removing it from the unused output).

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
