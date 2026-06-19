# Structure Outline

## Approach

Three failing tests in the code-removal / diff-rendering pipeline, each with a
*different* root cause and a *different* correct fix direction (per `design.md`).
Each failure is its own vertical slice: it touches exactly one production-or-test
seam and is independently verifiable by running its single test file. Order is by
ascending blast radius — fix the test-only change first (no production risk), then
the two production edits, then a full-suite regression gate. If a later phase
fails, earlier phases remain independently valuable (each leaves one more test
green than before).

Shared verification harness for every phase (coverage addopts disabled so a
single file can run in isolation):

```
uv run pytest <file> -o addopts=""
```

The final gate uses the real command: `just test`.

---

## Phase 1: 7a — Update stale `--dry` diff expectation (test-only)

Fix `test_coloring_of_a_diff` to expect the clean `with open("tmp.txt", "r"):`
the production code already emits, replacing the stale ` as :` leftover. **No
production code touched.** Establishes a green baseline before any risky edit.

**Files**: `tests/cli_args/test_dry.py`

**Key changes**:
- `test_dry.py:273` — change asserted `+` diff line from
  `+with open("tmp.txt", "r") as :` to `+with open("tmp.txt", "r"):`
  (remove the 4 chars ` as `). Apply the identical edit to any sibling
  colored-line assertion in the same block (`:240-304`) that repeats the
  `as :` form (e.g. the green-wrapped `\033[32m...\033[0m` variant).
- No type/interface changes.

**Verify**:
- `uv run pytest tests/cli_args/test_dry.py -o addopts=""` → 0 failed (the
  `test_coloring_of_a_diff` case passes; `assertFiles` half already passed).
- Manual/scripted: `grep -n 'as :' tests/cli_args/test_dry.py` returns no
  matches inside the `test_coloring_of_a_diff` block.

---

## Phase 2: 7b — Whitespace-only delete-opcode guard (production)

Stop nested `with ... as <name>` removal from eating body indentation. Add a
guard in the single shared opcode loop so a `"delete"` opcode that covers only
line-leading whitespace is skipped, preserving the `print(...)` body line and
trailing blanks.

**Files**: `deadcode/visitor/fix_unused_code_visitor.py`

**Key changes** (inside `get_chars_to_remove`, `:189-225`, guard at `:212-216`):
- For each `"delete"` opcode `(i1, i2)` over `original_code`, skip emitting a
  `Part` when:
  ```python
  segment = original_code[i1:i2]
  if segment.strip() == "" and (i1 == 0 or original_code[i1 - 1] == "\n"):
      continue  # ast.unparse re-indented the body; surplus indent is not a real delete
  ```
- `get_chars_to_remove(...) -> list[Part]` — signature unchanged; only the set of
  emitted `Part`s narrows. `Part` named tuple unchanged
  (`data_types.py:37-49`).

**Verify**:
- `uv run pytest tests/cli_args/test_fix.py::TestFixCliOption::test_empty_lines_are_removed_properly_indented -o addopts=""`
  → passes; produced body line is `print("File was openned")` (not the corrupted
  `t("File was openned")`) and 2 trailing blank lines are preserved.
- Regression scope (other `with`/import multi-line cases share this loop):
  `uv run pytest tests/cli_args/test_fix.py tests/cli_args/test_dry.py -o addopts=""`
  → no previously-passing test regresses.

---

## Phase 3: 7c — Preserve truncated first-line newline (production)

Stop one interior blank line from vanishing when a multi-line `Part` truncates
its first line. Keep/re-attach the `\n` to the truncated first line so the
buffered blank line remains a real separator.

**Files**: `deadcode/utils/remove_file_parts_from_content.py`

**Key changes** (in `remove_file_parts_from_content`, `:127-396`):
- At the first-line truncation `line = line[:from_col]` (`:230`), re-attach the
  trailing newline before the line is appended (`:236-239`):
  ```python
  line = line[:from_col] + "\n"   # was: line = line[:from_col]
  ```
  so the later blank-line bookkeeping does not consume the buffered blank line's
  `\n` as the missing terminator.
- Invariant to preserve: `has_block_started = not line.strip()` (`:233`) stays
  correct because `"\n".strip() == ""`.
- Edge cases to check against existing tests (Open Risks in design): the
  `not updated_content_lines[-1].endswith('\n')` branch (`:282`), column-0
  truncation, and fully-emptied lines.
- Function signature unchanged.

**Verify**:
- `uv run pytest tests/fix/test_unused_imports_in_a_single_file.py::TestAssignmentExpressionRemoval::test_aliases_are_removed -o addopts=""`
  → passes; produced content is
  `from spam import bar as bar_alias\n\nprint(bar_alias)\n` (interior blank line
  kept).
- Regression scope:
  `uv run pytest tests/fix/test_unused_imports_in_a_single_file.py -o addopts=""`
  → no previously-passing import-removal test regresses.

---

## Phase 4: Full-suite regression + coverage gate

Confirm all three fixes coexist and nothing in the ~27 neighboring tests that
share the same machinery regressed, under the real coverage-enforcing command.

**Files**: none (verification only).

**Verify**:
- `just test` → exits 0; summary shows **0 failed, 2 skipped** (the two
  pre-existing `@skip` tests at `test_fix.py:352,376` stay skipped — no new
  skips).
- Coverage stays ≥ 88 (`--cov-fail-under=88.0`, `pyproject.toml:211`); `just
  test` not aborting on the coverage gate confirms this.
- Scripted assertion: `just test` output contains `0 failed` and `2 skipped`
  and does not contain `Required test coverage of 88.0% not reached`.

---

## Testing Checkpoints

After each phase, the following should be true (for resuming if context resets):

- **After Phase 1**: `tests/cli_args/test_dry.py` fully green. Production
  unchanged. Failure count down from 3 → 2.
- **After Phase 2**: `test_empty_lines_are_removed_properly_indented` green;
  `with`-removal body indentation preserved. Failure count 2 → 1. One ~3-4 line
  guard added to `fix_unused_code_visitor.py`.
- **After Phase 3**: `test_aliases_are_removed` green; interior blank line
  preserved. Failure count 1 → 0. One-line change in
  `remove_file_parts_from_content.py`.
- **After Phase 4**: `just test` exits 0 with 0 failed / 2 skipped, coverage
  ≥ 88. Desired end state reached.

**Note on slicing**: these slices are independent *fixes* rather than feature
layers, but each still crosses the relevant seams (test assertion ↔ production
removal/diff code) and is independently testable via its own test file — which is
the vertical-slice property that matters here. No phase depends on another's
production edit; ordering is purely risk-ascending.
