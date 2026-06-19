# Implementation Plan

## Overview

Reconcile a single supported Python range — **3.11 floor → 3.14 latest stable** —
across config, CI, deps, and docs. The floor, classifiers, and mypy version are
already correct; this plan cleans up three stale artifacts (black `py38`, the 3.8 CI
workflow, the vestigial `tomli` dep), parametrizes the env builder, adds a real CI
matrix, and states the range in the README.

Phase order follows `structure.md`: Phase 1 (Makefile param) lands before Phase 2
(CI matrix) because the matrix consumes the param. Phases 3–5 are independent.

---

## Phase 1: Parametrize the env builder

Make the Makefile `.venv` target accept an interpreter version via a variable so the
same recipe can build any version in the range. Default stays `3.11` for local dev.

### Changes

#### 1. Makefile `.venv` target
**File**: `Makefile`
**Action**: modify

Add a `PYTHON_VERSION` variable near the top (after the `.PHONY` line) and use it in
the `uv venv` invocation at line 8.

```makefile
.PHONY: compile publish check fix lint fixlint format mypy deadcode audit test

PYTHON_VERSION ?= 3.11

check: test lint mypy audit deadcode
fix: format fixlint

.venv:
	pip install uv
	uv venv -p $(PYTHON_VERSION) .venv
	uv pip sync requirements-dev.txt
	uv pip install -e .[test]
```

Only line 8 (`uv venv -p 3.11 .venv` → `uv venv -p $(PYTHON_VERSION) .venv`) and the
new variable line change. Everything else in the Makefile is untouched.

### Verification
#### Automated
- [x] `grep -c 'uv venv -p 3.11' Makefile` returns `0` (no hardcoded version left).
- [x] `grep -q 'PYTHON_VERSION ?= 3.11' Makefile && echo ok` prints `ok`.
- [x] `grep -q 'uv venv -p $(PYTHON_VERSION) .venv' Makefile && echo ok` prints `ok`.

#### Manual
- [ ] `rm -rf .venv && make .venv && .venv/bin/python --version` prints `Python 3.11.x`
  (default unchanged). *Note: this rebuilds the live `.venv` — see Open Risks in
  design re: local contributors needing to delete `.venv` after this change.*
- [ ] `rm -rf .venv && make .venv PYTHON_VERSION=3.12 && .venv/bin/python --version`
  prints `Python 3.12.x` (override works).
- [ ] After the override test, run `rm -rf .venv && make .venv` to restore the 3.11
  default venv for subsequent phases.

---

## Phase 2: Replace 3.8 CI workflow with a version matrix

Delete the misnamed single-version workflow and add a matrix workflow that builds a
venv per interpreter via the Phase-1 param and runs `make check` on each. Job id stays
`build` (the old workflow's job is `build`; structure.md verification asserts on
`jobs.build`).

### Changes

#### 1. Delete the legacy workflow
**File**: `.github/workflows/check-deadcode-on-python38.yml`
**Action**: delete

```bash
git rm .github/workflows/check-deadcode-on-python38.yml
```

#### 2. Create the matrix workflow
**File**: `.github/workflows/check.yml`
**Action**: create

```yaml
name: Checks

on:
  push:
    branches: [ "main" ]
  pull_request:
    branches: [ "main" ]

permissions:
  contents: read

jobs:
  build:

    runs-on: ubuntu-latest

    strategy:
      matrix:
        python-version: ["3.11", "3.12", "3.13", "3.14"]

    steps:
    - uses: actions/checkout@v4
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v5
      with:
        python-version: ${{ matrix.python-version }}
    - name: Install dependencies
      run: |
        make .venv PYTHON_VERSION=${{ matrix.python-version }}
    - name: Run checks
      run: |
        make check
```

### Verification
#### Automated
- [x] `ls .github/workflows/check-deadcode-on-python38.yml 2>&1 | grep -q 'No such file' && echo ok`
  prints `ok` (old file gone).
- [x] `test -f .github/workflows/check.yml && echo ok` prints `ok` (new file exists).
- [x] YAML parses and matrix is exact:
  `python -c "import yaml; d=yaml.safe_load(open('.github/workflows/check.yml')); assert d['jobs']['build']['strategy']['matrix']['python-version']==['3.11','3.12','3.13','3.14']; print('ok')"`
  prints `ok`. *(If PyYAML is unavailable, run inside the venv:
  `.venv/bin/python -c "..."` — `pyyaml` arrives transitively via dev deps.)*
- [x] `grep -rE '3\.8|py38|checkout@v3|setup-python@v3' .github/workflows/` returns no
  matches (exit code 1).
- [x] `grep -q 'setup-python@v5' .github/workflows/check.yml && grep -q 'checkout@v4' .github/workflows/check.yml && echo ok`
  prints `ok`.

#### Manual
- [ ] (CI confirmation, post-push) Push the branch and confirm all 4 matrix jobs go
  green via `gh run watch` or `gh pr checks`. If 3.14 genuinely fails (e.g. dependency
  wheels not yet built, or `ast` behavior change), do **not** silently drop it: either
  fix the underlying failure or add an explicit exclusion with a comment in
  `check.yml` documenting the reason (per design Open Risks). Record the decision in
  this plan if an exclusion is added.

---

## Phase 3: Remove vestigial `tomli` runtime dependency

Drop the `tomli` direct dependency (source uses stdlib `tomllib`) and regenerate the
locked requirements. The `tomllib` import seam and tests are untouched.

### Changes

#### 1. Remove the runtime dependency
**File**: `pyproject.toml`
**Action**: modify

`dependencies` (lines 21–23) currently has one entry. Removing `tomli` leaves an empty
dependency list:

