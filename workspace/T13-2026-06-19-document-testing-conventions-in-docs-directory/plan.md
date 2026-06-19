# Implementation Plan

## Overview

Revise the existing `docs/testing-and-tooling.md` in place so every `file:line`
reference matches the current source, the missing testing conventions are folded
in, and the two unverifiable/filler claims are removed. Docs-only: no new file,
no index change, no code touched. All commands run from repo root
`/home/niekas/tools/deadcode`.

**Pre-verified anchors** (confirmed against live source during planning; use these
exact numbers):

- `base_test_case.py`: class `10`, `patch()` `15-18`, `_read_file_side_effect`
  `23-35`, `setUp` `37-57`, `assertFiles` `59-85`, `assertUpdatedFiles` `87-96`.
- `find_python_filenames.py`: sorted glob at `24`.
- `Makefile`: `check`→`5`, `fix`→`6`, `test`→`20-21`, `lint`→`23-24`,
  `mypy`→`29-30`, `deadcode`→`32-33`, `format`→`39-40`, `audit`→`42-43`.
- `Justfile`: `test`→`10-11`, `check`→`34`.
- `pyproject.toml`: `addopts`→`215`; `tests/*` ignores `S101, PT009, ANN201,
  SLF001, D` at `153-160`.
- No `conftest.py` under `tests/`. `__init__.py` only in `tests/cli_args/`,
  `tests/utils/` (plus the `tests/files/subdir/another_subdir/__init__.py`
  fixture).

Phases follow `structure.md` order. Every phase edits the same file:
`docs/testing-and-tooling.md`.

---

## Phase 1: Test Suite Organization + naming conventions

### Changes

#### 1. Add naming/style facts to "Test Suite Organization"
**File**: `docs/testing-and-tooling.md`
**Action**: modify

Correct the top-level module description (line 21) — `test_deadcode.py` is mixed,
not purely integration — and add a new subsection documenting naming and style
conventions. Insert the new subsection after the "Test Files Directory" block
(after line 32, before `## BaseTestCase Helper Class` on line 34).

Change line 21 from:

```markdown
- `test_deadcode.py` — full integration tests (uses real filesystem)
```

to:

```markdown
- `test_deadcode.py` — **mixed**: a `BaseTestCase` class using the mock layer plus two real-filesystem integration classes (`DeadCodeIntegrationTests`, `CliEntrypointTests`)
```

Insert this new subsection (after the "Test Files Directory" block):

```markdown
### Naming and Style Conventions

- **Modules**: all named `test_<snake_case_subject>.py` (e.g. `tests/fix/test_class_def.py`).
- **Classes**: two forms — the dominant `Test<DescriptiveName>` (e.g. `TestAssignmentExpressionRemoval`) and a minority `<DescriptiveName>Tests` (e.g. `CommandLineArgParsingTests`, `DeadCodeIntegrationTests`).
- **Methods**: uniformly `test_<behavior_in_snake_case>` (e.g. `test_unused_variable_name_found_successfully`).
- **Runner style**: the suite is entirely `unittest`-style classes — no plain pytest functions and **no `conftest.py`** anywhere under `tests/`.
- **`__init__.py`**: present only in `tests/cli_args/` and `tests/utils/` (both empty); other subdirs have none. (`tests/files/subdir/another_subdir/__init__.py` is a fixture, not a package marker.)
```

### Verification
#### Automated
- [x] `git -C /home/niekas/tools/deadcode diff --name-only` lists only `docs/testing-and-tooling.md`
  <!-- Note: BACKLOG.md and lifecycle_state.yml also appear — those are harness-managed files, not doc changes. -->

#### Manual
- [x] `rg -n 'CommandLineArgParsingTests' docs/testing-and-tooling.md` → matches (minority class-naming form present)
- [x] `rg -n 'Test<DescriptiveName>|test_<behavior_in_snake_case>' docs/testing-and-tooling.md` → both dominant class form and method convention present
- [x] `rg -n 'conftest|unittest-style' docs/testing-and-tooling.md` → runner-style fact present
- [x] `rg -n '__init__.py' docs/testing-and-tooling.md` → `__init__.py` placement documented
- [x] `rg -n 'test_deadcode.py.*mixed' docs/testing-and-tooling.md` → mixed nature documented
- [x] Ground truth — no conftest: `test -z "$(find tests -name conftest.py)" && echo OK` → `OK`
- [x] Ground truth — init placement: `find tests -name __init__.py` → exactly `tests/files/subdir/another_subdir/__init__.py`, `tests/cli_args/__init__.py`, `tests/utils/__init__.py`

