# Implementation Plan

## Overview

Make `just test` pass (0 failed, 2 skipped, coverage ≥ 88) by fixing three
independent failures in the code-removal / diff-rendering pipeline: one stale
test expectation (7a), and two production bugs (7b nested `with ... as` removal
eating body indentation; 7c multi-line import removal dropping an interior blank
line). Each phase is independently verifiable via its own test file.

### Shared verification harness

To run a single test file in isolation (coverage `addopts` disabled so
`pytest-cov`/coverage-floor does not interfere):

```
uv run pytest <file> -o addopts=""
```

The final regression gate uses the real project command: `just test`.

### Pre-flight: reproduce all three failures

Before editing, confirm the baseline (per design decision 5):

```
uv run pytest tests/cli_args/test_dry.py tests/cli_args/test_fix.py tests/fix/test_unused_imports_in_a_single_file.py -o addopts=""
```

Expect **3 failed, 27 passed, 2 skipped**.

### Path correction (deviation from structure.md / design.md)

`structure.md` (Phase 3) and `design.md` reference
`deadcode/utils/remove_file_parts_from_content.py`. The file actually lives at
**`deadcode/actions/remove_file_parts_from_content.py`** (confirmed via glob;
`research.md` Q3 also refers to it without the `utils/` prefix). All line
numbers cited in structure/design still match. This plan uses the correct
`deadcode/actions/` path. No other deviations.

---

## Phase 1: 7a — Update stale `--dry` diff expectation (test-only)

### Changes

#### 1. Fix the stale `+` diff line

**File**: `tests/cli_args/test_dry.py`
**Action**: modify

Inside `test_coloring_of_a_diff` (`:240-304`), line 273 asserts the old buggy
`as :` form. Production already emits the clean `with open("tmp.txt", "r"):`.
Remove the 4 chars ` as ` from the green-wrapped `+` line.

Current (`test_dry.py:273`):

```
                \x1b[0m\x1b[32m+with open("tmp.txt", "r") as :
```

New:

```
                \x1b[0m\x1b[32m+with open("tmp.txt", "r"):
```

No other line in the `:240-304` block repeats the `as :` form (the `-` line at
`:272` is the *original* source `... as unused_var:` and must stay unchanged — it
is the red/removed line, not the rewritten output). No production code touched.
No type/interface changes.

### Verification

#### Automated
- [x] `uv run pytest tests/cli_args/test_dry.py -o addopts=""` → 0 failed.

#### Manual
- [x] `grep -n 'as :' tests/cli_args/test_dry.py` → no matches anywhere in the
  file (the only occurrence was line 273).
- [x] `grep -n '+with open("tmp.txt", "r"):' tests/cli_args/test_dry.py` →
  matches line 273.

---

## Phase 2: 7b — Whitespace-only delete-opcode guard (production)

### Changes

#### 1. Skip line-leading whitespace-only delete opcodes

**File**: `deadcode/visitor/fix_unused_code_visitor.py`
**Action**: modify

Root cause: for a nested `with open(...) as <name>:`, `ast.unparse` re-indents the
body to 4 spaces, so `SequenceMatcher` reports the original deeper indentation as
a spurious `"delete"` opcode. That phantom delete corrupts the `print(...)` body
line (`t("File was openned")`) and drops trailing blanks. Add a guard in the
single shared opcode loop inside `get_chars_to_remove` (`:212-216`) so a
`"delete"` opcode covering only line-leading whitespace is skipped.

Current (`fix_unused_code_visitor.py:214-216`):

```python
            if tag == "delete":
                code_part_to_remove = self.convert_1d_part_to_2d(i1, i2, original_code_line_lengths, first_line, first_col)
                code_parts_to_remove.append(code_part_to_remove)
```

New:

```python
            if tag == "delete":
                segment = original_code[i1:i2]
                if segment.strip() == "" and (i1 == 0 or original_code[i1 - 1] == "\n"):
                    continue  # ast.unparse re-indented the body; surplus indent is not a real delete
                code_part_to_remove = self.convert_1d_part_to_2d(i1, i2, original_code_line_lengths, first_line, first_col)
                code_parts_to_remove.append(code_part_to_remove)
```

`get_chars_to_remove(...)` signature and return type are unchanged; only the set
of emitted `Part`s narrows. `Part` named tuple (`data_types.py:37-49`) unchanged.
This is the single funnel for every `visit_*` using the unparse-diff mechanism
(`visit_With` `:281-289`, `visit_Import` `:339-359`, assign handling), so one
guard fixes the whole class without special-casing.

### Verification

#### Automated
- [x] `uv run pytest tests/cli_args/test_fix.py::TestFixCliOption::test_empty_lines_are_removed_properly_indented -o addopts=""`
  → passes.
- [x] Regression scope (sibling `with`/import multi-line cases share this loop):
  `uv run pytest tests/cli_args/test_fix.py tests/cli_args/test_dry.py -o addopts=""`
  → no previously-passing test regresses.

#### Manual
- [x] After the run above, the produced `foo.py` body line is
  `print("File was openned")` (not the corrupted `t("File was openned")`) and 2
  trailing blank lines are preserved — verified by
  `test_empty_lines_are_removed_properly_indented` passing (its `assertFiles`
  asserts exactly this at `test_fix.py:183-184`).
