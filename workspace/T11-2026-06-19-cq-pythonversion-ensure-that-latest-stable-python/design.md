# Design Discussion

## Current State

The `deadcode` project (v2.3.0, `pyproject.toml:3`) already declares a modern
Python floor, but three stale artifacts contradict it and CI does not actually
validate any supported version. Latest stable Python on 2026-06-19 is **3.14**
(released Oct 2025; 3.15 is not due until Oct 2026), and it is already listed in
the classifiers — so the task is *reconciliation*, not a floor bump.

Consistent on the 3.11 floor:
- `requires-python = ">= 3.11"` (`pyproject.toml:9`)
- Trove classifiers `3.11`–`3.14` (`pyproject.toml:16-19`)
- mypy `python_version = "3.11"` (`pyproject.toml:167`)
- Makefile `.venv` pins `uv venv -p 3.11 .venv` (`Makefile:8`)

Stale / contradictory:
- black `target_version = ["py38"]` (`pyproject.toml:209`) — and the `[tool.black]`
  block is unused; formatting is done by `ruff format` (`Justfile:13`, `Makefile:38`).
- The only CI workflow targets Python 3.8: `check-deadcode-on-python38.yml`
  (name `:4`, `python-version: "3.8"` `:23-25`), no `strategy.matrix`, uses
  outdated `checkout@v3`/`setup-python@v3`. It calls `make .venv` (`:28`), which
  itself forces 3.11 — so the 3.8 setup-python is inert and CI silently tests 3.11.
- `tomli>=2.0.1` is a declared runtime dependency (`pyproject.toml:22`,
  `requirements.txt:3`) but source imports stdlib `tomllib` unconditionally
  (`deadcode/actions/parse_arguments.py:6`), with no fallback. `tomli` is a
  backport only needed for <3.11 — vestigial under the 3.11 floor.
- README has no supported-versions statement; its only version note says "Dropped
  Python3.8 support … in v2.4.0" (`README.md:253`) while the package is v2.3.0.

No source/test code branches on interpreter version (research Q5). ruff has no
explicit `target-version`; it infers from `requires-python` (`pyproject.toml:62-73`).

## Desired End State

A single coherent supported range — **Python 3.11 (floor) through 3.14 (latest
stable)** — declared once and verified in CI across every version in the range.

Verification:
- `requires-python`, classifiers, and mypy `python_version` unchanged (already
  correct: floor 3.11, range to 3.14).
- No `py38`/`3.8` references remain in tooling config or CI.
- CI runs a `strategy.matrix` over `["3.11", "3.12", "3.13", "3.14"]`, each job
  building its venv with the matrix interpreter and passing `make check`.
- `tomli` no longer in `dependencies`; `requirements*.txt` regenerated; tests and
  `make check` still pass (tomllib seam unchanged).
- README states the supported Python range.
- `make check` and `just check` pass locally on 3.11.

## Patterns to Follow

- **Justfile is the canonical task runner** (CLAUDE.md §5). The Justfile `sync`
  recipe deliberately pins no interpreter and uses the ambient venv
  (`Justfile:6-8`); keep that — version selection is CI's job via the matrix.
- **Let ruff infer its target** from `requires-python` (`pyproject.toml:62-73`).
  Do not add an explicit `[tool.ruff] target-version` — matches current intent.
- **mypy checks against the floor.** `python_version = "3.11"` (`pyproject.toml:167`)
  is standard practice (type-check against the minimum supported); leave it.
- **TOML parsing seam.** stdlib `tomllib` at `parse_arguments.py:6`, single
  parse site `parse_pyproject_toml()` (`parse_arguments.py:220-221`); tests patch
  `deadcode.actions.parse_arguments.tomllib.load` (`tests/cli_args/test_parsing.py:13`).
  Do not change this seam — removing the `tomli` *dependency* does not touch it.
- **Makefile `.venv` is the authoritative env builder**; CI already reuses it via
  `make .venv` (`workflow:28`). Keep that contract — parametrize, don't bypass.

