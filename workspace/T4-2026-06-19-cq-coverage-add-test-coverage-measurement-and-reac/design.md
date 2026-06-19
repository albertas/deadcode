# Design Discussion

## Current State

Coverage is already wired, but loosely:

- **Config**: the only pytest/coverage setting is
  `addopts = "--cov=. --no-cov-on-fail --cov-fail-under=88.0"` in
  `pyproject.toml:[tool.pytest.ini_options]` (last line). There is **no
  `[tool.coverage.*]` section at all** — no `source`, `omit`, `exclude_lines`,
  or `branch` (research Q1).
- **`--cov=.` measures the whole repo** (both `deadcode/` and `tests/`), so the
  reported TOTAL (90.14%) is diluted by uncovered *test* lines from `@skip`ed
  test modules. The package-only figure is **~90.8% (1190 stmts, 110 missing)**
  measured via `pytest -o addopts="" --cov=deadcode --cov-report=term-missing`
  (research Q2). Suite today: **127 passed, 18 skipped**.
- **Runners**: `Justfile test` → `uv run pytest -n "$(nproc...)"` and
  `Makefile test` → `.venv/bin/pytest -vv`; neither adds coverage flags —
  coverage comes solely from `addopts` (research Q1). CI
  (`.github/workflows/check-deadcode-on-python38.yml`) runs `make check` on
  **Python 3.8**, enforcing only the 88.0 gate.
- **Largest gaps** (research Q2): `visitor/find_unused_code_visitor.py`
  (47 missing / 83%), `visitor/utils.py` (15 / 69% — `_safe_eval`,
  `condition_is_always_*`, `get_decorator_name`),
  `actions/remove_file_parts_from_content.py` (21 / 87%). Smaller gaps in
  `find_python_filenames.py`, `merge_overlaping_file_parts.py`,
  `parse_arguments.py`, `cli.py`, `fix_indent.py`, `flatten_lists.py`,
  `nested_scopes.py`, `print_ast.py`, `code_item.py`, `lines.py`,
  `fix_unused_code_visitor.py`.
- A meaningful share of missing lines map to **18 skipped tests** and **empty
  stub test files** in `tests/cli_args/` (research Q4, cross-cutting notes).

## Desired End State

1. Coverage measures **the package only** (`deadcode/`), reported clean and
   un-diluted by test files.
2. `--cov-fail-under` is raised to **95.0**, and the package genuinely reaches
   **≥ 95% line coverage** with the suite green.
3. New, behavior-describing tests close the real gaps; `just test` /
   `make test` and CI all pass on Python 3.8.

**Verification**: `just test` (and `make check`) pass; the terminal coverage
report shows TOTAL ≥ 95% with `Required test coverage of 95.0% reached`; no
test is newly skipped to dodge a gap.

## Patterns to Follow

- **Shared harness `BaseTestCase`** (`deadcode/utils/base_test_case.py`): the
  sole test base. Set `self.files = {name: source}`, call
  `main([...])`, assert on the returned string, then `assertFiles({...},
  removed=[...])` (research Q5). It patches `find_python_filenames`, `open` in
  the three IO modules, and `os.remove`.
- **Pattern A** — virtual-FS fix test: `tests/cli_args/test_fix.py:8-33`.
- **Pattern B** — deletion via `os.remove` mock: `tests/fix/test_empty_files.py:10-22`.
- **Pattern C** — multi-line expected output wrapped in `fix_indent("""...""")`,
  args via `'foo.py --no-color --fix --dry'.split()`: `tests/cli_args/test_dry.py:7-30`.
- **Integration over real fixtures**: `tests/test_deadcode.py`
  `DeadCodeIntegrationTests` runs `main()` against real `tests/files/` paths —
  use this style for end-to-end CLI/output paths.
- **Unit tests of action functions** on raw tuples/`Part`s:
  `tests/actions/test_*.py` (research Q4) — use for
  `remove_file_parts_from_content` / `merge_overlaping_file_parts` gaps.
- **Conventions** (research Q4): files `test_<topic>.py`, classes
  `TestCamelCase`/`*Tests`, methods `test_*`, plain `assert`/`assertEqual`.
  Tests must stay **Python 3.8-compatible** (CI runtime).

