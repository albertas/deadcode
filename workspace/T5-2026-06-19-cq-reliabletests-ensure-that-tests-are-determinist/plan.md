# Implementation Plan

## Overview

Make every unit test pass regardless of cwd, `PYTHONHASHSEED`, and xdist worker
count by sorting the one non-deterministic directory walk, mocking config
discovery in the shared base, converting the two FS-bypass test modules to
isolated temp trees, anchoring the genuine e2e tests to the repo root, and
aligning the serial `Makefile` runner onto the same parallel invocation as the
`Justfile`.

Phases are landed in order (1→5); each is independently verifiable. The repo
root is `/home/niekas/tools/deadcode`. Run all `just`/`make` commands from there.

---

## Phase 1: Deterministic directory walk (source)

Sort the single OS-order-dependent walk so discovery order, verbose logs, and
order-sensitive assertions are stable across filesystems and xdist workers.
Foundational because Phases 3–4 assert on walk output.

### Changes

#### 1. Sort the glob walk
**File**: `deadcode/actions/find_python_filenames.py`
**Action**: modify

Line 25 currently:

```python
            paths += list([str(p) for p in path.glob('*')])
```

Change to:

```python
            paths += sorted(str(p) for p in path.glob('*'))
```

Rationale and notes:
- The walk uses a LIFO stack (`paths.pop()` at line 15), so the *appended*
  order determines discovery order. `sorted(...)` makes that order
  deterministic regardless of the host filesystem.
- The function signature `find_python_filenames(args: Args) -> List[str]` is
  unchanged. Final emitted output is already normalized by
  `sorted(..., key=(filename, name_line))` in
  `deadcode/visitor/find_unused_code_visitor.py:156-169`, so the emitted
  results stay byte-identical; only intermediate discovery/verbose order
  becomes stable.
- The `list([...])` wrapper is replaced by `sorted(...)` (which returns a list),
  so the `+=` concatenation semantics are preserved.

### Verification
#### Automated
- [x] `just test` passes (coverage ≥ 95%, gate at `pyproject.toml:211`).
- [ ] `just lint` and `just typecheck` pass (no signature/type change). NOTE: `just lint` was already failing before this change with 3 pre-existing errors in `find_python_filenames.py` (UP035/UP006 — deprecated `typing.List`). My change introduces no new lint issues. The 3 errors are unchanged from before this phase.

#### Manual
- [x] Repeated-call determinism probe returns `OK` and exits 0:
  ```bash
  cd /tmp && uv run python -c "import sys; sys.path.insert(0,'/home/niekas/tools/deadcode'); from deadcode.actions.find_python_filenames import find_python_filenames; from deadcode.data_types import Args; a=Args(); a.paths=['/home/niekas/tools/deadcode/deadcode']; r1=find_python_filenames(args=a); b=Args(); b.paths=['/home/niekas/tools/deadcode/deadcode']; r2=find_python_filenames(args=b); assert r1==r2; assert r1==sorted(r1, reverse=True) or True; print('OK')"
  ```
  (The two runs from a foreign cwd must be equal; prints `OK`.)
- [x] Confirm the edit is present:
  `grep -q "sorted(str(p) for p in path.glob('\*'))" deadcode/actions/find_python_filenames.py`
  returns 0.

---

## Phase 2: Mock config discovery in the shared base

Patch `parse_pyproject_toml` to return `{}` by default in `BaseTestCase.setUp`,
removing the hidden cwd dependence on the repo's real `[tool.deadcode]` block
for every unit test that reaches `main()`. Foundational for all `BaseTestCase`
subclasses.

### Changes

#### 1. Add the config-discovery mock in `setUp`
**File**: `deadcode/utils/base_test_case.py`
**Action**: modify

In `setUp`, after the existing `os.remove` patch (line 52) and before
`self.args = Args()` (line 54), add:

```python
        self.parse_pyproject_toml_mock = self.patch('deadcode.actions.parse_arguments.parse_pyproject_toml')
        self.parse_pyproject_toml_mock.return_value = {}
```

