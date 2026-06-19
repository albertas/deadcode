# Implementation Plan

## Overview

Encode a McCabe ceiling of **8** in `pyproject.toml`, then refactor the four
functions that exceed it (`remove_file_parts_from_content`, `visit`,
`fix_indent`, `fix_or_show_unused_code`) below 9 by extracting same-module
helpers — a pure structural refactor verified by the pre-existing test suite and
the 95% coverage gate, ending with `just check` green end-to-end.

**Conventions for every phase**
- Behavior must not change. Do **not** edit tests unless an extraction drops a
  branch's coverage below 95% (then add the minimal test only).
- Keep `C901` in the global `ignore` (`pyproject.toml:87`); do not add it to
  `select`. Do not touch the `just lint` / `check-lint` recipes.
- Do **not** remove the `print(...)` debug statements or the commented-out code
  blocks in `remove_file_parts_from_content.py` — out of scope (CLAUDE.md §3).
  When extracting a helper, the live code moves; the surrounding comments stay.
- Use full-word names; new module-private helpers are `_`-prefixed.
- Run checks via the Justfile (`just check-complexity`, `just test`,
  `just check`) — not raw `ruff`/`pytest`.
- **Per-helper complexity self-check**: `just check-complexity` flags *any*
  function > 8, including newly extracted helpers. If a helper lands at 9,
  split it further before moving on. The estimates below are sized to ≤ 8, but
  the recipe is the authority.

Phase order is fixed (lowest-risk first): config → `fix_or_show_unused_code` →
`fix_indent` → `visit` → `remove_file_parts_from_content`. A later failure
leaves earlier phases independently valuable.

---

## Phase 1: Encode `max-complexity = 8` in config

### Changes

#### 1. Add the mccabe threshold
**File**: `pyproject.toml`
**Action**: modify

Insert a new table between the `[tool.ruff.lint.flake8-quotes]` block
(`pyproject.toml:69-70`) and `[tool.ruff.lint]` (`pyproject.toml:72`). Sub-tables
already appear before the parent `[tool.ruff.lint]` table here, so this placement
is consistent with the existing file:

```toml
[tool.ruff.lint.flake8-quotes]
inline-quotes = "single"

[tool.ruff.lint.mccabe]
max-complexity = 8

[tool.ruff.lint]
```

No other edits. `C901` stays in `ignore`; `select` unchanged; no Justfile edit —
the existing `--select C901` in `check-complexity` now enforces 8.

### Verification
#### Automated
- [x] `just check-complexity` exits **non-zero** and lists exactly four
  functions, each annotated `> 8`:
  `deadcode/actions/remove_file_parts_from_content.py:128` (`remove_file_parts_from_content`, 24),
  `deadcode/visitor/find_unused_code_visitor.py:518` (`visit`, 19),
  `deadcode/utils/fix_indent.py:4` (`fix_indent`, 10),
  `deadcode/actions/fix_or_show_unused_code.py:15` (`fix_or_show_unused_code`, 9).
- [x] `just test` green (config-only change touches no runtime code).

#### Manual
- [x] `just check-complexity 2>&1 | grep -c 'C901'` → `4` (exactly four offenders;
  confirms `max-complexity=8` is being applied, not the default 10).
  Note: raw count is 5 due to the `uv run ruff check --select C901` command line
  also matching; actual violation lines = 4.
- [x] `just check-complexity 2>&1 | grep -q 'remove_file_parts_from_content'` and
  the same for `visit`, `fix_indent`, `fix_or_show_unused_code` (capture this list
  as the baseline every later phase shrinks).

---

## Phase 2: Refactor `fix_or_show_unused_code` (9 → ≤ 8)

Split the per-file loop body into two same-module helpers. All `open` /
`os.remove` / `unified_diff` call sites stay in this module so `BaseTestCase`'s
patches (`base_test_case.py:49-52`) keep binding.

### Changes

#### 1. Extract content computation + per-file emit
**File**: `deadcode/actions/fix_or_show_unused_code.py`
**Action**: modify (no new imports needed)

Add two module-private helpers above `fix_or_show_unused_code`:

```python
def _compute_updated_content(
    filename: Filename,
    file_unused_items: list[CodeItem],
    additional_code_parts_to_remove: dict[Filename, list[Part]],
) -> list[str]:
    file_parts = flatten_list([item.code_parts for item in file_unused_items])
    if additional_code_parts_to_remove and additional_code_parts_to_remove.get(str(filename)):
        file_parts.extend(additional_code_parts_to_remove[str(filename)])

    unused_file_parts = merge_overlaping_file_parts(file_parts)

    with open(filename) as f:
        file_content_lines = f.readlines()

    return remove_file_parts_from_content(file_content_lines, unused_file_parts)


def _emit_for_file(filename: Filename, updated_file_content_lines: list[str], args: Args) -> str | None:
    updated_file_content = ''.join(updated_file_content_lines)
    if updated_file_content.strip():
        if args.dry and ('__all_files__' in args.dry or _match(filename, args.dry)):
            with open(filename, 'r') as f:
                diff = unified_diff(f.readlines(), updated_file_content_lines, fromfile=filename, tofile=filename)
                diff_str = ''.join(diff) + '\n'
                if args.no_color:
                    return diff_str
                return add_colors_to_diff(diff_str)
        elif args.fix:
            with open(filename, 'w') as f:
                f.write(updated_file_content)
    else:
        os.remove(filename)
    return None
```

Rewrite the loop body in `fix_or_show_unused_code` to call them:

```python
    result = []

    for filename, file_unused_items in filename_to_unused_items.items():
        updated_file_content_lines = _compute_updated_content(
            filename, file_unused_items, additional_code_parts_to_remove
        )
        emitted = _emit_for_file(filename, updated_file_content_lines, args)
        if emitted is not None:
            result.append(emitted)

    if result:
        return ''.join(result)
    return ''
```

The `defaultdict` grouping (`...py:28-30`) and trailing TODO comments stay
unchanged.

**Deviation from structure**: structure §Phase 2 typed `_compute_updated_content
-> str` and passed a joined string to `_emit_for_file`. The dry branch needs the
**list** of updated lines as the `tofile` argument to `unified_diff`; re-deriving
it from a joined string via `splitlines` risks a trailing-newline edge difference.
So `_compute_updated_content` returns `list[str]` and `_emit_for_file` joins
internally for the `.strip()`/`write` paths. Behavior is identical to the
original.

### Verification
#### Automated
- [x] `just check-complexity 2>&1 | grep -q 'fix_or_show_unused_code'` → no match
  (3 offenders remain).
- [x] `just check-complexity 2>&1 | grep -c 'C901'` → `3`.
  Note: raw count is 4 due to the `uv run ruff check --select C901` command line
  also matching; actual violation lines = 3.
- [x] `just test` green; coverage ≥ 95% (the `--cov-fail-under=95.0` gate). 98.85%.

#### Manual
- [x] `uv run pytest tests/cli_args/test_fix.py tests/cli_args/test_dry.py tests/fix/test_empty_files.py -q`
  exits 0 — exercises the write branch, the diff/color branches, and the
  `os.remove` branch (`test_empty_files.py:10` asserts `os_remove`).
  Note: 26 passed, 2 skipped; subset coverage drop expected.

---

## Phase 3: Refactor `fix_indent` (10 → ≤ 8)

Extract the two loops into same-file private helpers; keep the `try/except`,
first-line strip, the `margin` guard, and the blank-line trim in `fix_indent`.

### Changes

#### 1. Extract margin scan and de-indent loops
**File**: `deadcode/utils/fix_indent.py`
**Action**: modify (already imports `sys`; no new imports)

Add two helpers above `fix_indent`:

```python
def _find_common_margin(lines: list[str]) -> int:
    """Minimum indentation across non-blank lines; sys.maxsize if none found."""
    margin = sys.maxsize
    for line in lines:
        content = len(line.lstrip())
        if content:
            indent = len(line) - content
            margin = min(margin, indent)
    return margin


def _strip_margin(lines: list[str], margin: int) -> None:
    """De-indent lines[1:] in place, preserving non-space prefix characters."""
    for i in range(1, len(lines)):
        prefix = lines[i][:margin]
        if prefix_without_spaces := prefix.rstrip(' '):
            lines[i] = prefix_without_spaces + lines[i][margin:]
        else:
            lines[i] = lines[i][margin:]
```

