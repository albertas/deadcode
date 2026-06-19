# Design Discussion

## Current State

The suite already runs in parallel in one place and serially in another, and a
handful of "unit" tests reach the live filesystem and the current working
directory.

- **Two divergent runners.** `Justfile:10-11` runs
  `uv run pytest -n "$(nproc --ignore=1)"` — pytest-xdist across all-but-one
  cores. `Makefile:18-19` runs `.venv/bin/pytest -vv` — **serial, no `-n`**.
  Both pick up coverage via `addopts` (`pyproject.toml:211`,
  `--cov-fail-under=95.0`). pytest-xdist + pytest-cov are declared
  (`pyproject.toml:33-34`).
- **Shared base mocks file I/O but not config discovery.**
  `BaseTestCase` (`deadcode/utils/base_test_case.py:10`) patches
  `find_python_filenames` (only at the `deadcode.cli` import site, `:40-41`),
  `open` in three modules (`:43-50`), and `os.remove` (`:52`). It serves an
  in-memory `self.files` dict. It does **not** mock `parse_pyproject_toml`.
- **Hidden cwd coupling in unit tests.** Any `BaseTestCase` test that calls
  `main()` triggers `parse_pyproject_toml` (`parse_arguments.py:219`), which
  opens `pyproject.toml` **relative to cwd** with no upward search. The repo's
  `pyproject.toml:179-190` defines a populated `[tool.deadcode] ignore_names`,
  so these tests silently inherit real config — passing only because CI runs
  from the repo root. `test_parsing.py:12-22` is the one place that mocks
  `tomllib.load` in its own `setUp`.
- **Tests that bypass the mock and hit real FS.**
  `tests/actions/test_find_python_filenames.py` and
  `tests/cli_args/test_exclude.py` import `find_python_filenames` **directly**
  (`test_find_python_filenames.py:1`, `test_exclude.py:2`), so the
  `deadcode.cli` mock never intercepts them. They walk the real `deadcode/`
  package via bare relative literals (`'deadcode/.'`, `'deadcode/cli.py'`),
  resolving only when cwd == repo root.
- **Genuine end-to-end tests.** `DeadCodeIntegrationTests`
  (`tests/test_deadcode.py:9`, plain `TestCase`) and `CliEntrypointTests`
  (`:73`) call `main()` / `runpy` against real files under `tests/files/` and
  `deadcode/`, again via cwd-relative literals.
- **Source non-determinism is narrow.** `find_python_filenames.py:25`
  (`path.glob('*')`) returns entries in filesystem order; discovery order is
  OS-dependent. But final output is normalized by `sorted(...)` on
  `(filename, name_line)` (`find_unused_code_visitor.py:156-169`). Sets are used
  only for membership tests (research Q5); dict iteration is insertion-order.
  No network access exists anywhere (research Q4). No `lru_cache`/global mutable
  state leaks across tests (research Q6).

## Desired End State

- A single, consistent invocation runs the whole suite in parallel via
  pytest-xdist on all-but-one cores; the serial Makefile path is aligned so it
  cannot diverge.
- Every test classified as a **unit test** passes regardless of cwd,
  `PYTHONHASHSEED`, xdist worker count, or the contents of the repo's real
  `pyproject.toml` and `deadcode/` tree.
- Only the explicitly-designated **end-to-end tests**
  (`DeadCodeIntegrationTests`, `CliEntrypointTests`) touch real resources, and
  even those anchor to the repo root so they are cwd-independent.

**Verification:** `just test` is green; `just test` re-run with
`cd /tmp && PYTHONHASHSEED=random uv run pytest -p xdist -n auto <repo>/tests`
is green; running the two converted unit modules from an arbitrary cwd passes;
coverage stays ≥ 95% (`pyproject.toml:211`).

## Patterns to Follow

- **Mock via `self.patch(...)` with `addCleanup`** — `base_test_case.py:15-18`.
  New mocks (config discovery) go through this same helper in `setUp`.
- **In-memory `self.files` dict as the file fixture** — rebind per test, never
  mutate the class default (`base_test_case.py:11`, research Q6). Keep this.
- **Patch the seam on the *defining* module object** — e.g.
  `tomllib.load` is patched at `deadcode.actions.parse_arguments.tomllib.load`
  (`test_parsing.py:13`). Follow this for the config-discovery mock, not at the
  stdlib site.
- **Repo-root anchoring from `__file__`** for e2e: derive the root as
  `Path(__file__).parents[1]` and `chdir` with an `addCleanup` restore — the
  codebase has no such helper yet, so introduce a small one local to the e2e
  module rather than a new framework.

**Patterns to NOT follow:**

- Do **not** import `find_python_filenames` directly into a `BaseTestCase`
  subclass and then walk the real tree (`test_find_python_filenames.py:1`,
  `test_exclude.py:2`) — this is the exact bypass causing cwd/FS coupling.
