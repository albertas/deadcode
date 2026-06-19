# Structure Outline

## Approach

Three independent, test-first correctness fixes (design Decisions 2–5). Each
slice writes a failing test in the existing per-area test file, then makes the
single defective expression correct. No architectural change; the flat
`used_names` scope limitation stays out of scope. After every slice, `just test`
and `just check` must pass. Slices are ordered by confidence: the two confirmed
defects first (#1, #2), the provisional `__all__` fix last (#3), so that if #3
is dropped (Decision 5) the first two remain independently valuable.

Each "vertical slice" here crosses the relevant layers for this CLI tool:
the implementation function (service/logic), its unit/behavior test, and the
end-to-end `main([...])` report/fix output that the test asserts on.

---

## Phase 1: Fix `does_include` self-comparison in part merge

Fix the `line_end_b == line_end_b` (always-`True`) typo so a removal part is
treated as contained only when the bigger part genuinely contains it on **both**
line and column axes. Restores correct/complete multi-part edits within one file.

**Files**: `deadcode/actions/merge_overlaping_file_parts.py`,
`deadcode/tests/actions/test_merge_overlaping_file_parts.py`

**Key changes**:
- `does_include(bigger_part: Part, smaller_part: Part) -> bool` — change line 10
  clause `(line_end_b == line_end_b)` → `(line_end_b == line_end_s)`. Signature
  unchanged.
- New unit test constructing `Part(...)` tuples directly: a `smaller_part` whose
  `col_end_b <= col_end_s` but whose `line_end` differs from the bigger part —
  asserts it is **not** dropped from the merged list. Complete the existing
  TODO/commented same-line assertion at `test_merge_overlaping_file_parts.py:54-67`.

**Verify**: `just test` passes (new test fails before the one-token edit, passes
after — confirm by running `just test` on the test file before applying the fix
and observing the assertion failure, then again after); `just check` passes
(format, lint, complexity ≤10, mypy). No other existing test changes behavior;
if one breaks, decide per Open Risks whether it pinned the bug.

---

## Phase 2: Align noqa matching with flake8 (whitespace + lowercase codes)

Make `# noqa` detection match flake8: accept `#noqa` / `#  noqa` (any
whitespace) and lowercase codes (`# noqa: dc01`), mapping them to DC codes so a
valid suppression is honored instead of producing a false negative.

**Files**: `deadcode/visitor/noqa.py`,
`deadcode/tests/noqa/test_noqa_comments.py`

**Key changes**:
- `NOQA_REGEXP` (noqa.py:4-14) — change literal `# noqa` to `#\s*noqa`
  (flake8's pattern). Keep `re.IGNORECASE`. Code subpattern stays `[A-Z]+[0-9]+`
  (matches lowercase under IGNORECASE).
- `parse_noqa(code: str) -> dict[str, set[int]]` (noqa.py:54-62) — normalize the
  captured code with `.upper()` before the `NOQA_CODE_MAP.get(...)` lookup at
  noqa.py:60, so `dc01`/`f401` resolve. Signature unchanged.
- New behavior tests (subclass `BaseTestCase`, set `self.files`, call
  `main([...])`): `#noqa`, `#  noqa`, and `# noqa: dc07` each suppress the
  expected DC code; plus a guard test that a benign `# type: ignore` line is
  **not** suppressed (report still lists the name). Do **not** un-skip the
  DC05/06/08/09/13 `@skip`ped tests (Decision 7).

**Verify**: `just test` passes (each new test fails before the regex/`.upper()`
edits, passes after); `just check` passes. Manually confirm via:
`just test` filtered to `test_noqa_comments` shows the new cases green and the
previously-passing per-code/`all` cases still green.

---

## Phase 3: Recognize `__all__` AugAssign/AnnAssign (provisional — Decision 5)

Mark string elements of `__all__ += [...]` and `__all__: list = [...]` as used so
names exported only that way are not reported unused (false positive). Include
**only if** step-4 exploration confirms (a) it is a real false positive today and
(b) the fix is local to `_assigns_special_variable__all__` + the `visit_Assign`
dispatch. If it needs scope handling, drop it and record under Open Risks.

**Files**: `deadcode/visitor/ignore.py`,
`deadcode/visitor/find_unused_code_visitor.py`,
`deadcode/tests/test_deadcode.py` (or the existing `__all__` test location)

**Key changes**:
- `_assigns_special_variable__all__(node: ast.Assign | ast.AugAssign | ast.AnnAssign) -> bool`
  (ignore.py:66-70) — broaden the type guard/assert to also accept `AugAssign`
  (single `target`) and `AnnAssign` (single `target`, optional `value`); return
  `True` when the target name is `__all__` and `value` is a `List`/`Tuple`.
- Add `visit_AugAssign` / `visit_AnnAssign` (or extend the `visit_Assign`
  dispatch at find_unused_code_visitor.py:503-508) to iterate
  `node.value.elts`, adding each string `ast.Constant` via `add_used_name`.
  Guard `AnnAssign` for `value is None`.
- New detection test: a module with `def used_via_all(): ...` exported via
  `__all__ += ['used_via_all']` (and a second test via `__all__: list[str] =
  [...]`) asserts the name is **absent** from the unused report.

**Verify**: `just test` passes (new test fails before the broadened guard,
passes after); `just check` passes. If the fix turns out to require touching
scope handling, this phase is **dropped** — record in `design.md` Open Risks and
leave Phases 1–2 as the delivered scope.

---

## Testing Checkpoints

After **Phase 1**: `just test` + `just check` green. `does_include` returns
`True` only for genuine line+column containment; merge no longer drops valid
removal parts that share a file. The completed same-line merge test asserts this.

After **Phase 2**: `just test` + `just check` green. `parse_noqa` recognizes
`#noqa`, `#  noqa`, and lowercase/legacy codes; `# type: ignore` is unaffected.
flake8-equivalent suppression behavior verified by new `test_noqa_comments` cases.

After **Phase 3** (if in scope): `just test` + `just check` green. `__all__`
augmented/annotated assignments mark their string elements used; names exported
that way are no longer false-positives. If dropped, repo state equals end of
Phase 2 and the drop is documented in `design.md` Open Risks.

Resume rule: each phase is self-contained and test-first. To resume after a
context reset, run `just test`; the first failing or missing assertion among the
three areas (merge → noqa → `__all__`) identifies the next phase.