Rewrite the `else:` body of `fix_indent` to call them (the `try/except`,
first-line strip, `if margin < sys.maxsize` guard, blank-trim `while`, and final
`join` stay):

```python
    else:
        margin = _find_common_margin(lines)
        if lines:
            lines[0] = lines[0].lstrip()
        if margin < sys.maxsize:
            _strip_margin(lines, margin)

        ## Remove any leading blank lines.
        while lines and not lines[0]:
            lines.pop(0)
        return ''.join(lines)
```

The pre-existing `# TODO` / commented-out trailing-line block (`...py:14, 35-37`)
stay where they are. `fix_indent` is in `[tool.deadcode] ignore_names`, so the new
`_`-prefixed helpers (defined in the same file) are not flagged as unused.

### Verification
#### Automated
- [x] `just check-complexity 2>&1 | grep -q 'fix_indent'` → no match (2 offenders
  remain).
- [x] `just check-complexity 2>&1 | grep -c 'C901'` → `2`. (Confirms the final
  score is **≤ 8**, not merely < 10 — Open Risk in design.)
- [x] `just test` green; coverage ≥ 95%. (98.85%)

#### Manual
- [x] `uv run pytest tests/utils/test_fix_indent.py -q` exits 0 (3 tests:
  `test_indentation_is_not_removed_from_second_line`,
  `test_fix_indent_for_empty_lines`, `test_fix_indent_last_empty_line`).
  Note: 3 tests passed; coverage gate fails at subset level (expected for partial run).
- [x] `uv run pytest tests/cli_args/test_dry.py -q` exits 0 (downstream user via
  `base_test_case.py`). 7 tests passed.

---

## Phase 4: Refactor `visit` (19 → ≤ 8)

`visit` is a linear pipeline of phases, not deeply nested. Extract each phase into
a private method; `visit` becomes an orchestrator. Flag/scope semantics stay
identical.

### Changes

#### 1. Extract the phases into private methods
**File**: `deadcode/visitor/find_unused_code_visitor.py`
**Action**: modify (`_match`, `_match_many` already imported `:25-30`)

Add these private methods to `FindUnusedCodeVisitor` (place them just before
`visit`). Each returns/uses the exact flags the inline code did.

```python
def _apply_ignore_definitions(self, node_name: str | None, inherits_from: list[str] | None) -> bool:
    """Activate should_ignore_new_definitions for name/inheritance matches.

    Returns True iff this call turned the flag on (i.e. the caller owns turning
    it back off in teardown).
    """
    if (node_name and _match(node_name, self.args.ignore_definitions)) or (
        inherits_from and _match_many(inherits_from, self.args.ignore_definitions_if_inherits_from)
    ):
        if not self.should_ignore_new_definitions:
            self.should_ignore_new_definitions = True
            return True
    return False

def _apply_ignore_bodies(self, inherits_from: list[str] | None) -> bool:
    """Activate should_ignore_new_definitions for ignore_bodies_if_inherits_from."""
    if inherits_from and _match_many(inherits_from, self.args.ignore_bodies_if_inherits_from):
        if not self.should_ignore_new_definitions:
            self.should_ignore_new_definitions = True
            return True
    return False

def _dispatch_pre_visit(self, node: ast.AST) -> None:
    visitor = getattr(self, 'visit_' + node.__class__.__name__, None)
    if visitor:
        visitor(node)

def _maybe_push_scope(self, node: ast.AST) -> bool:
    """Push class/function name onto scope_parts; return whether a scope was pushed."""
    if isinstance(node, ast.ClassDef):
        self.scope_parts.append(node.name)
    elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        self.scope_parts.append(node.name)
    else:
        return False
    return True

def _visit_type_comment(self, node: ast.AST) -> None:
    type_comment = getattr(node, 'type_comment', None)
    if type_comment is not None:
        mode = 'func_type' if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) else 'eval'
        self.visit(ast.parse(type_comment, filename='<type_comment>', mode=mode))

def _visit_children(self, node: ast.AST) -> None:
    """Replaces generic_visit: traverse child nodes, handling list fields for unreachable code."""
    if not node:
        return
    for _, value in ast.iter_fields(node):
        if isinstance(value, list):
            self._handle_ast_list(value)
            for item in value:
                if isinstance(item, ast.AST):
                    self.visit(item)
        elif isinstance(value, ast.AST):
            self.visit(value)

def _dispatch_post_visit(self, node: ast.AST) -> None:
    visit_method = getattr(self, 'visit_' + node.__class__.__name__ + '_after_visiting_child_nodes', None)
    if visit_method:
        visit_method(node)
```