**Patterns NOT to follow**: do not add new `@skip`/empty-stub test files like
the existing `cli_args/test_count.py` etc. — those are the anti-pattern this
task partly exists to correct. Fill stubs with real assertions or leave them
untouched; never add a skip to hide an uncovered line.

## Design Decisions

1. **Scope coverage to the package** — change `--cov=.` → `--cov=deadcode` in
   `addopts`. Test files should not count toward (or dilute) package coverage;
   this makes the 95% gate meaningful (research Q2 shows the dilution).
2. **Add an explicit `[tool.coverage.run]` / `[tool.coverage.report]` block** —
   set `source = ["deadcode"]` and keep line (not branch) coverage. Makes the
   measurement self-documenting instead of implicit in `addopts` (research Q1
   found none exists).
3. **Omit `deadcode/utils/base_test_case.py` from coverage** via
   `[tool.coverage.run] omit`. It is test infrastructure that lives in the
   package only for packaging reasons and is already doubly exempt from
   deadcode's own analysis (`ignore_names_in_files`, research Q6). Omitting it
   removes the `assertUpdatedFiles` 87-90 gap legitimately rather than testing a
   test helper.
4. **Raise the gate to 95.0** — `--cov-fail-under=95.0`. This is the task's
   target; bump only after the package actually clears it to avoid a red CI.
5. **Close gaps by writing new targeted tests, not by un-skipping** — the 18
   skips largely cover *unimplemented / aspirational* behavior (e.g.
   `test_scope.py`, `test_accurate_usage_detection.py` are entirely `@skip`).
   Changing product behavior is out of scope; prefer fresh tests that exercise
   currently-reachable code paths (research cross-cutting notes).
6. **Prefer tests over `# pragma: no cover`** — the task explicitly asks to
   "write whatever additional tests are needed." Reserve a pragma only for
   genuinely untestable debug-only lines (e.g. `utils/print_ast.py:5`) and
   record any such use here. Default is a real test.
7. **Leave `Justfile`/`Makefile` runner recipes unchanged** — they already
   inherit coverage from `addopts`; only `pyproject.toml` changes. pytest-cov
   composes with `-n` (xdist) automatically, so parallel runs keep working.
8. **No coverage upload/badge/CI restructuring** — out of scope; the existing
   `make check` gate is the enforcement point.

## What We're NOT Doing

- Not enabling **branch coverage** (`branch = true`) — line coverage only, as
  today (research Q1, Q6).
- Not **un-skipping** the 18 skipped tests or implementing the features they
  describe.
- Not **refactoring or "improving" source** in `deadcode/` to make it more
  testable; tests adapt to the code, not vice versa.
- Not adding CI coverage upload, badges, or a separate coverage job.
- Not deleting the existing empty stub test files (pre-existing; out of the
  surgical-change boundary unless filling them is the cheapest way to a gap).
- Not changing `[tool.deadcode]` analysis exclusions.

## Open Risks

- **Reaching exactly ≥95% may require many small tests** across `visitor/`
  (47 + 15 missing lines). Some uncovered lines in
  `find_unused_code_visitor.py` (format-string / Call / unreachable-code /
  `_add_aliases` paths) may be hard to trigger from the public `main()` surface
  and might need direct visitor-level unit tests (`CodeItem`,
  `FindUnusedCodeVisitor`).
- **`visitor/utils.py` `_safe_eval` / `condition_is_always_*`** paths may
  require crafted AST inputs; a few branches could prove genuinely unreachable —
  if so, a justified `# pragma: no cover` (Decision 6) is the fallback.
- **Python 3.8 compatibility**: locally we may run a newer interpreter; AST
  shapes differ across versions. New tests must avoid 3.9+ syntax and any
  version-specific AST node assumptions, or CI will fail.
- **Omitting `base_test_case.py`** shifts the denominator; recompute the target
  after the config change before trusting the percentage.
- The intended threshold above 88.0 was never specified in config — 95.0 comes
  from `task.md`, not prior project config (research Q1, Open Areas).
```

Next: run `/lifecycle:4_structure workspace/T4-2026-06-19-cq-coverage-add-test-coverage-measurement-and-reac/`
