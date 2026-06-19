# Structure Outline

## Approach

Make every unit test pass regardless of cwd, hash seed, and xdist worker count
by (a) making the one non-deterministic source path deterministic, (b) mocking
config discovery in the shared base, (c) converting the two FS-bypass test
modules to isolated temp trees, and (d) anchoring the genuine e2e tests to the
repo root — then aligning the two divergent runners onto one parallel
invocation. Each change is independently landable and verifiable; no new
dependency or fixture framework is added (design decisions 6 & 7 are no-ops).

---

## Phase 1: Deterministic directory walk (source)

Sort the single OS-order-dependent walk so discovery order, verbose logs, and
any order-sensitive assertion are stable across filesystems and xdist workers.
Foundational because Phases 3–4 assert on walk output.

**Files**: `deadcode/actions/find_python_filenames.py`

**Key changes**:
- Line 25: `paths += [str(p) for p in path.glob('*')]` →
  `paths += sorted(str(p) for p in path.glob('*'))` — discovery order made
  deterministic. Signature of `find_python_filenames(args: Args) -> List[str]`
  is unchanged; emitted output already passes through
  `sorted(..., key=(filename, name_line))` so results are byte-identical.

**Verify**: `just test` passes (coverage ≥ 95%). Determinism probe — run the
walk twice from an arbitrary cwd and assert identical order:
`cd /tmp && uv run python -c "import os,sys; sys.path.insert(0,'/home/niekas/tools/deadcode'); from deadcode.actions.find_python_filenames import find_python_filenames; from deadcode.data_types import Args; a1=Args(); a1.paths=['/home/niekas/tools/deadcode/deadcode']; r1=find_python_filenames(args=a1); a2=Args(); a2.paths=['/home/niekas/tools/deadcode/deadcode']; assert r1==find_python_filenames(args=a2) and r1==sorted(r1) or r1==find_python_filenames(args=a2); print('OK')"`
returns `OK` and exits 0.

---

## Phase 2: Mock config discovery in the shared base

Patch `parse_pyproject_toml` to return `{}` by default in
`BaseTestCase.setUp`, removing the hidden cwd dependence on the repo's real
`[tool.deadcode]` block for every unit test that reaches `main()`. Foundational
for all `BaseTestCase` subclasses.

**Files**: `deadcode/utils/base_test_case.py`

**Key changes**:
- In `setUp` (after the existing `self.patch(...)` calls), add:
  `self.parse_pyproject_toml_mock = self.patch('deadcode.actions.parse_arguments.parse_pyproject_toml')`
  then `self.parse_pyproject_toml_mock.return_value = {}` — patched on the
  *defining* module object, via the existing `self.patch(path: str) -> MagicMock`
  helper (registers `addCleanup`). No new types.
- `test_parsing.py` overrides `setUp` already and isolates config itself
  (mocks `tomllib.load`); confirm it is unaffected.

**Verify**: `just test` passes. cwd-independence probe — the full suite stays
green from a foreign cwd with config that would otherwise interfere:
`cd /tmp && PYTHONHASHSEED=random uv run pytest -p xdist -n auto /home/niekas/tools/deadcode/tests` exits 0. Confirm the real `[tool.deadcode] ignore_names`
no longer leaks: a `BaseTestCase` test calling `main()` produces identical
output whether run from `/tmp` or the repo root (compare two `pytest` runs of
`tests/test_output.py`, both exit 0).

---

## Phase 3: Convert FS-bypass unit modules to temp trees

Rewrite the two modules that import `find_python_filenames` directly (bypassing
the `deadcode.cli` mock and hitting the real tree at cwd-relative literals) to
build a controlled directory tree under `tempfile.TemporaryDirectory()` in
`setUp`, pointing `args.paths` at absolute paths inside it. Preserves the
behavioral coverage (file detection, dir recursion, exclude-by-file,
exclude-by-dir, missing-path error, verbose logs) while being cwd-independent.

**Files**: `tests/actions/test_find_python_filenames.py`,
`tests/cli_args/test_exclude.py`

**Key changes**:
- `setUp` builds a temp tree (e.g. `pkg/cli.py`, `pkg/utils/helper.py`) and
  stores its absolute root: `self.tree_root: str`. Register cleanup via
  `addCleanup(self._tmp.cleanup)` (or `tearDown`).
- Each test sets `self.args.paths = [<abs path under self.tree_root>]` and
  `self.args.exclude = [<abs path>]`; assertions switch from
  `'deadcode/cli.py'` literals to temp-relative/absolute names.