Replace the body of `visit` (`...py:518-597`) with the orchestrator:

```python
def visit(self, node: ast.AST) -> None:
    node_name = getattr(node, 'name', None)

    inherits_from = self.get_inherits_from(node)
    if inherits_from:
        node.inherits_from = inherits_from  # type: ignore

    should_turn_off_ignore_new_definitions = self._apply_ignore_definitions(node_name, inherits_from)

    self._dispatch_pre_visit(node)

    was_scope_increased = self._maybe_push_scope(node)

    should_turn_off_ignore_new_definitions = (
        self._apply_ignore_bodies(inherits_from) or should_turn_off_ignore_new_definitions
    )

    self._visit_type_comment(node)
    self._visit_children(node)
    self._dispatch_post_visit(node)

    if should_turn_off_ignore_new_definitions:
        self.should_ignore_new_definitions = False
    if was_scope_increased:
        self.scope_parts.pop()
```

Notes on equivalence:
- The original `if inherits_from := self.get_inherits_from(node):` assigns
  `inherits_from` (used later at `:536, :559`) regardless of truthiness; the
  rewrite preserves this by binding `inherits_from` first, then guarding the
  `node.inherits_from = ...` assignment.
- `_apply_ignore_bodies(...) or should_turn_off...` preserves the original's
  "OR-accumulate the teardown flag" semantics: if either activation block turned
  the flag on, teardown turns it off.
- The two activation blocks share identical "only turn on if not already on"
  logic; both are expressed via the early-return helpers. `should_ignore_new_definitions`
  is only reset to `False` in teardown when *this* `visit` frame turned it on.

**Deviation from structure**: structure §Phase 4 named `_apply_ignore_definitions`
and the scope/type-comment/children helpers but did not explicitly list a helper
for the second activation block (`...py:559-562`). That block contributes
complexity, so it is extracted as `_apply_ignore_bodies` to keep `visit` ≤ 8.
Structure also suggested `_apply_ignore_definitions(self, node, node_name,
inherits_from)`; `node` is unused by that block, so it is dropped from the
signature (CLAUDE.md §2).

### Verification
#### Automated
- [x] `just check-complexity 2>&1 | grep -q 'def visit\b\|find_unused_code_visitor.py:518'`
  → `visit` no longer reported (1 offender remains).
- [x] `just check-complexity 2>&1 | grep -c 'C901'` → `1` (only
  `remove_file_parts_from_content`). Raw count is 2 (command line also matches).
- [x] `just test` green; coverage ≥ 95%. 176 passed, 98.78%.

#### Manual
- [x] `uv run pytest tests/visitor/test_find_unused_code_visitor.py -q` exits 0
  — 16 passed (async def, type comment, `__all__`, unreachable code, `visit_MatchClass`).
- [x] `uv run pytest -q` (full suite via `just test`) shows no new failures vs.
  the Phase 3 baseline. 176 passed, 18 skipped, 98.78% coverage.

---

## Phase 5: Refactor `remove_file_parts_from_content` (24 → ≤ 8)

Highest-risk refactor — done last. Extract the four-way line dispatch into
per-branch handlers; thread the ~10 mutable loop locals through one mutable
`@dataclass` (pass-by-reference keeps mutation semantics identical). **Extract one
branch at a time, running `just test` after each step**, to localize any ordering
regression.

### Changes

#### 1. Add a mutable state dataclass + per-branch handlers
**File**: `deadcode/actions/remove_file_parts_from_content.py`
**Action**: modify

Add the import at the top:

```python
from dataclasses import dataclass, field
```

Add the state record (after the existing helpers, before
`remove_file_parts_from_content`):