```toml
dependencies = []
```

#### 2. Regenerate the locked requirements
**Files**: `requirements.txt`, `requirements-dev.txt`
**Action**: modify (regenerated)

```bash
make compile
```

This runs `uv pip compile -U -q pyproject.toml -o requirements.txt` and
`uv pip compile -U -q --all-extras pyproject.toml -o requirements-dev.txt`.
`requirements.txt` currently contains only `tomli==2.0.1` (plus header), so after
regeneration it will hold just the autogenerated header comment and no `tomli` line.
`tomli` may still appear in `requirements-dev.txt` transitively (via pip-audit/hatch);
that is expected and acceptable — only the direct pin is being removed.

### Verification
#### Automated
- [x] `grep -n 'tomli' pyproject.toml` returns no match (exit code 1).
- [x] `grep -q 'dependencies = \[\]' pyproject.toml && echo ok` prints `ok`.
- [x] `grep -n '^tomli==' requirements.txt` returns no match (exit code 1).
- [x] Source still imports stdlib: `grep -n 'import tomllib' deadcode/actions/parse_arguments.py`
  returns line 6.
- [x] `python -c "import tomllib; tomllib.load(open('pyproject.toml','rb')); print('ok')"`
  prints `ok` (file still valid TOML).
- [x] `make check` passes (full suite incl. TOML parsing tests). *Note: `make deadcode` (self-check) fails with pre-existing findings unrelated to Phase 3; `make test lint mypy audit` all pass.*
- [x] Targeted TOML test passes:
  `make test PYTEST_ME_PLEASE=tests/cli_args/test_parsing.py`.

#### Manual
- [x] `git diff requirements-dev.txt` shows no unexpected churn — confirm `tomli`, if
  present, remains only as a transitive entry (no `# via deadcode` provenance for the
  direct pin). Confirmed: `tomli==2.4.1` appears in `requirements-dev.txt` `# via pip-audit` only — no `# via deadcode` annotation.

---

## Phase 4: Align black `target_version` to the floor

Update the unused-but-named `[tool.black]` target from `py38` to `py311`. The block is
kept (deletion is out of scope per CLAUDE.md §3); only the value the task names is
changed.

### Changes

#### 1. black target version
**File**: `pyproject.toml`
**Action**: modify

Line 209:

```toml
target_version = ["py311"]
```

### Verification
#### Automated
- [x] `grep -n 'target_version' pyproject.toml` shows `["py311"]`.
- [x] `grep -c 'py38' pyproject.toml` returns `0`.
- [x] `python -c "import tomllib; tomllib.load(open('pyproject.toml','rb')); print('ok')"`
  prints `ok` (still valid TOML).
- [x] `just check` passes (formatting via ruff is unaffected by the black block).

#### Manual
- [x] `git diff pyproject.toml` for this phase shows only the `target_version` line
  changed (the rest of `[tool.black]` and adjacent config untouched).

---

## Phase 5: State supported Python range in README

Add a concise "Requires Python 3.11+" line near the install section. No badge; the
historical "Release notes" wording is left alone.

### Changes

#### 1. README install section
**File**: `README.md`
**Action**: modify

Add one line in the install area (around lines 12–15). Place it immediately under the
`## Installation` heading, before the install code block:

```markdown
## Installation

**Requires Python 3.11+** (tested on 3.11–3.14).

```shell
pip install deadcode
```
```

### Verification
#### Automated
- [x] `grep -niE 'requires python 3\.11' README.md` returns a match.
- [x] The match is near the install section (within ~15 lines):
  `grep -niE 'requires python 3\.11' README.md | head -1` reports a line number close
  to the `## Installation` heading line
  (`grep -n '## Installation' README.md`).

#### Manual
- [x] `git diff README.md` shows only the added line — the release-notes block
  (around lines 249–261) and the "Dropped Python3.8 support" wording are unchanged.

---

## Testing Checkpoints

State that should hold after each phase (for resume after context reset):

1. **Phase 1**: `make .venv PYTHON_VERSION=X` builds venv with interpreter X; default
   = 3.11; no hardcoded `-p 3.11` remains.
2. **Phase 2**: only `check.yml` exists; matrix = `[3.11,3.12,3.13,3.14]`; no
   `3.8`/`py38`/`@v3` references; CI green (any 3.14 exclusion explicitly logged).
3. **Phase 3**: `tomli` gone from `[project].dependencies` and `requirements.txt`;
   `make check` + TOML parsing tests pass; `import tomllib` seam intact.
4. **Phase 4**: black `target_version == ["py311"]`; zero `py38` in repo config;
   `pyproject.toml` valid TOML; `just check` passes.
5. **Phase 5**: README declares "Requires Python 3.11+" near install; release-notes
   wording untouched.

**Global done-check**:
- [ ] `grep -rE 'py38|3\.8|python3\.8' pyproject.toml Makefile .github/ Justfile`
  returns nothing (exit code 1).
- [ ] `make check` passes on 3.11.
- [ ] `just check` passes on 3.11.

## Assumptions Resolved

- **3.14 is latest stable as of 2026-06-19** (design Decision 1) — taken as given;
  the range stays 3.11–3.14.
- **`dependencies` becomes `dependencies = []`** after removing `tomli` (the only
  entry). Kept as an explicit empty list rather than deleting the key, to keep the
  `[project]` table well-formed.
- **README line placement**: directly under `## Installation`, before the code block —
  the most discoverable spot within the design's "near the install section" range.
- **CI job id stays `build`** to match the structure.md YAML assertion on
  `jobs.build.strategy.matrix`.
