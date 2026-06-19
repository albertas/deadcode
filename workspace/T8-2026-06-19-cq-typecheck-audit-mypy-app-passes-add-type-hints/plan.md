# Implementation Plan

## Overview

Drive `just check-typecheck` (`uv run mypy deadcode/` under `strict = true`) from
**42 errors → 0** by fixing types only — correct annotations, narrowing
`isinstance`, type-equivalent node constructs, generics, and `typing.cast` — with
no `# type: ignore`, no mypy-config loosening, and no runtime-logic edits. `just
test` stays green throughout (176 passed, 18 skipped, coverage ≥ 95%).

> **This plan was validated by applying every phase end-to-end against the live
> tree and reverting.** The per-phase error counts, the line-number drift, and
> three deviations from `structure.md` (called out inline and summarized at the
> end) are confirmed against real `mypy`/`ruff`/`pytest` runs — not estimated.

### How to use this plan

- **Anchor edits on the quoted code, not line numbers.** Each phase edits a file
  whose line numbers shift as earlier edits within the same file land. The
  `structure.md`/`design.md` line numbers refer to the *original* file; this plan
  gives `old` → `new` snippets so edits are robust to drift.
- **Apply phases in order 1 → 6.** Phases 1–5 are each independently valuable and
  mergeable; Phase 6 is the capstone.
- **After each phase, both invariants must hold** (see *Shared Verification* and
  the checkpoint table). An unexpected count is signal, not noise.

### Shared Verification Primitives (used by every phase)

```bash
# Live error count (the single source of truth for phase deltas):
uv run mypy deadcode/ 2>&1 | grep -c ': error:'

# A given file is fully clear (no errors mention it):
uv run mypy deadcode/ 2>&1 | grep -c '<relative/path>.py:'   # expect 0

# No regression in the test suite:
just test            # exits 0

# No suppression was added (count of ADDED 'type: ignore' lines in the diff):
git diff -- deadcode/ | grep -E '^\+' | grep -c 'type: ignore'   # expect 0
```

> Use `uv run mypy deadcode/` directly for the count probes (identical to the
> `just check-typecheck` recipe but without the `sync` step re-running each time).
> Run `just check-typecheck` once at the end for the authoritative gate.

### Corrected checkpoint table (validated live)

| After phase | `mypy ... grep -c ': error:'` | `just test` |
|-------------|-------------------------------|-------------|
| baseline    | 42                            | green       |
| 1           | 38                            | green       |
| 2           | 32                            | green       |
| 3           | 15                            | green       |
| 4           | 11                            | green       |
| 5           | 5                             | green       |
| 6           | 0 (`Success`)                 | green       |

> **Deviation from `structure.md`:** the `structure.md` checkpoint table lists
> 20 / 16 / 10 after phases 3 / 4 / 5. Those numbers undercount the position-read
> cluster in Phase 3. The validated counts are **15 / 11 / 5**. The *content* of
> every phase is unchanged; only the running totals are corrected.

---

## Phase 1: Isolated standalone fixes (42 → 38)

Three unrelated single-spot fixes in separate files; zero fan-out.

### Changes

#### 1. Remove the stray `# type: ignore`
**File**: `deadcode/utils/print_ast.py`
**Action**: modify — clears `[unused-ignore]` (it is itself one of the 42 errors,
because `strict` enables `warn_unused_ignores`).

```python
# old
    print(ast.dump(node, indent=4))  # type: ignore
# new
    print(ast.dump(node, indent=4))
```

#### 2. Construct a complete empty module
**File**: `deadcode/actions/parse_abstract_syntax_tree.py`
**Action**: modify — `ast.Module()` requires `body`/`type_ignores`; clears
`[call-arg]`. Equivalent empty module.

```python
# old
        return ast.Module()
# new
        return ast.Module(body=[], type_ignores=[])
```

