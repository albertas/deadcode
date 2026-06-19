# Structure Outline

## Approach

Scope coverage to the `deadcode/` package and make the measurement explicit
(`[tool.coverage.*]` block, `omit` the in-package test base), then close real
gaps with new behavior-describing tests — module group by module group — and
only after the package genuinely clears 95% do we raise `--cov-fail-under` to
95.0. Each phase is verifiable via a per-area `--cov-report=term-missing` run so
a failure in a later phase still leaves earlier phases independently valuable.
No product code in `deadcode/` changes; tests adapt to the code.

**Note on slicing**: a coverage task does not slice into UI/DB/API layers. The
"vertical slice" unit here is *one measurement-or-module area carried end to
end* — config wired + new tests written + coverage re-measured + suite green.
Each phase below is independently runnable and independently verifiable.

---

## Phase 1: Coverage measurement scaffolding (no gate change)

Scope coverage to the package and document it in config, **without** raising the
threshold. Establishes the clean denominator everything else is measured
against.

**Files**: `pyproject.toml`

**Key changes**:
- `[tool.pytest.ini_options] addopts`: `--cov=.` → `--cov=deadcode` (keep
  `--no-cov-on-fail`; keep `--cov-fail-under=88.0` for now).
- New `[tool.coverage.run]`: `source = ["deadcode"]`,
  `omit = ["deadcode/utils/base_test_case.py"]` (line coverage only — no
  `branch = true`).
- New `[tool.coverage.report]`: defaults (no `exclude_lines` yet).

**Verify**: `pytest -o addopts="" --cov=deadcode --cov-report=term-missing`
runs; then `just test` passes and the report TOTAL no longer includes any
`tests/` rows and shows no `base_test_case.py` row. Capture the new baseline
percentage (recompute — omitting `base_test_case` shifts the denominator) for
use as the Phase 2-5 reference; assert TOTAL ≥ 88.0 so the existing gate stays
green.

---

## Phase 2: Close `actions/` gaps (unit tests on action functions)

Add targeted unit tests for the standalone action functions on raw tuples /
`Part`s, following `tests/actions/test_*.py`.

**Files**: `tests/actions/test_remove_file_parts_from_content.py`,
`tests/actions/test_merge_overlaping_file_parts.py`,
`tests/actions/test_find_python_filenames.py`, and `Args`-driven cases in
`tests/cli_args/test_parsing.py` (for `parse_arguments.py` lines `9, 25, 222`).

**Target lines**: `remove_file_parts_from_content.py` (21: `28-34, 38-41,
47-57, 112, 219, 290-291`), `merge_overlaping_file_parts.py` (4: `14, 86-87,
114`), `find_python_filenames.py` (3: `19, 32-33`), `parse_arguments.py` (3).

**Key signatures exercised** (no changes — tests only):
- `remove_file_parts_from_content(content: FileContent, parts: list[Part]) -> FileContent`
- `merge_overlaping_file_parts(parts: list[Part]) -> list[Part]`
- `find_python_filenames(args: Args) -> list[Filename]`

**Verify**: `pytest -o addopts="" --cov=deadcode --cov-report=term-missing
tests/actions tests/cli_args/test_parsing.py` passes; the four listed modules'
"Missing" columns shrink to (ideally) empty; suite shows no new skips.

---

## Phase 3: Close `visitor/utils.py` + small visitor gaps

Add direct unit tests for the AST helper functions, which are hard to reach from
`main()` and need crafted AST inputs.

**Files**: new `tests/visitor/test_utils.py`; extend
`tests/code_item/test_code_item.py`; new/extend `tests/visitor/test_lines.py`.

**Target lines**: `visitor/utils.py` (15: `23-27, 29, 55-62, 73, 85` —
`_safe_eval`, `condition_is_always_true/false`, `get_decorator_name`),
`visitor/code_item.py` (3: `91, 129, 137`), `visitor/lines.py` (4: `64-65,
80-81`), `visitor/fix_unused_code_visitor.py` (1: `184`).

**Key signatures exercised**:
- `_safe_eval(node: ast.AST, ...) -> object` — feed literal/comparison/unsafe
  nodes via `ast.parse(src).body[0]`.