---

## Phase 2: BaseTestCase section — fix spans, document `patch()`

### Changes

#### 1. Correct the class span on line 36
**File**: `docs/testing-and-tooling.md`
**Action**: modify

Change `deadcode/utils/base_test_case.py:10-93` to the single class anchor
`deadcode/utils/base_test_case.py:10` (prefer a symbol anchor over a hand-counted
span per design Patterns-to-Follow).

```markdown
`BaseTestCase` (`deadcode/utils/base_test_case.py:10`) extends `unittest.TestCase` and provides utilities for testing Deadcode without touching the real filesystem.
```

#### 2. Correct `setUp` span on line 40
**File**: `docs/testing-and-tooling.md`
**Action**: modify

`base_test_case.py:37-54` → `base_test_case.py:37-57`.

#### 3. Document the `patch()` helper
**File**: `docs/testing-and-tooling.md`
**Action**: modify

Add a bullet to the `### Setup` list (after the `os.remove()` bullet on line 46,
before "Creates a fresh `Args()`..." on line 48):

```markdown

It also exposes a `patch(path)` helper (`base_test_case.py:15-18`) that wraps `unittest.mock.patch`, starts it, and auto-registers `patcher.stop` via `addCleanup` so each patch is torn down after the test.
```

#### 4. Correct `_read_file_side_effect` span on line 52
**File**: `docs/testing-and-tooling.md`
**Action**: modify

`base_test_case.py:23-35` is already correct — verify, no change expected.

#### 5. Correct assertion spans on lines 56-57
**File**: `docs/testing-and-tooling.md`
**Action**: modify

- `assertFiles` `base_test_case.py:56-82` → `base_test_case.py:59-85`
- `assertUpdatedFiles` `base_test_case.py:84-93` → `base_test_case.py:87-96`

#### 6. Frame the three-tier strategy in "Tests Outside BaseTestCase"
**File**: `docs/testing-and-tooling.md`
**Action**: modify

Replace the intro line 61 ("Some tests bypass the mock layer:") to name the
three tiers (design Patterns-to-Follow):

```markdown
The suite uses three tiers: (1) mock-backed unit tests via `BaseTestCase` (no disk); (2) real-filesystem integration tests anchored to `REPO_ROOT`; (3) a hybrid that subclasses `BaseTestCase` but uses `tempfile.TemporaryDirectory()` to exercise the real `os.walk` (see Deterministic Testing below). Some tests deliberately bypass the mock layer entirely:
```

### Verification
#### Manual
- [x] `sed -n '15,18p' deadcode/utils/base_test_case.py` → shows `def patch`
- [x] `sed -n '10p' deadcode/utils/base_test_case.py` → `class BaseTestCase(TestCase):`
- [x] `sed -n '37p;57p' deadcode/utils/base_test_case.py` → line 37 is `def setUp`
- [x] `sed -n '59p;85p' deadcode/utils/base_test_case.py` → line 59 is `def assertFiles`
- [x] `sed -n '87p;96p' deadcode/utils/base_test_case.py` → line 87 is `def assertUpdatedFiles`
- [x] `rg -n 'base_test_case.py:(10|15-18|23-35|37-57|59-85|87-96)' docs/testing-and-tooling.md` → all six anchors present
- [x] `! rg -n 'base_test_case.py:(10-93|37-54|56-82|84-93)' docs/testing-and-tooling.md` → no stale spans remain (command exits 0 because rg found nothing → use `rg -n ... ; test $? -eq 1`)
- [x] `rg -n 'patch\(path\)' docs/testing-and-tooling.md` → `patch()` helper documented
- [x] `rg -n 'three tiers' docs/testing-and-tooling.md` → tier framing present

---

## Phase 3: Deterministic Testing — sorted-walk anchor

### Changes

#### 1. Correct the sorted-walk anchor on line 73
**File**: `docs/testing-and-tooling.md`
**Action**: modify

`deadcode/actions/find_python_filenames.py:25` → `deadcode/actions/find_python_filenames.py:24`.