#### 3. Make `remove_from_list` generic
**File**: `deadcode/utils/remove_from_list.py`
**Action**: modify — add a module-local `TypeVar` and subscript the bare `list`
and `Callable`; clears 2× `[type-arg]`. `Callable` is already imported from
`collections.abc`.

```python
# old
from collections.abc import Callable


def remove_from_list(elements: list, should_remove: Callable) -> None:
# new
from collections.abc import Callable
from typing import TypeVar

T = TypeVar('T')


def remove_from_list(elements: list[T], should_remove: Callable[[T], bool]) -> None:
```

### Verification
#### Automated
- [x] `uv run mypy deadcode/ 2>&1 | grep -c ': error:'` → `38`
- [x] `just test` exits `0`

#### Manual
- [x] `uv run mypy deadcode/ 2>&1 | grep -cE 'print_ast.py:|parse_abstract_syntax_tree.py:|remove_from_list.py:'` → `0` (all three files gone from output)
- [x] `git diff -- deadcode/ | grep -E '^\+' | grep -c 'type: ignore'` → `0`

---

## Phase 2: Correct `visit_X` node types + attribute narrowing (38 → 32)

Fix the two lying `visit_X` parameter annotations in the fix-visitor, narrow the
attribute reads they expose, **and widen `visit_Import` so the
`visit_ImportFrom` → `visit_Import` delegation still type-checks.**

### Changes

**File**: `deadcode/visitor/fix_unused_code_visitor.py` (all four edits)

#### 1. `visit_With` operates on `ast.With`, narrow `.optional_vars` to `ast.Name`
**Action**: modify — clears `[override]` (`visit_With`) and `[attr-defined]` on
`.items` and `.id`. Narrowing the guard from `ast.AST` to `ast.Name` is
type-equivalent: only `ast.Name` has `.id`, and a non-`Name` target never reached
the `.id` read meaningfully.

```python
# old
    def visit_With(self, node: ast.ClassDef) -> None:
        # Remove optional_var node from AST if optional_var name is in unused_names
        for item in node.items:
            if isinstance(item.optional_vars, ast.AST):
# new
    def visit_With(self, node: ast.With) -> None:
        # Remove optional_var node from AST if optional_var name is in unused_names
        for item in node.items:
            if isinstance(item.optional_vars, ast.Name):
```

#### 2. Read `.name` via `getattr` in `visit_ClassDef`
**Action**: modify — `node.body` items are `ast.stmt`, which has no `.name`. The
comprehension already filters on `getattr(body_node, 'name', None)`; read the
value the same way so the type resolves. Type-equivalent (returns the same name
string, only for truthy-named statements). Clears `[attr-defined] .name`.

```python
# old
        names = [body_node.name for body_node in node.body if getattr(body_node, 'name', None)]
# new
        names = [getattr(body_node, 'name', None) for body_node in node.body if getattr(body_node, 'name', None)]
```

#### 3. `visit_ImportFrom` operates on `ast.ImportFrom`
**Action**: modify — clears `[override]` (`visit_ImportFrom`) and
`[attr-defined] .module`.

```python
# old
    def visit_ImportFrom(self, node: ast.Import) -> None:
        if node.module != '__future__':
            self.visit_Import(node)
# new
    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module != '__future__':
            self.visit_Import(node)
```

#### 4. Widen `visit_Import` to accept the delegated `ast.ImportFrom`
**Action**: modify — **DEVIATION from `structure.md`, required.** Once
`visit_ImportFrom`'s param is correctly `ast.ImportFrom`, the existing
`self.visit_Import(node)` delegation passes an `ast.ImportFrom` into
`visit_Import(node: ast.Import)`, producing a *new* `[arg-type]` error (count
would land at 33, not 32). `ast.ImportFrom` is **not** a subtype of `ast.Import`,
so widen the param to the union. This is a valid Liskov-contravariant override
(wider param than the base `visit_Import`), confirmed clean by mypy. The body uses
only `.names`/`.asname`/`.name`, present on both node types, so runtime is
unchanged.

