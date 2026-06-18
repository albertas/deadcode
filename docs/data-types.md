# Data Types

This document describes the shared types and constants that flow through the Deadcode pipeline. See [Architecture](architecture.md) for context on how these types are used across stages.

## Core Argument Type: `Args`

`Args` (`data_types.py:13-34`) is a `@dataclass` carrying 20 configuration fields that govern the analysis and output:

- **Boolean flags** (default `False`): `fix`, `verbose`, `no_color`, `quiet`, `count`
- **List fields** (default `()`): `dry`, `paths`, `exclude`, ignore-* variants (`ignore_definitions`, `ignore_definitions_if_decorated_with`, `ignore_definitions_if_inherits_from`, `ignore_bodies_of`, `ignore_bodies_if_decorated_with`, `ignore_bodies_if_inherits_from`, `ignore_if_decorated_with`, `ignore_if_inherits_from`, `ignore_names`, `ignore_names_if_inherits_from`, `ignore_names_if_decorated_with`, `ignore_names_in_files`)

The type alias `Pathname = str` (`data_types.py:10`) denotes list field values. Additional type aliases include `AbstractSyntaxTree = ast.Module`, `FileContent = str`, and `Filename = str` (fully-qualified file path).

## Code Fragment Type: `Part`

`Part` (`data_types.py:37-49`) is a `NamedTuple` representing an atomic removal or replacement region—a span of lines and columns to remove or replace during the fix stage:

- `line_start, line_end, col_start, col_end: int` — 0-indexed line and column boundaries (inclusive start, exclusive end)
- `insert_code: str | None = None` — optional code to insert in place of the removed fragment
- `insert_code_if_character_is_not_removed: tuple[int,int] | None = None` — optional conditional insertion: insert `insert_code` only if the character at this coordinate survives removal

The fix stage (`fix-and-output.md`) merges overlapping `Part`s from all unused items and applies them to files.

## Code Item Type: `CodeItem`

`CodeItem` (`code_item.py:39-140`) is a plain Python class (marked TODO to convert to `@dataclass`) that holds metadata about a detected code element:

- `name: str` — the identifier name (e.g., variable, function, or class name)
- `type_: UnusedCodeType` — one of 12 types (see "Error codes" below)
- `filename: Path` — file containing the item
- `code_parts: List[Part]` — regions to remove (usually one, but can be multiple for complex removals)
- `scope: str` — dotted path to the item's lexical scope (e.g., `"MyClass.my_method"`)
- `inherits_from: List[str]` — for classes, list of base class names
- `name_line, name_column: int` — position of the item's definition
- `message: str` — human-readable message (e.g., `"Variable x is never used"`)
- `error_code: UnusedCodeErrorCode` — derived from `type_` via `ERROR_TYPE_TO_ERROR_CODE` (`code_item.py:83`)
- `number_of_uses: int` — tracked but not currently used in output

Properties:
- `scoped_name` — returns `"{scope}.{name}"` for qualified reference
- `filename_with_position` — returns `"path:line:column:"` for output formatting

Note: `CodeItem.__eq__` and `__hash__` compare by `name` only (`code_item.py:131, :139`), making items comparable as strings and usable in sets.

## Error Codes and Types

`UnusedCodeType` (`constants.py:4-17`) is a `Literal` of 12 type tags:

```
'attribute', 'class', 'function', 'import', 'method', 'property',
'variable', 'unreachable_code', 'name', 'unused_file', 'commented_out_code', 'ignore_expression'
```

`UnusedCodeErrorCode` (`constants.py:20-33`) is a `Literal` of error codes:

```
DC01 (variable), DC02 (function), DC03 (class), DC04 (method), DC05 (attribute),
DC06 (name), DC07 (import), DC08 (property), DC09 (unreachable_code),
DC11 (unused_file), DC12 (commented_out_code), DC13 (ignore_expression)
```

Note: **DC10 is intentionally skipped** in the numbering.

`ERROR_TYPE_TO_ERROR_CODE` (`constants.py:36-49`) maps each `UnusedCodeType` to its code. For example:
- `'variable'` → `'DC01'`
- `'import'` → `'DC07'`
- `'unused_file'` → `'DC11'`

## Type Flow

The pipeline's three main stages work with these types:

1. **Parsing**: `parse_arguments` → `Args`
2. **Analysis**: `find_unused_names` → `Tuple[Iterable[CodeItem], dict[Filename, List[Part]]]`
3. **Output**: Items flow to error message formatting and the fix stage