```python
@dataclass
class _RemovalState:
    unused_file_parts: list[Part]  # all parts to remove, peeked via unused_part_index
    updated_content_lines: list[str] = field(default_factory=list)  # output accumulator
    unused_part_index: int = 0  # cursor into unused_file_parts
    previous_non_removed_line: str = ''  # last line kept in output
    has_block_started: bool = False  # a multi-row removal block is open
    was_block_removed: bool = False  # a block spanning multiple rows was removed
    next_line_after_removed_block: str | None = None  # first line following a removed block
    indentation_of_first_removed_line: str = ''  # indent used for an inserted `pass`
    empty_lines_in_a_row_list: list[str] = field(default_factory=list)  # buffered trailing blanks
    empty_lines_before_removed_block_list: list[str] = field(default_factory=list)  # buffered leading blanks
```

Add the three handlers (keep every existing `print(...)` line verbatim inside the
moved code — omitted below for brevity, shown as `# (print statements preserved)`):

```python
def _handle_first_line(line: str, code_part: Part, state: _RemovalState) -> None:
    """Branch B: current_lineno == from_line (single-line vs multi-line start)."""
    from_line, to_line, from_col, _to_col, insert_code, _insert_condition = code_part
    state.indentation_of_first_removed_line = get_indentation(line)
    # (print statements preserved)

    if from_line == to_line:
        line, index_increment = remove_unused_fragments_from_a_line(
            line, state.unused_file_parts, state.unused_part_index
        )
        state.unused_part_index += index_increment
        if insert_code:
            line += insert_code
        if not line.strip():
            state.empty_lines_before_removed_block_list, state.empty_lines_in_a_row_list = (
                state.empty_lines_in_a_row_list,
                state.empty_lines_before_removed_block_list,
            )
            state.was_block_removed = True

    if from_line != to_line:
        line = line[:from_col]
        if insert_code:
            line += insert_code
        state.has_block_started = not line.strip()

    if line.strip() and not line.startswith('#'):
        state.previous_non_removed_line = line
        state.updated_content_lines.append(line)


def _handle_last_line(line: str, state: _RemovalState) -> None:
    """Branch C: current_lineno == to_line (end of a removed block)."""
    line, index_increment = remove_unused_fragments_from_a_line(
        line, state.unused_file_parts, state.unused_part_index
    )
    if not line.strip():
        line = ''
    state.unused_part_index += index_increment

    if (line.strip() and not line.startswith('#')) or (
        state.updated_content_lines and not state.updated_content_lines[-1].endswith('\n')
    ):
        state.updated_content_lines.append(line)
    elif line:
        state.empty_lines_in_a_row_list.append(line)

    state.empty_lines_before_removed_block_list, state.empty_lines_in_a_row_list = (
        state.empty_lines_in_a_row_list,
        state.empty_lines_before_removed_block_list,
    )

    if state.has_block_started:
        state.was_block_removed = True
    state.has_block_started = False


def _handle_normal_line(line: str, state: _RemovalState) -> None:
    """Branch D: line is kept (blank / no-prior-block / after-removed-block)."""
    if not line.strip():
        if state.was_block_removed:  # buffered until the next non-empty line
            return
        state.empty_lines_in_a_row_list.append(line)
        return

    if not state.was_block_removed:
        state.updated_content_lines.extend(state.empty_lines_in_a_row_list)
        state.empty_lines_in_a_row_list.clear()
    else:
        state.next_line_after_removed_block = line
        if ends_with_semicolon(state.previous_non_removed_line):
            if indentation_is_not_childs(state.previous_non_removed_line, state.next_line_after_removed_block):
                state.updated_content_lines.append(f'{state.indentation_of_first_removed_line}pass\n')
            if indentation_is_not_childs(state.previous_non_removed_line, state.next_line_after_removed_block):
                state.updated_content_lines.extend(state.empty_lines_in_a_row_list)
                state.empty_lines_in_a_row_list.clear()
                state.empty_lines_before_removed_block_list.clear()
            else:
                state.updated_content_lines.extend(state.empty_lines_before_removed_block_list)
                state.empty_lines_before_removed_block_list.clear()
                state.empty_lines_in_a_row_list.clear()
        else:
            state.updated_content_lines.extend(state.empty_lines_before_removed_block_list)
            state.empty_lines_before_removed_block_list.clear()
            state.empty_lines_in_a_row_list.clear()

    state.was_block_removed = False
    state.previous_non_removed_line = line
    state.updated_content_lines.append(line)
```