- Do **not** rely on cwd-relative bare literals (`'deadcode/.'`) to locate
  inputs (`test_deadcode.py:11`, etc.).
- Do **not** add `setUpClass`/class-level mutable fixtures — none exist today;
  parallel workers + shared class state is a flakiness source.

## Design Decisions

1. **Single parallel runner, nproc-based.** Keep `-n "$(nproc --ignore=1)"`
   in the shell runners and update `Makefile:18-19` to match the Justfile, so
   both run parallel on all-but-one cores. Rationale: `addopts` cannot compute
   `nproc-1`, so the value must stay in the shell recipe; the task mandates
   all-but-one cores specifically (not `-n auto`).
2. **Mock config discovery in `BaseTestCase.setUp`.** Patch
   `deadcode.actions.parse_arguments.parse_pyproject_toml` to return `{}` by
   default. Rationale: removes the hidden cwd dependence on the real
   `[tool.deadcode]` block for every unit test that calls `main()`; patching the
   single function is simpler and less brittle than mocking
   `os.path.isfile`+`tomllib.load`. `test_parsing.py`'s own `setUp` already
   isolates config and is unaffected.
3. **Convert the two FS-bypass modules to isolated temp trees.** In
   `test_find_python_filenames.py` and `test_exclude.py`, build a controlled
   directory tree under `tempfile.TemporaryDirectory()` in `setUp` (cleaned up
   in `tearDown`/`addCleanup`) and point `args.paths` at absolute paths inside
   it. Rationale: still exercises the *real* walk logic (`is_file`/`is_dir`/
   `glob`/`exclude`) but with deterministic, cwd-independent input. Rejected
   alternatives: patching every `pathlib` seam (brittle, couples tests to
   implementation); adding `pyfakefs` (new dependency, no existing fixture
   infra — research Q6 found no `conftest.py`).
4. **Keep e2e tests real, make them cwd-independent.** Leave
   `DeadCodeIntegrationTests` and `CliEntrypointTests` reading real files, but
   `chdir` to `Path(__file__).parents[1]` in `setUp` with an `addCleanup`
   restore so they pass from any cwd. Rationale: the task explicitly permits
   genuine e2e tests to use real resources; only their cwd assumption is the
   defect.
5. **Sort the directory walk in source.** Change
   `find_python_filenames.py:25` to iterate `sorted(path.glob('*'))`.
   Rationale: makes discovery order, verbose logs (`:31-33`), and any
   order-sensitive assertion stable across filesystems and xdist workers.
   Low-risk: final output is already `sorted(...)` so emitted results are
   unchanged. (Judgment call — minimal, surgical, directly serves determinism.)
6. **Do not pin `PYTHONHASHSEED`.** Research Q5 confirms sets are
   membership-only and dicts iterate insertion-order, so output is already
   hash-seed-independent. Pinning would mask, not fix, future regressions.
7. **No new fixture framework.** Stay with unittest + `self.patch`; do not
   introduce `conftest.py` or `@pytest.fixture`. Rationale: surgical change,
   matches the dominant pattern.

## What We're NOT Doing

- Not rewriting passing `BaseTestCase` tests, the `assertFiles` helper, or the
  `self.files` mechanism.
- Not adding `pyfakefs`, `pytest-randomly`, or any new dependency.
- Not changing the coverage gate, coverage source/omit, or `addopts`
  (`pyproject.toml:211-215`).
- Not removing the Makefile or the (never-called) `assertUpdatedFiles`
  (`base_test_case.py:84`) or the empty test files
  (`tests/cli_args/test_no_color.py`, etc.) — flagged as orphans only.
- Not adding upward `pyproject.toml` search to `parse_arguments.py` (out of
  scope; we mock it in tests instead).
- Not refactoring the source beyond the single `sorted()` change.

## Open Risks

- **Temp-tree conversion may shift assertions.** Current
  `test_find_python_filenames`/`test_exclude` assert on names like
  `'deadcode/cli.py'`; the rewritten tests will assert on temp-relative names.
  Need to keep the *behavioral* coverage (file detection, dir recursion, exclude
  by file and by dir, missing-path error, verbose logs) equivalent.
- **Coverage drift.** Replacing real-FS tests could change which source lines
  execute; watch the 95% gate (`pyproject.toml:211`) and add cases if a branch
  drops.
- **e2e output ordering.** With decision 5 the integration output is stable, but
  if any e2e assertion implicitly relied on the old glob order it must be
  re-confirmed against the sorted order.
- **xdist + chdir interaction.** e2e `chdir` runs inside worker processes;
  `addCleanup` restore must be reliable so concurrent tests in the same worker
  don't observe a stale cwd.