```python
# old
    def visit_Import(self, node: ast.Import) -> None:
        # Adjust node by removing unused code items
        names = [e.asname or e.name.partition('.')[0] for e in node.names[::-1]]
# new
    def visit_Import(self, node: ast.Import | ast.ImportFrom) -> None:
        # Adjust node by removing unused code items
        names = [e.asname or e.name.partition('.')[0] for e in node.names[::-1]]
```

### Verification
#### Automated
- [x] `uv run mypy deadcode/ 2>&1 | grep -c ': error:'` → `32`
- [x] `just test` exits `0` (exercises the import/with-removal fix paths)

#### Manual
- [x] `uv run mypy deadcode/ 2>&1 | grep -E 'fix_unused_code_visitor.py' | grep -E 'override|has no attribute "(items|id|name|module)"'` → empty
- [x] `uv run mypy deadcode/ 2>&1 | grep -c 'visit_Import' ` → `0` (no leftover `arg-type` on the delegation)

---

## Phase 3: Position-bearing node reads via `cast` (32 → 15)

Single technique for every spot that reads `lineno` / `col_offset` /
`end_lineno` / `end_col_offset` off a statically-`ast.AST` value (typeshed
defines these on `ast.stmt`/`ast.expr`, not `ast.AST`). Use
`typing.cast('ast.stmt', node)` where recursion / generic dispatch makes the
static type genuinely `ast.AST` (Decision 4).

> **Two DEVIATIONS from `structure.md`, both required and validated:**
> 1. **Quoted cast type expressions.** Ruff rule `TC006` (enabled in this repo's
>    lint config) flags `cast(ast.stmt, x)` and requires `cast('ast.stmt', x)`.
>    Bare-symbol casts pass mypy but fail `just check-lint`. Use the quoted form
>    everywhere.
> 2. **`end_lineno` / `end_col_offset` are `int | None` on `ast.stmt`.** A bare
>    `cast('ast.stmt', node)` resolves the `[attr-defined]` errors but then those
>    two attributes are `Optional`, which breaks `Part(...)` (`int` fields) and
>    `... + 1`. Wrap each such read in `cast('int', ...)` — a pure type assertion,
>    zero runtime change (these are never `None` for a parsed node). Where the
>    code already guards with `or 0` (e.g. `find_unused_code_visitor`), no extra
>    cast is needed.

### Changes

#### 1. `lines.py` — cast the recursion node before `.lineno`
**File**: `deadcode/visitor/lines.py`
**Action**: modify. Add the `cast` import; cast at the three `.lineno` reads.
Resolves `[attr-defined]` at the reads and the two `[no-any-return]` (once the
read is typed `int`, the returns are no longer `Any`).

```python
# old (top of file)
import ast


def _get_last_child_with_lineno(node: ast.AST) -> ast.AST | None:
# new
import ast
from typing import cast


def _get_last_child_with_lineno(node: ast.AST) -> ast.AST | None:
```

```python
# old (in get_last_line_number)
    max_lineno = node.lineno
    while True:
        last_child = _get_last_child_with_lineno(node)
        if last_child is None:
            return max_lineno
        else:
            try:
                max_lineno = max(max_lineno, last_child.lineno)
# new
    max_lineno = cast('ast.stmt', node).lineno
    while True:
        last_child = _get_last_child_with_lineno(node)
        if last_child is None:
            return max_lineno
        else:
            try:
                max_lineno = max(max_lineno, cast('ast.stmt', last_child).lineno)
```

```python
# old (end of get_first_line_number)
        return lineno
    return node.lineno
# new
        return lineno
    return cast('ast.stmt', node).lineno
```

#### 2. `find_unused_code_visitor.py` — cast `last_node` in `_define`
**File**: `deadcode/visitor/find_unused_code_visitor.py`
**Action**: modify. Add `cast` to the `typing` import; introduce one narrowed
local and use it for the four position reads in the `CodeItem(...)` construction.
`end_col_offset or 0` already handles `Optional`, so no `cast('int', ...)` is
needed here.