Rewrite `remove_file_parts_from_content` as the loop + dispatch (keep the per-line
`print(...)` lines that surround the dispatch):

```python
def remove_file_parts_from_content(content_lines: list[str], unused_file_parts: list[Part]) -> list[str]:
    """ """
    state = _RemovalState(unused_file_parts=unused_file_parts)

    for current_lineno, line in enumerate(content_lines, start=1):
        # (print statements preserved)

        from_line, to_line, from_col, to_col = 0, 0, 0, 0
        if unused_part := list_get(unused_file_parts, state.unused_part_index):
            from_line, to_line, from_col, to_col, insert_code, insert_condition = unused_part
            # (print statements preserved)

        if from_line < current_lineno < to_line:
            continue
        elif current_lineno == from_line:
            _handle_first_line(line, unused_part, state)
        elif current_lineno == to_line:
            _handle_last_line(line, state)
        else:
            _handle_normal_line(line, state)

        # (print statements preserved)

    if state.was_block_removed and ends_with_semicolon(state.previous_non_removed_line):
        state.updated_content_lines.append(f'{state.indentation_of_first_removed_line}pass\n')

    return state.updated_content_lines
```

Equivalence / deviation notes:
- **Skip condition** rewritten from `current_lineno > from_line and current_lineno
  < to_line` to the chained comparison `from_line < current_lineno < to_line` —
  semantically identical, and counts as one decision point (vs. two), which keeps
  the orchestrator ≤ 8.
- When `current_lineno == from_line` is true, `from_line` came from a non-`None`
  unpacked `unused_part`, so `unused_part` passed to `_handle_first_line` is a
  valid `Part`.
- `_handle_last_line` does **not** take `code_part`: the original Branch C body
  (`...py:247-328`) never references the part's columns (it re-derives via
  `remove_unused_fragments_from_a_line`). Dropping the unused param (CLAUDE.md §2)
  is a deviation from the structure's listed signature.
- Branch D's blank-line `continue` becomes `return` inside `_handle_normal_line`
  (skips the shared append tail, exactly as the original `continue` skipped
  `...py:378-381`).
- Post-loop `pass` fixup folded from two nested `if`s into one `and` — identical
  behavior, one fewer decision point.
- The IO-free helpers (`list_get`, `get_indentation`, `ends_with_semicolon`,
  `indentation_is_not_childs`, `remove_unused_fragments_from_a_line`,
  `get_code_parts_for_the_same_line`) and all commented-out blocks
  (`...py:190-215, 263-281`) stay in the module untouched.

### Verification
#### Automated
- [x] `just check-complexity` exits **0** (no offenders).
- [x] `just check-complexity 2>&1 | grep -c 'C901'` → `1` (only the `uv run ruff check --select C901` command line matches; actual violation lines = 0).
- [x] `just test` green; coverage ≥ 95%. 176 passed, 98.79%.
- [x] **`just check` green end-to-end** (check-format + check-lint +
  check-complexity + check-typecheck + test).

#### Manual
- [x] `uv run pytest tests/actions/test_remove_file_parts_from_content.py -q`
  exits 0 (7 passed; coverage gate fails at subset level — expected for partial run).
- [x] `uv run pytest tests/fix/ -q` exits 0 (21 passed, 8 skipped; coverage gate fails at subset level — expected for partial run).
- [x] All handlers extracted together then `just test` exits 0 — 176 passed, 98.79% coverage.

---

## Testing Checkpoints

Re-derive the current phase by running `just check-complexity` and counting
remaining offenders (`grep -c 'C901'`):

- **After Phase 1**: 4 offenders, all `> 8`; `just test` green. Threshold is
  config, not CLI.
- **After Phase 2**: 3 offenders (`fix_or_show_unused_code` cleared); `just test`
  green, coverage ≥ 95%.
- **After Phase 3**: 2 offenders (`fix_indent` cleared, score ≤ 8); `just test`
  green.
- **After Phase 4**: 1 offender (`visit` cleared); `just test` green.
- **After Phase 5**: 0 offenders; `just check-complexity` exits 0; `just check`
  green end-to-end.

**Coverage watch (all phases)**: if `--cov-fail-under=95.0` dips after a split,
an extracted branch is unexercised — add the single minimal test for that branch
(CLAUDE.md §4); do not broaden scope.