Patterns NOT to follow (stale): black `py38` (`pyproject.toml:209`), the 3.8 CI
workflow, and the `tomli` runtime dependency.

## Design Decisions

1. **Keep the 3.11 floor; treat 3.14 as the latest stable** — Do not bump
   `requires-python`. The range 3.11–3.14 is already declared in classifiers and
   is the "single up-to-date range" the task asks for. tomllib requires 3.11+, so
   the floor cannot drop. Assumption: 3.14 is latest stable as of 2026-06-19.

2. **Replace, not edit, the CI workflow with a matrix** — Rename
   `check-deadcode-on-python38.yml` → `check.yml`; add
   `strategy.matrix.python-version: ["3.11","3.12","3.13","3.14"]`; bump to
   `actions/checkout@v4` and `actions/setup-python@v5`. Rationale: the old name
   and 3.8 target are wrong, and a single hardcoded version cannot validate the
   range.

3. **Parametrize Makefile `.venv` with `PYTHON_VERSION ?= 3.11`** — Change
   `Makefile:8` to `uv venv -p $(PYTHON_VERSION) .venv`. CI passes
   `make .venv PYTHON_VERSION=${{ matrix.python-version }}` then `make check`.
   Keeps default local behavior (3.11) while making the matrix meaningful.
   Rejected alternative: bypassing make with raw `uv venv` in CI — duplicates the
   env-build contract.

4. **Fix black `target_version` to `["py311"]`** — Keep the `[tool.black]` block
   but align it to the floor rather than deleting it. Rationale: deletion of
   unused config is out of scope per CLAUDE.md §3 ("mention, don't delete"); the
   task explicitly lists black target-version as a value to reconcile, so updating
   the value (not removing the block) is the minimal in-scope change.

5. **Remove the vestigial `tomli` runtime dependency** — Drop `"tomli>=2.0.1"`
   from `pyproject.toml:21-23` and regenerate `requirements.txt` /
   `requirements-dev.txt` via `make compile`. Rationale: `tomli` is a pre-3.11
   backport that the source never imports; it is a direct relic of older-version
   support and removing it is part of reconciling to the 3.11+ range.

6. **State supported versions in README** — Add a concise "Requires Python
   3.11+" line near the install section (`README.md:12-15`). Do not add a badge
   and do not edit the historical "Release notes" wording.

## What We're NOT Doing

- Not bumping `requires-python` above 3.11 or dropping any version from 3.11–3.14.
- Not deleting the `[tool.black]` block, the unused isort config, or any other
  pre-existing dead config (only aligning the value the task names).
- Not fixing the package-version vs README "v2.4.0 release note" mismatch — that
  is release bookkeeping, not Python-version reconciliation.
- Not changing the `tomllib` import seam, source logic, or tests.
- Not adding an explicit ruff `target-version` (inference is intentional).
- Not migrating Makefile→Justfile or consolidating the two runners.

## Open Risks

- **Matrix CI on 3.14 may surface real failures** (e.g. dependency wheels not yet
  built for 3.14, or stdlib `ast` behavior changes the visitor relies on). If a
  version genuinely fails, decide per-version whether to fix or exclude — do not
  silently drop it; log the exclusion. This is the most likely source of churn.
- **`uv venv -p 3.14`** requires uv to fetch/locate a 3.14 interpreter in CI;
  `actions/setup-python@v5` must provide it (3.14 is released, so expected OK).
- **Removing `tomli`** changes the resolved dependency tree; `make compile` output
  diff should be reviewed to confirm nothing transitive depended on the *direct*
  pin (research: `tomli` still arrives transitively via pip-audit/hatch in dev,
  `requirements-dev.txt:173-180`, so dev tooling is unaffected).
- **The live `.venv`** may have been created with an unknown interpreter
  (research Open Area); CI builds fresh per-matrix, but local contributors may
  need to delete `.venv` after the Makefile change.