```python
# old
from typing import TextIO
# new
from typing import TextIO, cast
```

```python
# old
        last_node = last_node or first_node
        type_: UnusedCodeType = collection.type_  # type: ignore
# new
        last_node = last_node or first_node
        last_node_with_position = cast('ast.stmt', last_node)
        type_: UnusedCodeType = collection.type_  # type: ignore
```

```python
# old
            code_parts=[Part(first_lineno, last_lineno, last_node.col_offset, last_node.end_col_offset or 0)],
            scope=self.scope,
            name_line=last_node.lineno,  # TODO: Maybe this should be a property?
            name_column=last_node.col_offset,  # TODO: Maybe this should be a property?
# new
            code_parts=[
                Part(
                    first_lineno,
                    last_lineno,
                    last_node_with_position.col_offset,
                    last_node_with_position.end_col_offset or 0,
                )
            ],
            scope=self.scope,
            name_line=last_node_with_position.lineno,  # TODO: Maybe this should be a property?
            name_column=last_node_with_position.col_offset,  # TODO: Maybe this should be a property?
```

> Keep the existing `# type: ignore` on the `type_ = collection.type_` line
> untouched — it is load-bearing and not one of the 42 errors.

#### 3. `fix_unused_code_visitor.py` — `get_original_code_lines`
**File**: `deadcode/visitor/fix_unused_code_visitor.py`
**Action**: modify. Add `cast` to the `typing` import (shared with Phase 5);
cast `node` to `ast.stmt`, and wrap the `end_col_offset` read (used in `... + 1`)
in `cast('int', ...)`. `end_lineno` needs no `int` cast — it is only a slice
bound, where `None` is allowed.

```python
# old
from typing import Any
from deadcode.data_types import Part, Filename
# new
from typing import Any, cast
from deadcode.data_types import Part, Filename
```

```python
# old
    def get_original_code_lines(self, node: ast.AST) -> list[str]:
        lines = self.file_content_lines[node.lineno - 1 : node.end_lineno]
        lines[0] = lines[0][node.col_offset :]
        lines[-1] = lines[-1][: node.end_col_offset + 1]
        return lines
# new
    def get_original_code_lines(self, node: ast.AST) -> list[str]:
        statement = cast('ast.stmt', node)
        lines = self.file_content_lines[statement.lineno - 1 : statement.end_lineno]
        lines[0] = lines[0][statement.col_offset :]
        lines[-1] = lines[-1][: cast('int', statement.end_col_offset) + 1]
        return lines
```

#### 4. `fix_unused_code_visitor.py` — `remove_node`
**Action**: modify. Cast `node` to `ast.stmt`; the two `Part` fields fed by
`end_lineno` / `end_col_offset` need `cast('int', ...)` (Part fields are `int`).

```python
# old
    def remove_node(self, node: ast.AST) -> None:
        self.additional_code_parts_to_remove[str(self.filename)].append(
            Part(node.lineno, node.end_lineno, node.col_offset, node.end_col_offset)
        )
# new
    def remove_node(self, node: ast.AST) -> None:
        statement = cast('ast.stmt', node)
        self.additional_code_parts_to_remove[str(self.filename)].append(
            Part(
                statement.lineno,
                cast('int', statement.end_lineno),
                statement.col_offset,
                cast('int', statement.end_col_offset),
            )
        )
```

### Verification
#### Automated
- [x] `uv run mypy deadcode/ 2>&1 | grep -c ': error:'` → `15`
- [x] `uv run ruff check deadcode/` → `All checks passed!` (confirms the quoted casts satisfy `TC006`)
- [x] `just test` exits `0` (line-number computation and node removal are exercised by the fix/diff tests)