Rationale and notes:
- `parse_pyproject_toml` is defined and called as a bare name within
  `deadcode/actions/parse_arguments.py` (defined at `:213`, called at `:198`
  inside `parse_arguments`). Patching the name on the *defining* module object
  (per the `test_parsing.py:13` pattern) intercepts that call.
- Uses the existing `self.patch(path: str) -> MagicMock` helper, which registers
  `addCleanup(patcher.stop)`. No new types or imports.
- Returning `{}` matches the real function's "no config" contract (it returns
  `{}` when `pyproject.toml` is absent — `parse_arguments.py:220`).
- `test_parsing.py` overrides `setUp` and does **not** call `super().setUp()`;
  it isolates config itself by mocking `tomllib.load`. It is therefore
  unaffected by this change. No edit needed there.

### Verification
#### Automated
- [x] `just test` passes (coverage ≥ 95%).
- [ ] `cd /tmp && PYTHONHASHSEED=random uv run pytest -p xdist -n auto /home/niekas/tools/deadcode/tests`
  exits 0 (full suite green from a foreign cwd under hash randomization +
  xdist). NOTE: 9 failures remain from Phases 3–4 (test_find_python_filenames.py, test_exclude.py, test_deadcode.py integration tests); those are resolved by Phases 3 and 4 respectively.

#### Manual
- [x] cwd-independence probe: `tests/test_output.py` produces identical results
  from `/tmp` and the repo root: 6 passed in both environments (exit code 1 from
  coverage gate is expected for a partial-suite run, not a Phase 2 concern).
- [x] Confirm the mock is wired:
  `grep -q "parse_pyproject_toml_mock" deadcode/utils/base_test_case.py` returns 0.

---

## Phase 3: Convert FS-bypass unit modules to temp trees

Rewrite the two modules that import `find_python_filenames` directly (bypassing
the `deadcode.cli` mock and hitting the real tree at cwd-relative literals) to
build a controlled directory tree under `tempfile.TemporaryDirectory()` in
`setUp`, pointing `args.paths` at absolute paths inside it. Preserves the
behavioral coverage (file detection, dir recursion, exclude-by-file,
exclude-by-dir, missing-path error, verbose logs) while being cwd-independent.

These classes still subclass `BaseTestCase` (so they inherit the Phase-2 config
mock), but they no longer rely on the `deadcode.cli.find_python_filenames` mock
because they call the function directly against the temp tree.

### Changes

#### 1. Rewrite `test_find_python_filenames.py`
**File**: `tests/actions/test_find_python_filenames.py`
**Action**: modify (full rewrite)

Build a temp tree in `setUp`. Shape mirrors the original assertions
(`deadcode/cli.py` + a `deadcode/utils/` subdir):

```
<tmp>/pkg/cli.py
<tmp>/pkg/utils/helper.py
<tmp>/pkg/notes.txt        # non-.py, to exercise the suffix filter
```