- `condition_is_always_true(node) -> bool` / `condition_is_always_false(node) -> bool`
- `get_decorator_name(node: ast.expr) -> str | None`
- `CodeItem.__eq__` / `__hash__` edge cases.

**Verify**: `pytest -o addopts="" --cov=deadcode --cov-report=term-missing
tests/visitor tests/code_item` passes; `utils.py` rises from 69% toward 100%;
`code_item.py`, `lines.py`, `fix_unused_code_visitor.py` "Missing" shrink. Tests
must use 3.8-compatible AST (no 3.9+ syntax / version-specific node assertions).

---

## Phase 4: Close `visitor/find_unused_code_visitor.py` gaps (the big one)

Largest gap (47 lines). Drive as many paths as possible from the public
`main()` surface via `BaseTestCase` virtual-FS tests (Pattern A), falling back
to direct `FindUnusedCodeVisitor` unit tests for paths unreachable from `main()`
(`_add_aliases`, format-string, `Call`, conditional / unreachable-code paths).

**Files**: new `tests/fix/test_unreachable_code.py` cases and/or
`tests/visitor/test_find_unused_code_visitor.py`; possibly extend
`tests/test_imports.py` for alias/import paths.

**Target lines**: `find_unused_code_visitor.py` (47: `204-210, 251, 265-267,
343, 347, 358, 366-368, 378, 381-397, 402, 428-430, 440, 447, 449, 459,
493-496, 503-504, 556-557, 599-607`).

**Key signatures exercised**:
- `FindUnusedCodeVisitor.visit_abstract_syntax_trees(trees, args) -> None`
- visitor dispatch methods (`visit_*`, `_define`, `_add_aliases`) via parsed
  fixtures.

**Verify**: `pytest -o addopts="" --cov=deadcode --cov-report=term-missing
tests/visitor tests/fix tests/test_imports.py` passes; module rises from 83%
toward ~100%. Any genuinely unreachable branch gets a justified
`# pragma: no cover` recorded inline + noted in the phase log (Design Decision
6) — default is a real test.

---

## Phase 5: Close `utils/` leaf + `cli.py` gaps

Mop up the small remaining misses in leaf helpers and the orchestrator.

**Files**: extend `tests/utils/test_fix_indent.py`; new
`tests/utils/test_flatten_lists.py`, `tests/utils/test_nested_scopes.py`;
`cli.py` line via `tests/test_deadcode.py` integration case.

**Target lines**: `fix_indent.py` (2: `12-13`), `flatten_lists.py` (1: `18`),
`nested_scopes.py` (1: `24`), `cli.py` (1: `35`), `print_ast.py` (1: `5` —
candidate for a justified `# pragma: no cover`, debug-only).

**Verify**: `pytest -o addopts="" --cov=deadcode --cov-report=term-missing`
shows package TOTAL ≥ 95.0%; suite green with no new skips.

---

## Phase 6: Raise the gate to 95.0

Only after Phase 5 confirms the package clears 95%. Flip the enforcement value.

**Files**: `pyproject.toml`

**Key change**:
- `[tool.pytest.ini_options] addopts`: `--cov-fail-under=88.0` →
  `--cov-fail-under=95.0`.

**Verify**: `just test` and `make check` pass; terminal report prints
`Required test coverage of 95.0% reached` and TOTAL ≥ 95.0%. Confirm the suite
still reports the original 18 skips (or fewer) — `pytest -o addopts="" -rs`
shows no *newly added* skip used to dodge a gap.

---

## Testing Checkpoints

- **After Phase 1**: coverage measures `deadcode/` only; no `tests/` or
  `base_test_case.py` rows; new baseline % recorded; 88.0 gate still green.
- **After Phase 2**: `actions/` modules at/near 100%; suite green.
- **After Phase 3**: `visitor/utils.py` ≫ 69%; small visitor/code_item/lines
  gaps closed; all AST tests 3.8-compatible.
- **After Phase 4**: `find_unused_code_visitor.py` ≫ 83%; any pragma uses
  documented; suite green.
- **After Phase 5**: package TOTAL ≥ 95.0% with the gate still at 88.0
  (so the green/red transition is purely the Phase 6 flip).
- **After Phase 6**: `make check` enforces 95.0 on Python 3.8; CI green; no
  new skips. Task complete.