#### Manual
- [x] `uv run mypy deadcode/ 2>&1 | grep -cE 'lines.py:'` → `0`
- [x] `uv run mypy deadcode/ 2>&1 | grep -E 'has no attribute "(lineno|col_offset|end_lineno|end_col_offset)"'` → empty
- [x] `grep -c "cast('ast.stmt'" deadcode/visitor/lines.py` → `3`

---

## Phase 4: Deprecated `ast.Str`/`.s` → `ast.Constant` (15 → 11)

**File**: `deadcode/visitor/find_unused_code_visitor.py`
**Action**: modify (four spots). Replace the removed-in-3.12 `ast.Str` / `.s`
API with `isinstance(node, ast.Constant) and isinstance(node.value, str)` then
read `node.value`. The added `str` check matches `ast.Str`'s old string-only
semantics, so runtime is unchanged; the typed `str` value clears the 4
`[arg-type]` errors (e.g. `re.findall`/`add_used_name` were receiving the
`ast.Constant.value` union `str | bytes | int | ... | None`).

#### 1. `visit_BinOp` (old `%`-format strings)
```python
# old
        if isinstance(node.left, ast.Str) and isinstance(node.op, ast.Mod) and self._is_locals_call(node.right):
            self.used_names |= set(re.findall(r'%\((\w+)\)', node.left.s))
# new
        if (
            isinstance(node.left, ast.Constant)
            and isinstance(node.left.value, str)
            and isinstance(node.op, ast.Mod)
            and self._is_locals_call(node.right)
        ):
            self.used_names |= set(re.findall(r'%\((\w+)\)', node.left.value))
```

#### 2. `visit_Call` — `getattr`/`hasattr` attr-name argument
```python
# old
            attr_name_arg = node.args[1]
            if isinstance(attr_name_arg, ast.Str):
                self.add_used_name(attr_name_arg.s)
# new
            attr_name_arg = node.args[1]
            if isinstance(attr_name_arg, ast.Constant) and isinstance(attr_name_arg.value, str):
                self.add_used_name(attr_name_arg.value)
```

#### 3. `visit_Call` — `"...".format(**locals())`
```python
# old
        if (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Str)
            and node.func.attr == 'format'
            and any(kw.arg is None and self._is_locals_call(kw.value) for kw in node.keywords)
        ):
            self._handle_new_format_string(node.func.value.s)
# new
        if (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Constant)
            and isinstance(node.func.value.value, str)
            and node.func.attr == 'format'
            and any(kw.arg is None and self._is_locals_call(kw.value) for kw in node.keywords)
        ):
            self._handle_new_format_string(node.func.value.value)
```

#### 4. `visit_Assign` — `__all__ = [...]` string elements
```python
# old
            for elt in node.value.elts:
                if isinstance(elt, ast.Str):
                    self.add_used_name(elt.s)
# new
            for elt in node.value.elts:
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                    self.add_used_name(elt.value)
```

### Verification
#### Automated
- [x] `uv run mypy deadcode/ 2>&1 | grep -c ': error:'` → `11`
- [x] `just test` exits `0`

#### Manual
- [x] `grep -c 'ast.Str' deadcode/visitor/find_unused_code_visitor.py` → `0`
- [x] `git diff -- deadcode/visitor/find_unused_code_visitor.py | grep -E '^-' | grep -c 'ast.Str'` → `4` (only removals)
- [x] `uv run mypy deadcode/ 2>&1 | grep -E '"findall"|add_used_name|_handle_new_format_string' | grep -c 'arg-type'` → `0`

---

## Phase 5: Helper annotation gaps (11 → 5)

Fill the remaining untyped params / var-annotation / missing-return gaps.

> **DEVIATION from `structure.md`, required and validated:** the structure
> outline annotates `remove_unused_fragments_from_a_line`'s `code_parts` (and its
> `:86` local) as `list[tuple[int, int, int, int]]`. That is **wrong** — the body
> unpacks each element as a **6-tuple** (`from_line, to_line, from_col, to_col,
> _insert_code, _insert_condition = ...`), and the runtime value passed in is
> `list[Part]` (a 6-field `NamedTuple`). Annotating it as a 4-tuple introduces
> **5 new errors** (`Need more than 4 values to unpack` ×3 plus 2 caller
> `arg-type`s). The correct annotation is `list[Part]`. The unrelated `:48` local
> inside `get_code_parts_for_the_same_line` (whose own param *is* a 4-tuple and is
> only indexed `[0]`/`[1]`) stays `list[tuple[int, int, int, int]]`.