- Classes still subclass `BaseTestCase` (so they inherit the Phase-2 config
  mock); they no longer rely on the `deadcode.cli.find_python_filenames` mock
  because they call the function directly against the temp tree.

**Verify**: `cd /tmp && uv run pytest /home/niekas/tools/deadcode/tests/actions/test_find_python_filenames.py /home/niekas/tools/deadcode/tests/cli_args/test_exclude.py` exits 0 (passes from a
non-repo cwd — the defining symptom of the old bypass). `just test` still
green and coverage ≥ 95% (watch that the `is_file`/`is_dir`/`glob`/`exclude`/
missing-path/verbose branches still execute — add a case if a branch drops).

---

## Phase 4: Anchor e2e tests to the repo root

Keep `DeadCodeIntegrationTests` and `CliEntrypointTests` reading real files
under `tests/files/` and `deadcode/`, but `chdir` to the repo root in `setUp`
with an `addCleanup` restore so they pass from any cwd and survive concurrent
xdist workers.

**Files**: `tests/test_deadcode.py`

**Key changes**:
- Add a small module-local helper (no new framework): derive
  `REPO_ROOT = Path(__file__).parents[1]`.
- In each `TestCase`'s `setUp`: `self._prev_cwd = os.getcwd()`,
  `os.chdir(REPO_ROOT)`, `self.addCleanup(os.chdir, self._prev_cwd)` — restore
  is reliable per test so a worker never observes a stale cwd. Real
  relative-path literals (`'tests/files/variables.py'`, `'deadcode/data_types.py'`)
  are kept; they now resolve against the anchored root.

**Verify**: `cd /tmp && uv run pytest /home/niekas/tools/deadcode/tests/test_deadcode.py` exits 0. Run under
xdist from a foreign cwd to confirm the chdir/worker interaction is safe:
`cd /tmp && uv run pytest -p xdist -n auto /home/niekas/tools/deadcode/tests/test_deadcode.py` exits 0 and the
integration output ordering matches the Phase-1 sorted order.

---

## Phase 5: Single parallel runner

Align the serial `Makefile` test target with the `Justfile` so both run
pytest-xdist on all-but-one cores and cannot diverge. Consolidation phase — if
it fails, Phases 1–4 remain independently valuable.

**Files**: `Makefile`

**Key changes**:
- Line 18–19: `.venv/bin/pytest -vv $(PYTEST_ME_PLEASE)` →
  `.venv/bin/pytest -n "$(shell nproc --ignore=1)" -vv $(PYTEST_ME_PLEASE)`
  (the `-n` value stays in the recipe because `addopts` cannot compute
  `nproc-1`; task mandates all-but-one cores, not `-n auto`). `Justfile:11`
  is already correct and left unchanged.

**Verify**: `just test` exits 0. `grep -q 'nproc --ignore=1' Makefile` returns
0. `make test PYTEST_ME_PLEASE=tests/test_output.py` runs under multiple
workers (output shows `gw0`/`gw1` xdist workers) and exits 0.

---

## Testing Checkpoints

After each phase the following should hold (useful for resuming if context
resets):

- **After Phase 1**: `just test` green; `find_python_filenames` returns the
  same order on repeated calls from any cwd.
- **After Phase 2**: full suite green from `/tmp` under
  `PYTHONHASHSEED=random` + xdist; no unit test inherits the repo's real
  `[tool.deadcode]` config.
- **After Phase 3**: `test_find_python_filenames.py` and `test_exclude.py`
  pass from a non-repo cwd; coverage still ≥ 95%; all walk branches exercised.
- **After Phase 4**: `test_deadcode.py` passes from any cwd, including under
  `-n auto`; integration output matches sorted discovery order.
- **After Phase 5**: `make test` and `just test` both run parallel on
  all-but-one cores; the two runners can no longer diverge.

**Final acceptance** (design "Verification"): `just test` green; re-run
`cd /tmp && PYTHONHASHSEED=random uv run pytest -p xdist -n auto /home/niekas/tools/deadcode/tests`
green; the two converted unit modules pass from an arbitrary cwd; coverage
stays ≥ 95% (`pyproject.toml:211`).

**Orphans noted, not touched** (per design "What We're NOT Doing"):
`assertUpdatedFiles` (`base_test_case.py:84`, never called) and the empty test
files (`tests/cli_args/test_no_color.py`, `test_quiet.py`, `test_count.py`,
`test_verbose.py`, `test_ignore_names_in_files.py`).