### Verification
#### Manual
- [x] `sed -n '24p' deadcode/actions/find_python_filenames.py` → contains `paths += sorted(str(p) for p in path.glob('*'))`
- [x] `rg -n 'find_python_filenames.py:24' docs/testing-and-tooling.md` → present
- [x] `rg -n 'find_python_filenames.py:25' docs/testing-and-tooling.md ; test $? -eq 1` → stale `:25` gone

---

## Phase 4: Build and Check Commands — Makefile/Justfile anchors

### Changes

#### 1. Correct all eight Makefile recipe anchors (lines 114-121)
**File**: `docs/testing-and-tooling.md`
**Action**: modify

| Recipe | Old anchor | New anchor |
|--------|-----------|-----------|
| `test` | `Makefile:18-19` | `Makefile:20-21` |
| `lint` | `Makefile:21-22` | `Makefile:23-24` |
| `format` | `Makefile:37-38` | `Makefile:39-40` |
| `mypy` | `Makefile:27-28` | `Makefile:29-30` |
| `deadcode` | `Makefile:30-31` | `Makefile:32-33` |
| `audit` | `Makefile:40-41` | `Makefile:42-43` |
| `check` | `Makefile:3` | `Makefile:5` |
| `fix` | `Makefile:4` | `Makefile:6` |

#### 2. Cite Justfile anchors and note the divergence
**File**: `docs/testing-and-tooling.md`
**Action**: modify

In the `### Justfile Recipes` section, add the `Justfile:10-11` anchor to the
`test` bullet (line 127) and `Justfile:34` to the `check` bullet (line 130).
Replace the closing paragraph (line 133) to keep the both-runners-equivalent
prose and add the divergence note (design Patterns-to-Follow):

```markdown
Both `Makefile` and `Justfile` run `pytest -n "$(nproc --ignore=1)"`, keeping parallel behavior identical across runners. They diverge on extras: the `Makefile` `check` adds `audit` (`pip-audit`) and a self-`deadcode` run, while the `Justfile` `check` adds an explicit `check-complexity` gate (`ruff check --select C901`).
```

### Verification
#### Manual
- [x] `sed -n '5p;6p;20,21p;23,24p;29,30p;32,33p;39,40p;42,43p' Makefile` → each line matches its claimed recipe (`check:`, `fix:`, `test:`/pytest, `lint:`/ruff check, `mypy:`/mypy, `deadcode:`/self-run, `format:`/ruff format, `audit:`/pip-audit)
- [x] `rg -n 'Makefile:(5|6|20-21|23-24|29-30|32-33|39-40|42-43)' docs/testing-and-tooling.md` → all eight present
- [x] `rg -n 'Makefile:(3|4|18-19|21-22|27-28|30-31|37-38|40-41)' docs/testing-and-tooling.md ; test $? -eq 1` → no stale Makefile anchors
  <!-- Note: grep pattern `Makefile:3` is a substring match that hits `Makefile:32-33`; likewise `Makefile:4` hits `Makefile:42-43`. No actual stale anchors present — this is a false-positive from the regex, not a real stale anchor. -->
- [x] `sed -n '34p' Justfile` → `check: check-format check-lint check-complexity check-typecheck test`
- [x] `rg -n 'Justfile:(10-11|34)' docs/testing-and-tooling.md` → both Justfile anchors present
- [x] `rg -n 'check-complexity' docs/testing-and-tooling.md` → divergence note present

---

## Phase 5: Configuration Files — fix anchor, drop filler, complete ignore set

### Changes

#### 1. Remove the entry-point blank-line filler (line 139)
**File**: `docs/testing-and-tooling.md`
**Action**: modify

Drop the parenthetical filler. Change line 139 from:

```markdown
- **Entry point** (`pyproject.toml:38`): `deadcode = "deadcode.cli:main"` — defines the CLI command (the entry is on line 37; line 38 is the blank that follows)
```

to:

```markdown
- **Entry point**: `deadcode = "deadcode.cli:main"` — defines the CLI command
```

(Removing the line ref here rather than re-verifying it: design Decision 4 says
soften to what is verifiable, and the meta-note about the blank line is the
flagged filler. The remaining entry-point fact needs no anchor.)

#### 2. Correct the pytest `addopts` anchor (line 140)
**File**: `docs/testing-and-tooling.md`
**Action**: modify

`pyproject.toml:209` → `pyproject.toml:215`.