> **Second consequence (validated):** annotating
> `add_code_adjustments_for_cleaned_up_code_items(self, node: ast.AST)` turns its
> previously-implicit-`Any` `node` into `ast.AST`, which surfaces **2 new
> `[attr-defined]`** errors at the `node.lineno` / `node.col_offset` reads in its
> body. Resolve them with the same `cast('ast.stmt', node)` pattern as Phase 3
> (the `cast` import is already added in Phase 3).

### Changes

#### 1. `remove_file_parts_from_content.py` — annotate the helper + its locals
**File**: `deadcode/actions/remove_file_parts_from_content.py`
**Action**: modify (three spots). `Part` is already imported (line 4).

`get_code_parts_for_the_same_line` local (4-tuple — matches that function's
4-tuple param; clears the `[var-annotated]`):
```python
# old (inside get_code_parts_for_the_same_line)
    code_parts_for_the_same_line = []
    line = None
# new
    code_parts_for_the_same_line: list[tuple[int, int, int, int]] = []
    line = None
```

`remove_unused_fragments_from_a_line` signature (`list[Part]`; clears the
`[no-untyped-def]`):
```python
# old
def remove_unused_fragments_from_a_line(line: str, code_parts, index: int) -> tuple[str, int]:
# new
def remove_unused_fragments_from_a_line(line: str, code_parts: list[Part], index: int) -> tuple[str, int]:
```

`remove_unused_fragments_from_a_line` local (`list[Part]`; clears the second
`[var-annotated]`):
```python
# old (inside remove_unused_fragments_from_a_line)
    code_parts_for_the_same_line = []
    for code_part in code_parts[index:]:
# new
    code_parts_for_the_same_line: list[Part] = []
    for code_part in code_parts[index:]:
```

#### 2. `fix_unused_code_visitor.py` — annotate `get_chars_to_remove` params
**File**: `deadcode/visitor/fix_unused_code_visitor.py`
**Action**: modify. Add the four param types. The return type stays
`list[tuple[int, int, int, int]]` for now and is changed to `list[Part]` in
Phase 6 (this edit clears the `[no-untyped-def]`).

```python
# old
    def get_chars_to_remove(
        self, original_code_lines, fixed_code, first_line, first_col
    ) -> list[tuple[int, int, int, int]]:
# new
    def get_chars_to_remove(
        self, original_code_lines: list[str], fixed_code: str, first_line: int, first_col: int
    ) -> list[tuple[int, int, int, int]]:
```

#### 3. `fix_unused_code_visitor.py` — `add_code_adjustments_for_cleaned_up_code_items`
**Action**: modify. Annotate the param `ast.AST` and the return `-> None` (all
three call sites discard the result; the body has no `return`, so `-> None`
resolves both the `[no-untyped-def]` and the `[return]`/missing-return error).
Then cast `node` for the two position reads it surfaces.

```python
# old
    def add_code_adjustments_for_cleaned_up_code_items(self, node) -> str:
# new
    def add_code_adjustments_for_cleaned_up_code_items(self, node: ast.AST) -> None:
```

```python
# old
        code_parts_to_remove = self.get_chars_to_remove(
            original_code_lines, fixed_code, node.lineno, node.col_offset
        )  # TODO: test with multiline code blocks
# new
        statement = cast('ast.stmt', node)
        code_parts_to_remove = self.get_chars_to_remove(
            original_code_lines, fixed_code, statement.lineno, statement.col_offset
        )  # TODO: test with multiline code blocks
```

