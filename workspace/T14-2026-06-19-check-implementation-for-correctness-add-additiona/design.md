# Design Discussion

## Current State

`deadcode` detects unused names in one AST pass and fixes them in a second
pass. The research (`research.md`) maps the whole pipeline; this design narrows
to the **concrete, bounded correctness defects** with unambiguous correct
behavior, leaving documented architectural limitations out of scope.

Confirmed defects (read directly, not just from research):

1. **`does_include` self-comparison bug** —
   `merge_overlaping_file_parts.py:10`:
   `ends_faster = (line_end_b < line_end_s) or ((line_end_b == line_end_b) and (col_end_b <= col_end_s))`.
   The second clause compares `line_end_b == line_end_b` (always `True`), so
   any part whose `col_end_b <= col_end_s` is treated as "contained" regardless
   of line numbers. This drops removal parts that are *not* actually contained,
   producing **incorrect/incomplete edits** when multiple parts share a file.

2. **noqa diverges from flake8 despite the "same regex" comment** —
   `noqa.py:4-14`. The pattern requires `# noqa` with exactly one space, so
   `#noqa` / `#  noqa` are missed. flake8's real pattern is `#\s*noqa`.
   Separately, the regex is `IGNORECASE` (`noqa.py:13`), so `# noqa: dc01` is
   captured as `dc01`; `NOQA_CODE_MAP` (`noqa.py:16-46`) only has uppercase
   keys, so the lookup misses and the code never matches the DC error code.
   Both are **false negatives** (a valid suppression is ignored → name still
   reported/removed).

3. **`__all__` only handled for plain `ast.Assign`** —
   `_assigns_special_variable__all__` (`ignore.py:66-70`) and `visit_Assign`
   (`find_unused_code_visitor.py:503-508`). `__all__ += [...]` / `__all__: list
   = [...]` (AugAssign/AnnAssign) are not recognized, so names exported only
   that way are reported unused (**false positive**). *Candidate — confirm
   scope in step 4 below.*

The flat `used_names: set[str]` membership test (`ignore.py:39-42`,
`code_item.py:130-139`) is the documented root of cross-scope false negatives
(`nested_scopes.py:41-45,65`). This is architectural and **explicitly out of
scope** — see "What We're NOT Doing".

## Desired End State

- `does_include` returns `True` only when `bigger_part` genuinely contains
  `smaller_part` on both line and column axes. A regression test exercises the
  previously-mishandled case (different end lines, `col_end_b <= col_end_s`).
- noqa recognizes `#noqa`, `#  noqa`, and lowercase codes (`# noqa: dc01`)
  exactly as flake8 does, mapping them to DC codes.
- (If confirmed in scope) `__all__` augmented/annotated assignments mark their
  string elements as used.
- All new tests pass; the **existing suite stays green** (`just test`), and
  `just check` (format, lint, complexity ≤10, mypy) passes.

Verification: `just test` and `just check` both pass; each fix has a test that
fails before the change and passes after.

## Patterns to Follow

- **Test structure**: subclass `BaseTestCase`, set `self.files` (virtual
  filename→source), call `main([...])`, assert on the returned report string
  and/or `assertFiles({...})` (`utils/base_test_case.py:11-96`,
  `tests/test_deadcode.py:13-71`).
- **Detection assertions**: `assertEqual(unused_names,
  'file:line:col: DCxx ...')` (`test_deadcode.py:22`, `test_imports.py:67`).
- **Fix assertions**: `assertFiles({'foo.py': '...'} , removed=[...])`
  (`base_test_case.py:59-85`).
- **noqa tests**: per-code and `all` forms live in
  `noqa/test_noqa_comments.py`; many real cases are present (the `@skip` ones
  are DC05/06/08/09/13, which depend on detection gaps — do not un-skip those).
- **Pure-unit tests for merge**: `actions/test_merge_overlaping_file_parts.py`
  constructs `Part(...)` tuples directly and asserts on the merged list — use
  this style for the `does_include` fix (it already has a TODO/commented
  same-line assertion at `:54-67` to complete).