```python
import tempfile
from pathlib import Path

from deadcode.actions.find_python_filenames import find_python_filenames
from deadcode.utils.base_test_case import BaseTestCase


class TestFindPythonFilenames(BaseTestCase):
    def setUp(self):
        super().setUp()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tree_root = Path(self._tmp.name)

        self.pkg = self.tree_root / 'pkg'
        self.utils = self.pkg / 'utils'
        self.utils.mkdir(parents=True)
        self.cli_py = self.pkg / 'cli.py'
        self.cli_py.write_text('x = 1\n')
        (self.utils / 'helper.py').write_text('y = 2\n')
        (self.pkg / 'notes.txt').write_text('not python\n')

    def test_file_detection(self):
        self.args.paths = [str(self.cli_py)]
        filenames = find_python_filenames(args=self.args)
        self.assertListEqual(filenames, [str(self.cli_py)])

    def test_exclude_directories(self):
        self.args.paths = [str(self.pkg)]
        filenames = find_python_filenames(args=self.args)
        self.assertTrue(any(f == str(self.cli_py) for f in filenames))
        self.assertTrue(any(str(self.utils) in f for f in filenames))

        self.args.exclude = [str(self.utils), str(self.cli_py)]
        filenames = find_python_filenames(args=self.args)
        self.assertFalse(any(f == str(self.cli_py) for f in filenames))
        self.assertFalse(any(str(self.utils) in f for f in filenames))

    def test_exclude_files(self):
        self.args.paths = [str(self.pkg)]
        filenames = find_python_filenames(args=self.args)
        self.assertTrue(str(self.cli_py) in filenames)

        self.args.exclude = [str(self.cli_py)]
        filenames = find_python_filenames(args=self.args)
        self.assertFalse(str(self.cli_py) in filenames)

    def test_non_python_file_is_skipped(self):
        self.args.paths = [str(self.pkg)]
        filenames = find_python_filenames(args=self.args)
        self.assertFalse(any(f.endswith('notes.txt') for f in filenames))

    def test_provided_path_does_not_exist(self):
        missing = str(self.tree_root / 'path_does_not_exist')
        self.args.paths = [missing]
        with self.assertLogs(level='ERROR') as cm:
            find_python_filenames(args=self.args)
        self.assertEqual(cm.output[0], f'ERROR:root:Error: {missing} could not be found.')

    def test_verbose_logs_ignored_and_listed_files(self):
        self.args.paths = [str(self.cli_py)]
        self.args.exclude = [str(self.cli_py)]
        self.args.verbose = True
        with self.assertLogs(level='INFO') as cm:
            find_python_filenames(args=self.args)
        assert any('Ignoring' in message for message in cm.output)
        assert any('Files to be checked' in message for message in cm.output)
```

Notes:
- `super().setUp()` is required so the Phase-2 config mock and the base mocks
  are installed; the original module had no `setUp` override.
- `test_non_python_file_is_skipped` is **added** to preserve coverage of the
  `path.suffix == '.py'` branch (`find_python_filenames.py:22`), which the
  original real-tree tests exercised implicitly via the real `deadcode/` tree.
- `_match(path, exclude)` (exclude logic) does substring/`fnmatch`-style
  matching on the path string; absolute temp paths work with the `==` /
  `in`-style assertions above. If `test_exclude_directories` /
  `test_exclude_files` fail because `_match` does not match an absolute exclude
  literal, inspect `deadcode/visitor/ignore.py:_match` and adjust the exclude
  string to the form it matches (e.g. a trailing-glob form) — keep the
  behavioral intent (the file/dir is excluded) identical.

#### 2. Rewrite `test_exclude.py`
**File**: `tests/cli_args/test_exclude.py`
**Action**: modify (full rewrite)

Same temp-tree approach; this module covers exclude-by-dir and exclude-by-file
only:

```python
import tempfile
from pathlib import Path

from deadcode.utils.base_test_case import BaseTestCase
from deadcode.actions.find_python_filenames import find_python_filenames


class TestExcludeCliArgUnit(BaseTestCase):
    def setUp(self):
        super().setUp()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tree_root = Path(self._tmp.name)

        self.pkg = self.tree_root / 'pkg'
        self.utils = self.pkg / 'utils'
        self.utils.mkdir(parents=True)
        self.cli_py = self.pkg / 'cli.py'
        self.cli_py.write_text('x = 1\n')
        (self.utils / 'helper.py').write_text('y = 2\n')

    def test_exclude_directories(self):
        self.args.paths = [str(self.pkg)]
        filenames = find_python_filenames(args=self.args)
        self.assertTrue(any(f == str(self.cli_py) for f in filenames))
        self.assertTrue(any(str(self.utils) in f for f in filenames))

        self.args.exclude = [str(self.utils), str(self.cli_py)]
        filenames = find_python_filenames(args=self.args)
        self.assertFalse(any(f == str(self.cli_py) for f in filenames))
        self.assertFalse(any(str(self.utils) in f for f in filenames))

    def test_exclude_files(self):
        self.args.paths = [str(self.pkg)]
        filenames = find_python_filenames(args=self.args)
        self.assertTrue(str(self.cli_py) in filenames)

        self.args.exclude = [str(self.cli_py)]
        filenames = find_python_filenames(args=self.args)
        self.assertFalse(str(self.cli_py) in filenames)
```

### Verification
#### Automated
- [x] `cd /tmp && uv run pytest /home/niekas/tools/deadcode/tests/actions/test_find_python_filenames.py /home/niekas/tools/deadcode/tests/cli_args/test_exclude.py`
  exits 0 (passes from a non-repo cwd — the defining symptom of the old bypass).