### Verification
#### Automated
- [x] `uv run mypy deadcode/ 2>&1 | grep -c ': error:'` → `5`
- [x] `uv run mypy deadcode/ 2>&1 | grep -c 'remove_file_parts_from_content.py:'` → `0`
- [x] `just test` exits `0`

#### Manual
- [x] `uv run mypy deadcode/ 2>&1 | grep -c 'unpack'` → `0` (confirms `list[Part]` did not introduce unpack errors)
- [x] `uv run mypy deadcode/ 2>&1 | grep -E 'add_code_adjustments|get_chars_to_remove'` → empty
- [x] Remaining 5 errors are exactly the Phase 6 cluster:
      `uv run mypy deadcode/ 2>&1 | grep ': error:'` lists only
      `fix_or_show_unused_code.py` (extend), `fix_unused_code_visitor.py`
      (`convert_1d_part_to_2d` return + `extend`), `find_unused_names.py`
      (return-value), and `cli.py` (arg-type).

---

## Phase 6: `Part` pipeline re-typing — capstone (5 → 0)

Re-type the second pipeline element from the lying
`list[tuple[int, int, int, int]]` / `dict[Filename, list[tuple[int,int,int,int]]]`
to the runtime truth `dict[Filename, list[Part]]`, end-to-end. `Part` carries the
extra `insert_code*` fields the removal algorithm relies on, so re-typing to
`Part` (not flattening to 4-tuples) is correct.

> **Fan-out is contained (validated).** `merge_overlaping_file_parts.py` already
> types every param/return as `Part`, and `remove_file_parts_from_content.py` was
> already corrected to `list[Part]` in Phase 5. Re-running `mypy` after the
> boundary edits surfaces **no** follow-on errors — the count goes straight to 0.

### Changes

#### 1. `find_unused_names.py` — return the dict-of-`Part`
**File**: `deadcode/actions/find_unused_names.py`
**Action**: modify. Import `Part`; correct the second return-tuple element. Clears
the `[return-value]`.

```python
# old
from deadcode.data_types import Args, Filename
# new
from deadcode.data_types import Args, Filename, Part
```

```python
# old
) -> tuple[Iterable[CodeItem], list[tuple[int, int, int, int]]]:
# new
) -> tuple[Iterable[CodeItem], dict[Filename, list[Part]]]:
```

#### 2. `fix_or_show_unused_code.py` — accept the dict-of-`Part`
**File**: `deadcode/actions/fix_or_show_unused_code.py`
**Action**: modify. Import `Part`; correct the param type. The `.extend(...)` at
the merge site is then `Part`-typed, clearing its `[arg-type]`.

```python
# old
from deadcode.data_types import Args, Filename
# new
from deadcode.data_types import Args, Filename, Part
```

```python
# old
    additional_code_parts_to_remove: dict[Filename, list[tuple[int, int, int, int]]],
# new
    additional_code_parts_to_remove: dict[Filename, list[Part]],
```

#### 3. `cli.py` — call site auto-resolves
**File**: `deadcode/cli.py`
**Action**: none. Once both ends agree on `dict[Filename, list[Part]]`, the
`fix_or_show_unused_code(unused_names, additional_code_parts_to_remove, ...)` call
type-checks with no edit. (Listed for completeness; verify its `[arg-type]` is
gone.)