- **Tooling**: run `just test` / `just check`, never raw `pytest`/`ruff`/`mypy`
  (Justfile recipes; CLAUDE.md §5).
- **Surgical edits** (CLAUDE.md §3): touch only the defective expressions; do
  not reformat neighboring code or rename the Lithuanian comments.

**Patterns to NOT follow / not extend**: the name-only `CodeItem` equality and
flat scope. Do not build new logic on top of `used_names` global membership;
do not attempt scope-aware disambiguation here.

## Design Decisions

1. **Scope = bounded correctness bugs, not the architecture** — chosen because
   the task asks to "find places where it produces wrong results" and pin them
   with tests, while the flat-scope limitation is large, documented, and
   covered by many intentionally-`@skip`ped tests. Fixing it is a separate
   effort. Assumption: reviewers want correct, low-risk fixes over a rewrite.

2. **Fix `does_include` to `line_end_b == line_end_s`** — the only defensible
   reading of "bigger contains smaller". This is a one-token fix with a clear
   correct value. Add a unit test that fails on the typo.

3. **Align noqa regex with flake8: `#\s*noqa` + uppercase codes** — chosen over
   inventing a new format, because the comment already states intent to match
   flake8 (`noqa.py:5-6`). Normalize captured codes with `.upper()` before
   `NOQA_CODE_MAP` lookup (`noqa.py:60`). Keep `IGNORECASE`.

4. **Drive every fix from a failing test first** (CLAUDE.md §4) — write the
   test, watch it fail, then change the implementation. New tests go in the
   existing per-area files, not new directories.

5. **`__all__` AugAssign/AnnAssign support is provisional** — included only if
   step-4 exploration confirms (a) it is genuinely a false positive today and
   (b) the fix is local to `_assigns_special_variable__all__` + the
   `visit_Assign` dispatch. If it requires touching scope handling, drop it and
   record under Open Risks. Assumption: most projects use plain `__all__ =
   [...]`, so this is lower priority than #2/#3.

6. **Do not change CLI/arg surface** — the parsed-but-unused `ignore_*` options
   (research Q4/Q5) are a feature gap, not a correctness bug for existing
   behavior; wiring them risks behavior changes. Excluded.

7. **Leave `@skip`ped tests skipped unless a fix legitimately enables them** —
   un-skipping a test that depends on the architectural limitation would force
   the rewrite we are deferring. Only un-skip a test if the corresponding
   bounded fix makes it pass cleanly.

## What We're NOT Doing

- Not reworking `used_names`/`CodeItem` equality or introducing scope-aware
  usage tracking (`code_item.py:130-139`, `nested_scopes.py:41-45,65`).
- Not implementing DC05 (attributes), DC06, DC08 (properties), DC09
  (unreachable) detection or their `@skip`ped noqa/fix tests.
- Not wiring the parsed-but-unused `ignore_*` / `ignore_decorators` options
  (`parse_arguments.py`, research Q4).
- Not adding upward `pyproject.toml` traversal or new config keys.
- Not refactoring the two-pass detect/fix architecture or `ast.unparse` +
  `SequenceMatcher` diffing.
- Not condensing or reformatting existing files (CLAUDE.md §3, §7).

## Open Risks

- **Existing tests may encode current-buggy behavior.** The `does_include`
  change could alter merge output for an existing test. Run `just test` after
  each change; if a test breaks, decide whether it pinned the bug (update it
  with justification) or a real regression (revert/adjust).
- **noqa regex widening could over-match.** `#\s*noqa` inside string literals
  or URLs could falsely suppress. flake8 has the same exposure, so matching its
  behavior is acceptable; add a test for a benign `# type: ignore` line staying
  unaffected.
- **`__all__` AugAssign scope** — may turn out to need more than a local edit;
  if so it is deferred (Decision 5).
- **Merge ordering** beyond `does_include` (the `sort_parts`/`does_overlap`
  TODOs, `merge_overlaping_file_parts.py:17,28`) may hide further bugs; only
  the confirmed self-comparison is in scope unless a new failing test surfaces
  during implementation.