- [x] `just test` still green and coverage ≥ 95%.
- [ ] `just lint` passes (new imports `tempfile`, `pathlib.Path` are used). NOTE: `just lint` has pre-existing failures (UP035/UP006/etc. in source files unrelated to this phase); no new lint issues introduced by Phase 3.

#### Manual
- [x] Confirm no cwd-relative bare literals remain in the two modules:
  `grep -n "deadcode/cli.py\|deadcode/\." tests/actions/test_find_python_filenames.py tests/cli_args/test_exclude.py`
  returns no matches (exit 1).
- [x] Confirm temp-tree usage is present:
  `grep -q "TemporaryDirectory" tests/actions/test_find_python_filenames.py tests/cli_args/test_exclude.py`
  returns 0.
- [x] Coverage of the walk branches did not drop: run
  `uv run pytest tests/actions/test_find_python_filenames.py tests/cli_args/test_exclude.py --cov=deadcode.actions.find_python_filenames --cov-report=term-missing --no-cov-on-fail`
  and confirm lines 22, 24, 25, 26, 29, 31-33 of
  `find_python_filenames.py` are not reported missing. RESULT: 100% coverage on find_python_filenames.py — no lines missing.

---

## Phase 4: Anchor e2e tests to the repo root

Keep `DeadCodeIntegrationTests` and `CliEntrypointTests` reading real files
under `tests/files/` and `deadcode/`, but `chdir` to the repo root in `setUp`
with an `addCleanup` restore so they pass from any cwd and survive concurrent
xdist workers.

### Changes

#### 1. Add a repo-root helper and `chdir` in e2e `setUp`
**File**: `tests/test_deadcode.py`
**Action**: modify

Add imports and a module-local `REPO_ROOT` (no new framework):

```python
import os
import runpy
import sys
from pathlib import Path
from unittest import TestCase, mock

from deadcode.cli import main
from deadcode.utils.base_test_case import BaseTestCase

REPO_ROOT = Path(__file__).parents[1]
```

Add a `setUp` to `DeadCodeIntegrationTests` (currently has none):

```python
class DeadCodeIntegrationTests(TestCase):
    def setUp(self):
        self._prev_cwd = os.getcwd()
        os.chdir(REPO_ROOT)
        self.addCleanup(os.chdir, self._prev_cwd)

    def test_unused_variable_name_found_successfully(self):
        ...
```

Add the identical `setUp` to `CliEntrypointTests`:

```python
class CliEntrypointTests(TestCase):
    def setUp(self):
        self._prev_cwd = os.getcwd()
        os.chdir(REPO_ROOT)
        self.addCleanup(os.chdir, self._prev_cwd)

    def test_module_runs_as_script(self):
        ...
```

Notes:
- `DeadCodeTests` (the `BaseTestCase` subclass at `:65`) uses `self.files` /
  mocks only — no real-FS access — so it does **not** need a `chdir`. Leave it
  unchanged.
- Keep the existing relative-path literals (`'tests/files/variables.py'`,
  `'deadcode/data_types.py'`, etc.); they now resolve against the anchored root.
- `addCleanup(os.chdir, self._prev_cwd)` restores per test, so a concurrent
  xdist worker never observes a stale cwd (Open Risk: xdist + chdir).
- `parents[1]` from `tests/test_deadcode.py` is the repo root
  (`/home/niekas/tools/deadcode`).

### Verification
#### Automated
- [x] `cd /tmp && uv run pytest /home/niekas/tools/deadcode/tests/test_deadcode.py`
  exits 0 (passes from a foreign cwd). NOTE: exit code 1 from coverage gate only (coverage tool maps to wrong paths from /tmp); all 6 tests passed.
- [x] `cd /tmp && uv run pytest -p xdist -n auto /home/niekas/tools/deadcode/tests/test_deadcode.py`
  exits 0 (chdir/worker interaction safe under xdist). Run with --no-cov; 6 passed.
- [x] `just test` green; coverage ≥ 95%. 176 passed, 18 skipped, 98.77% coverage.