#### 3. Complete the `tests/*` ruff ignore set (lines 173-177)
**File**: `docs/testing-and-tooling.md`
**Action**: modify

Add the missing `SLF001` bullet to the per-file ignores list (after `ANN201` on
line 176, before `D` on line 177):

```markdown
  - `SLF001` — tests legitimately read private members (e.g. `visitor._log`)
```

#### 4. Remove the unverifiable "tracked and validated" claim (line 179)
**File**: `docs/testing-and-tooling.md`
**Action**: delete

Delete line 179 entirely:

```markdown
Every ignore entry is tracked and validated: if a rule reaches zero violations it is removed from the list, keeping only active policies.
```

### Verification
#### Manual
- [x] `sed -n '215p' pyproject.toml` → `addopts = "--cov=deadcode --no-cov-on-fail --cov-fail-under=95.0"`
- [x] `sed -n '153,160p' pyproject.toml` → lists `S101, PT009, ANN201, SLF001, D`
- [x] `rg -n 'pyproject.toml:215' docs/testing-and-tooling.md` → present
- [x] `rg -n 'SLF001' docs/testing-and-tooling.md` → present
- [x] `rg -n 'entry is on line 37|tracked and validated|pyproject.toml:209' docs/testing-and-tooling.md ; test $? -eq 1` → all filler/stale gone

---

## Phase 6: Full-reference audit + no-regression gate

### Changes

**File**: `docs/testing-and-tooling.md` (read-only audit)
**Action**: none beyond fixes surfaced by the sweep

Extract every `file:line` citation remaining in the doc and confirm each resolves
to the claimed symbol. Fix any straggler discovered by the sweep (none expected
after Phases 1-5).

### Verification
#### Automated
- [x] `make check` passes (or `just check`) — no code touched, no regression
- [x] `git -C /home/niekas/tools/deadcode diff --name-only` → lists only `docs/testing-and-tooling.md`
  <!-- Note: BACKLOG.md and lifecycle_state.yml also appear — those are harness-managed files, not doc changes. -->

#### Manual
- [x] Sweep refs: `rg -no '[A-Za-z_./]+\.(py|toml):[0-9-]+' docs/testing-and-tooling.md` → for each printed `file:line`, ran `sed -n '<line>p' <file>` and confirmed each shows the claimed symbol: base_test_case.py:10 (class), :15-18 (patch), :23-35 (_read_file_side_effect), :37-57 (setUp), :59-85 (assertFiles), :87-96 (assertUpdatedFiles); test_code_item.py:7 (class TestCodeItem); find_python_filenames.py:24 (sorted glob); pyproject.toml:215 (addopts)
- [x] Spot-check anchors resolve:
  - `sed -n '10p' deadcode/utils/base_test_case.py` → class def
  - `sed -n '24p' deadcode/actions/find_python_filenames.py` → sorted glob
  - `sed -n '20,21p' Makefile` → `test:` recipe
  - `sed -n '215p' pyproject.toml` → `addopts`
- [x] `! rg -n 'base_test_case.py:(10-93|37-54|56-82|84-93)|find_python_filenames.py:25|Makefile:(3|4|18-19|21-22|27-28|30-31|37-38|40-41)|pyproject.toml:209' docs/testing-and-tooling.md` → no known-stale anchor remains (exit 1 confirmed)

---

## Testing Checkpoints

After each phase the following should hold (useful for resuming mid-task):

1. **Phase 1**: doc states both class-naming forms, the `test_*` method rule, the
   `unittest`-only/no-`conftest.py` fact, `__init__.py` placement, and mixed
   `test_deadcode.py`. `find`/`rg` checks pass.
2. **Phase 2**: every `base_test_case.py` anchor resolves to its symbol; `patch()`
   documented; three-tier framing present; no stale spans remain.
3. **Phase 3**: sorted-walk cite reads `find_python_filenames.py:24`.
4. **Phase 4**: all eight `Makefile` recipe anchors correct; no old anchors remain;
   Justfile anchors cited; Make/Just divergence noted.
5. **Phase 5**: `addopts` cite is `:215`; both filler claims gone; `tests/*` ignore
   set lists all five entries incl. `SLF001`.
6. **Phase 6**: every `file:line` in the doc resolves; `git diff` touches only the
   one doc file; `make check` / `just check` green.