#### 4. `fix_unused_code_visitor.py` — return `Part` from the builders
**File**: `deadcode/visitor/fix_unused_code_visitor.py`
**Action**: modify (two return types). `convert_1d_part_to_2d` already builds and
returns a `Part`, so its declared `tuple[int, int, int, int]` is the lie
(`Part`'s 6 fields are not assignable to a 4-tuple) — clears `[return-value]`.
Re-typing `get_chars_to_remove`'s return to `list[Part]` then makes its
`.extend(...)` site `Part`-typed — clears that `[arg-type]`.

```python
# old
        self, from_char: int, to_char: int, line_lengths: list[int], first_line: int, first_col: int
    ) -> tuple[int, int, int, int]:
# new
        self, from_char: int, to_char: int, line_lengths: list[int], first_line: int, first_col: int
    ) -> Part:
```

```python
# old
        self, original_code_lines: list[str], fixed_code: str, first_line: int, first_col: int
    ) -> list[tuple[int, int, int, int]]:
# new
        self, original_code_lines: list[str], fixed_code: str, first_line: int, first_col: int
    ) -> list[Part]:
```

> `Part` is already imported in `fix_unused_code_visitor.py`
> (`from deadcode.data_types import Part, Filename`); no import edit needed here.

### Verification
#### Automated
- [x] `just check-typecheck` prints `Success: no issues found in 29 source files` and exits `0`
- [x] `uv run mypy deadcode/ 2>&1 | grep -c ': error:'` → `0`
- [x] `uv run ruff check deadcode/` → `All checks passed!`
- [x] `uv run ruff format --check deadcode/` → `29 files already formatted`
- [x] `just test` exits `0` (validated: 176 passed, 18 skipped, coverage 98.84% ≥ 95%)

#### Manual
- [x] `uv run mypy deadcode/ 2>&1 | grep -cE 'cli.py:|find_unused_names.py:|fix_or_show_unused_code.py:'` → `0`
- [x] `git diff -- deadcode/ | grep -E '^\+' | grep -c 'type: ignore'` → `0` (no suppression added across the whole change)
- [x] `git diff -- deadcode/ | grep -E '^-' | grep -c 'type: ignore'` → `1` (the stray ignore removed in Phase 1)

---

## Out of Scope (do not touch)

Per `design.md` "What We're NOT Doing":

- **`visit_MatchClass`** (`find_unused_code_visitor.py`, `def visit_MatchClass(self, node) -> None:  # type: ignore`)
  is **not** among the 42 errors; its `# type: ignore` is currently load-bearing.
  Leave it untouched.
- The `# type: ignore` on `_log` and on the `type_ = collection.type_` line — both
  load-bearing, not in the 42; leave untouched.
- No `from __future__ import annotations`; no `CodeItem` → dataclass conversion;
  no touching the commented-out `VariableInfo` block.
- No mypy-config relaxation, per-module overrides, or file exclusions.
- No annotating `tests/` (mypy targets only `deadcode/`).
- **Pre-existing, out-of-scope failures:** `just check-complexity` reports 2
  pre-existing `C901` errors (`remove_file_parts_from_content` 24>10, `visit`
  19>10). These exist at baseline, are unrelated to typing, and must **not** be
  "fixed" here. Consequently, full `just check` is *not* a success gate for this
  task — use `just check-typecheck` + `just check-lint` + `just check-format` +
  `just test`.

## Summary of deviations from `structure.md` (all validated live)

1. **Phase 2 adds a 4th edit:** widen `visit_Import` to
   `ast.Import | ast.ImportFrom`, otherwise fixing `visit_ImportFrom` leaves a new
   `[arg-type]` on the delegation (count 33, not 32).
2. **Phase 3/5 casts are quoted** (`cast('ast.stmt', …)`, `cast('int', …)`) to
   satisfy ruff `TC006`, and `end_lineno`/`end_col_offset` get `cast('int', …)`
   because they are `Optional` on `ast.stmt`.
3. **Phase 5 uses `list[Part]`** (not `list[tuple[int,int,int,int]]`) for
   `remove_unused_fragments_from_a_line` and its `:86` local — the body unpacks
   6-tuples; the 4-tuple annotation would add 5 errors. Phase 5 also casts the two
   position reads exposed by annotating `add_code_adjustments_...`'s `node`.
4. **Checkpoint counts corrected** to 38 / 32 / 15 / 11 / 5 / 0 (the structure
   table's 20 / 16 / 10 mid-values undercounted the Phase 3 position cluster).

The phase *order* and *content boundaries* from `structure.md` are otherwise
preserved exactly.