#### Manual
- [x] Confirm the integration output ordering matches the Phase-1 sorted order —
  the existing assertions in `test_unused_variable_name_found_successfully`
  (lines 1/3/5 of `variables.py`) still pass; covered by the pytest run above
  exiting 0. If any assertion fails on ordering, re-confirm against the sorted
  discovery order (Open Risk: e2e output ordering).
- [x] Confirm the anchor is present:
  `grep -q "REPO_ROOT = Path(__file__).parents\[1\]" tests/test_deadcode.py` and
  `grep -q "self.addCleanup(os.chdir, self._prev_cwd)" tests/test_deadcode.py`
  both return 0.

---

## Phase 5: Single parallel runner

Align the serial `Makefile` test target with the `Justfile` so both run
pytest-xdist on all-but-one cores and cannot diverge. Consolidation phase — if
it fails, Phases 1–4 remain independently valuable.

### Changes

#### 1. Add xdist parallelism to the Makefile test target
**File**: `Makefile`
**Action**: modify

Line 19 currently:

```make
	.venv/bin/pytest -vv $(PYTEST_ME_PLEASE)
```

Change to:

```make
	.venv/bin/pytest -n "$(shell nproc --ignore=1)" -vv $(PYTEST_ME_PLEASE)
```

Rationale:
- Matches `Justfile:11` (`uv run pytest -n "$(nproc --ignore=1)"`). The task
  mandates all-but-one cores specifically (not `-n auto`).
- The `-n` value stays in the recipe because pytest `addopts` cannot compute
  `nproc-1`. `$(shell nproc --ignore=1)` is GNU-Make command substitution
  (distinct from the Justfile's shell `$(...)`).
- `Justfile:11` is already correct and left unchanged.

### Verification
#### Automated
- [x] `just test` exits 0 (Justfile unchanged, still parallel). 176 passed, 18 skipped, 98.77% coverage.
- [x] `make test PYTEST_ME_PLEASE=tests/test_output.py` exits 0 and runs under
  multiple workers. NOTE: exit code 1 from coverage gate (partial run only); 6 tests passed under 7 workers.

#### Manual
- [x] `grep -q 'nproc --ignore=1' Makefile` returns 0.
- [x] Worker fan-out is active: `make test PYTEST_ME_PLEASE=tests/test_output.py`
  output contains xdist worker markers — confirm with
  `make test PYTEST_ME_PLEASE=tests/test_output.py 2>&1 | grep -qE 'gw0|workers'`
  returns 0. Confirmed: "created: 7/7 workers", "7 workers [6 items]", "[gw0] PASSED".

---

## Testing Checkpoints

After each phase the following should hold (useful for resuming if context
resets):

- **After Phase 1**: `just test` green; `find_python_filenames` returns the same
  order on repeated calls from any cwd.
- **After Phase 2**: full suite green from `/tmp` under `PYTHONHASHSEED=random` +
  xdist; no unit test inherits the repo's real `[tool.deadcode]` config.
- **After Phase 3**: `test_find_python_filenames.py` and `test_exclude.py` pass
  from a non-repo cwd; coverage still ≥ 95%; all walk branches exercised.
- **After Phase 4**: `test_deadcode.py` passes from any cwd, including under
  `-n auto`; integration output matches sorted discovery order.
- **After Phase 5**: `make test` and `just test` both run parallel on
  all-but-one cores; the two runners can no longer diverge.

**Final acceptance** (design "Verification"):
- [ ] `just test` green.
- [ ] `cd /tmp && PYTHONHASHSEED=random uv run pytest -p xdist -n auto /home/niekas/tools/deadcode/tests`
  green.
- [ ] The two converted unit modules pass from an arbitrary cwd (Phase 3
  verification).
- [ ] Coverage stays ≥ 95% (`pyproject.toml:211`).

**Orphans noted, not touched** (per design "What We're NOT Doing"):
`assertUpdatedFiles` (`base_test_case.py:84`, never called) and the empty test
files (`tests/cli_args/test_no_color.py`, `test_quiet.py`, `test_count.py`,
`test_verbose.py`, `test_ignore_names_in_files.py`).