- [x] `grep -n 'segment.strip()' deadcode/visitor/fix_unused_code_visitor.py` →
  matches the new guard line.

---

## Phase 3: 7c — Preserve truncated first-line newline (production)

### Changes

#### 1. Re-attach the trailing newline on first-line truncation

**File**: `deadcode/actions/remove_file_parts_from_content.py`
**Action**: modify

Root cause: when a multi-line `Part` truncates its first line,
`line = line[:from_col]` (`:230`) strips the trailing `\n`; the buffered blank
line's `\n` is later consumed as that missing terminator, so one interior blank
line vanishes. Fix: re-attach the `\n` to the truncated first line so the
buffered blank line stays a real separator.

Current (`remove_file_parts_from_content.py:229-234`):

```python
            if from_line != to_line:
                line = line[:from_col]
                if insert_code:
                    line += insert_code
                has_block_started = not line.strip()
```

New (`:230`):

```python
            if from_line != to_line:
                line = line[:from_col] + "\n"
                if insert_code:
                    line += insert_code
                has_block_started = not line.strip()
```

Invariant preserved: `has_block_started = not line.strip()` (`:233`) stays
correct because `"\n".strip() == ""` (design decision 3, verified). Function
signature unchanged. Watch the `not updated_content_lines[-1].endswith('\n')`
branch (`:282`) per Open Risks — covered by the regression run below.

### Deviation from plan

The plan cited `remove_file_parts_from_content.py:230` as the fix location (the `from_line`
truncation in the main loop's `elif current_lineno == from_line:` branch). The actual bug
is at **line 101**, inside `remove_unused_fragments_from_a_line`: when line 3 is both the
`to_line` of Part1 AND the `from_line` of Part2, the `line[:from_col]` at line 101 strips
the `\n` from the Part2-start truncation. The plan's conceptual description is correct
("the buffered blank line's `\n` is consumed as the missing terminator"), but the stripping
happens one call-level deeper than described. Fix applied at line 101.

### Verification

#### Automated
- [x] `uv run pytest tests/fix/test_unused_imports_in_a_single_file.py::TestAssignmentExpressionRemoval::test_aliases_are_removed -o addopts=""`
  → passes.
- [x] Regression scope:
  `uv run pytest tests/fix/test_unused_imports_in_a_single_file.py -o addopts=""`
  → no previously-passing import-removal test regresses.

#### Manual
- [x] After the run above, produced `file.py` is
  `from spam import bar as bar_alias\n\nprint(bar_alias)\n` — the interior blank
  line is kept — verified by `test_aliases_are_removed` passing (its
  `assertFiles` asserts this at `test_unused_imports_in_a_single_file.py:247-252`).
- [x] `grep -n 'line\[:from_col\] + "' deadcode/actions/remove_file_parts_from_content.py`
  → matches line 101 (not 230; see deviation note above).

---

## Phase 4: Full-suite regression + coverage gate

All three fixes coexist; confirm nothing in the ~27 neighboring tests that share
the same machinery regressed, under the real coverage-enforcing command.

### Changes

None (verification only).

### Verification

#### Automated
- [x] `just test` → exits 0.

#### Manual
- [x] `just test 2>&1 | grep -E '[0-9]+ failed|[0-9]+ passed|[0-9]+ skipped'` →
  summary shows `0 failed` (i.e. no `failed` count) and `2 skipped` (the two
  pre-existing `@skip` tests at `test_fix.py:352,376` stay skipped; no new skips).
  Note: actual output is "127 passed, 18 skipped" — the plan's "2 skipped"
  under-counted pre-existing skips in the full suite; 0 failed is the key gate.
- [x] `just test 2>&1 | grep -c 'Required test coverage of 88.0% not reached'`
  → `0` (coverage stays ≥ 88; actual 90.14%).
- [ ] (Optional sanity) `just check` → exits 0 (format/lint/complexity/typecheck
  on the two edited production files plus the test edit; the new guard stays
  within McCabe ≤ 10 and line-length 120 per `pyproject.toml`).
  Note: `just check` exits 1 at `check-format` — 23 files need reformatting,
  but these are all pre-existing issues unrelated to our 3-phase changes.

---

## Testing Checkpoints

For resuming if context resets:

- **After Phase 1**: `tests/cli_args/test_dry.py` fully green. Production
  unchanged. Failures 3 → 2.
- **After Phase 2**: `test_empty_lines_are_removed_properly_indented` green;
  `with`-removal body indentation preserved. Failures 2 → 1. ~4-line guard added
  to `fix_unused_code_visitor.py`.
- **After Phase 3**: `test_aliases_are_removed` green; interior blank line
  preserved. Failures 1 → 0. One-line change in
  `deadcode/actions/remove_file_parts_from_content.py`.
- **After Phase 4**: `just test` exits 0 with 0 failed / 2 skipped, coverage
  ≥ 88. Desired end state reached.

## What we are NOT doing (from design.md)

- Not refactoring the unparse-diff pipeline, `merge_overlaping_file_parts`, or
  `fix_indent`.
- Not fixing the documented `merge_overlaping_file_parts.py:11` copy-paste bug
  (no failing test depends on it).
- Not un-skipping the two `@skip` tests (`test_fix.py:352,376`).
- Not adding features/flags/abstractions, and not touching coverage config or the
  Justfile.
