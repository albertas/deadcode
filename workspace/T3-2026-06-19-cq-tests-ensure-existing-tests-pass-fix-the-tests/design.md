# Design Discussion

## Current State

`just test` runs `uv run pytest -n <cores-1>` (`Justfile`) with coverage addopts
that require `pytest-cov` (`pyproject.toml:210-211`). The suite is ~145 tests; **3
fail, 27 pass, 2 skip** in the affected area. All three failures live in the
code-removal / diff-rendering pipeline and each has a *different* root cause and a
*different* correct resolution direction:

- **7a — `tests/cli_args/test_dry.py::test_coloring_of_a_diff`** (`:240-304`):
  The test asserts the diff `+` line as `with open("tmp.txt", "r") as :`
  (`test_dry.py:273`) — a leftover bare `as`. The production code now emits the
  *clean* `with open("tmp.txt", "r"):`. **The code is correct; the test asserts a
  stale buggy form.** Mismatch is exactly the 4 chars ` as `.

- **7b — `tests/cli_args/test_fix.py::test_empty_lines_are_removed_properly_indented`**
  (`:126-191`): The test asserts the clean nested rewrite
  `with open("example.txt"):` with the body `print("File was openned")` and 2
  trailing blank lines preserved (`:183-184`, comment `:168` "GOAL: make this
  method work with multiline code diffs"). Production produces a **corrupted** body
  line `t("File was openned")` (leading chars eaten) and drops trailing blanks.
  **The test asserts the intended result; the code is buggy.**

- **7c — `tests/fix/test_unused_imports_in_a_single_file.py::test_aliases_are_removed`**
  (`:211-253`): The test expects the blank line kept between the surviving import
  and `print(bar_alias)` (`:247-252`). Production drops that blank line.
  **The test asserts the intended result; the code is buggy.**

All three share one mechanism: mutate the AST node → `ast.unparse(node)` →
`difflib.SequenceMatcher` diff → emit a `Part` per `"delete"` opcode
(`fix_unused_code_visitor.py:227-236`, `189-225`, `165-187`). Its fragility shows
whenever `ast.unparse` reformats (re-indentation, paren collapse) differently from
the original source. Tests run entirely on mocked `open`/`os.remove` (no disk),
with content normalized by `fix_indent` on both read and assert
(`base_test_case.py:23-93`).

## Desired End State

`just test` passes with **0 failed, all previously-passing tests still green, 2
skipped** (the two pre-existing `@skip` tests at `test_fix.py:352,376` stay
skipped). Verification: `just test` exits 0 and coverage stays ≥ 88
(`pyproject.toml:211`). No new skips, no weakened assertions beyond the single
stale expectation in 7a.

Concretely:
1. 7a: `test_dry.py:273` expectation updated to the clean `with open("tmp.txt", "r"):`.
2. 7b: nested `with ... as <name>` removal no longer eats body indentation;
   the body line and trailing blanks survive.
3. 7c: removing one alias from a multi-line `from ... import (...)` preserves the
   interior blank line that followed the import.

## Patterns to Follow

- **Whitespace-only delete-opcode guard** belongs inside the existing opcode loop
  in `get_chars_to_remove` (`fix_unused_code_visitor.py:212-216`). It is the single
  funnel for every `visit_*` that uses the unparse-diff mechanism (`visit_With`
  `:281-289`, `visit_Import` `:339-359`, assign handling), so one guard there fixes
  the whole class of "ast.unparse re-indented, so the original deeper indentation
  looks deleted" bugs without special-casing.
- **`Part` is a named tuple** `(line_start, line_end, col_start, col_end,
  insert_code, insert_code_if_character_is_not_removed)` (`data_types.py:37-49`);
  emit `Part` exactly as `convert_1d_part_to_2d` does (`:186`).
- **Test harness conventions** (`base_test_case.py`): class-attr `files`,
  `assertFiles`/`assertUpdatedFiles`, `fix_indent` on both sides. Match these; do
  not add real filesystem I/O.
- **Degrade-at-boundary / raise-on-invariant** per `CLAUDE.md` and Code Best
  Practices — keep `ValueError` in `convert_1d_part_to_2d:183`.

**Patterns to NOT follow / NOT trust:**
- Do **not** treat the `Observed bug` notes in `docs/fix-and-output.md:37` or the
  `merge_overlaping_file_parts.py:11` copy-paste bug (`line_end_b == line_end_b`)
  as spec — they describe defects, not intended behavior. Leave the merge bug alone
  unless a failing test forces it (none of the three do).
- Do **not** rely on `fix_indent` to paper over blank-line differences. It strips
  only *leading* blank lines (`fix_indent.py:41-42`); interior blanks (7c) are
  compared exactly, so the bug is real, not a harness artifact.

## Design Decisions

1. **7a → fix the test, not the code.** The clean `with open("tmp.txt", "r"):`
   output is the obviously-intended result; the ` as :` form is a historical bug
   the code already outgrew. Update only the `+` expectation at `test_dry.py:273`
   (and any sibling colored-line assertion in the same block). Assumption: the
   stale expectation, not a regression, is what diverged. Touch nothing in
   production for 7a.

2. **7b → fix production via the whitespace-only delete guard (Option b).** In
   `get_chars_to_remove` (`fix_unused_code_visitor.py:214-216`), before converting a
   `"delete"` opcode to a `Part`, skip it when `original_code[i1:i2]` is all
   whitespace **and** it is line-leading (`i1 == 0 or original_code[i1-1] == '\n'`).
   Root cause: `ast.unparse` re-indents the `with` body to 4 spaces, so
   `SequenceMatcher` reports the surplus original indentation as a spurious delete
   that later corrupts the body line. Chosen over (a) re-indenting unparse output
   (fragile for nested compound bodies) and (c) special-casing `visit_With`
   (diverges from the shared mechanism). The guard is ~3-4 lines, local, and there
   is no legitimate operation in this codebase that deletes line-leading whitespace.

3. **7c → fix production by preserving the first-line newline in
   `remove_file_parts_from_content`.** When a multi-line `Part` truncates its first
   line, `line = line[:from_col]` (`remove_file_parts_from_content.py:230`) strips
   the trailing `\n`; the buffered blank line's `\n` is later consumed as that
   missing terminator, so one blank line vanishes. Fix: keep/re-attach the `\n` to
   the truncated first line before it is appended (`:236-239`) so the buffered blank
   line stays a real separator. Assumption verified: `has_block_started =
   not line.strip()` (`:233`) is unaffected because `"\n".strip() == ""`.

4. **Honor test intent over weakening tests for 7b/7c.** The task says fix
   whichever side reflects intended behavior. The GOAL/TODO comments
   (`test_fix.py:168`, `fix_indent.py:15`, `test_unused_imports...:242-243`) and the
   clean assertions express intent → fix the code. We do **not** rewrite 7b/7c
   expectations to match current buggy output.

5. **Verify-then-edit ordering.** Reproduce all 3 failures first
   (`uv run pytest <three files> -o addopts=""`), apply the smallest fix per
   failure, re-run the trio, then run the full `just test` to catch regressions in
   the 27 neighbors that exercise the same machinery.

## What We're NOT Doing

- Not refactoring the unparse-diff pipeline, `merge_overlaping_file_parts`, or
  `fix_indent`'s leading-blank behavior.
- Not fixing the documented `merge_overlaping_file_parts.py:11` copy-paste bug
  (no failing test depends on it).
- Not un-skipping the two `@skip` tests (`test_fix.py:352,376`).
- Not adding new features, flags, abstractions, or error handling beyond the three
  surgical fixes.
- Not touching coverage config or the Justfile.

## Open Risks

- **Blast radius of the 7b/7c production edits.** Both live in fragile, heavily
  state-driven code (`remove_file_parts_from_content.py` blank-line bookkeeping;
  the shared opcode loop). The whitespace guard (7b) and the newline-preserve (7c)
  could shift output in the ~27 neighboring tests (e.g. other multi-line import or
  `with` removal cases). Mitigation: full `just test` after each change; if a
  neighbor breaks, prefer narrowing the guard's condition over broadening it.
- **7c interaction at `:280-285`.** Re-attaching the first-line `\n` changes the
  `not updated_content_lines[-1].endswith('\n')` branch (`:282`); a few edge cases
  (column-0 truncation, fully-emptied lines) need checking against existing tests.
- **7b opcode alignment is heuristic.** `SequenceMatcher` may split the surplus
  indentation differently across versions; the guard keys on "line-leading
  whitespace-only," which is robust to where the split lands, but confirm with the
  captured-stdout cases in `test_fix.py`/`test_dry.py`.
- **Coverage floor.** Removing buggy branches must not drop coverage below 88
  (`pyproject.toml:211`); unlikely but worth a final check.
