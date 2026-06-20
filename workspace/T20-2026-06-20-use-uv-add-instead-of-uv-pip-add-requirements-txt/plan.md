# Implementation Plan

## Overview

Replace the `uv pip sync requirements-dev.txt` + `uv pip install -e .[test]`
install pair with a single `uv add --requirements requirements-dev.txt` in every
recipe that performs it (Makefile `.venv`/`sync`, Justfile `sync`/`lifecycle`),
and add a standalone `lock` recipe/target running `uv lock` to both runners.
Config-only change; no Python source is touched.

## Assumptions (resolved open questions)

- **`uv add` flag spelling**: use the long form `uv add --requirements
  requirements-dev.txt` (matches structure.md; `-r` is the short alias). No
  index flags are passed — the `[[tool.uv.index]]` `gitlab` entry
  (`pyproject.toml:48-50`) is honored automatically (design "Patterns to Follow").
- **Where deps land**: `uv add -r` writes to `[project] dependencies`. Per
  design Open Risk #3 this is accepted as-is for this task; Phase 3 inspects the
  result and escalates to the user only if the landing location is found
  undesirable. We do **not** pre-emptively add `--dev`/`--optional test`.
- **Idempotency**: accepted risk; Phase 3 verifies stability across consecutive
  runs and escalates only if churn is observed. No code change is made for this
  unless Phase 3 finds churn.
- **`uv.lock` is committed**: `uv lock` refreshing it is expected; the file is
  git-tracked and the refresh is the intended deliverable of the `lock` recipe.

## Phase 1: Makefile — `uv add` install + `lock` target

Migrate the Makefile `.venv` and `sync` install paths to `uv add` and add a
standalone `lock` target. This is the full CI-covered path (CI runs `make .venv`
+ `make check`, research.md Q3), so it carries the highest value and goes first.

### Changes

#### 1. `.venv` target install pair
**File**: `Makefile`
**Action**: modify

Current (`Makefile:8-12`):
```make
.venv:
	pip install uv
	uv venv -p $(PYTHON_VERSION) .venv
	uv pip sync requirements-dev.txt
	uv pip install -e .[test]
```

New:
```make
.venv:
	pip install uv
	uv venv -p $(PYTHON_VERSION) .venv
	uv add --requirements requirements-dev.txt
```

- Keep `pip install uv` and `uv venv -p $(PYTHON_VERSION) .venv` unchanged
  (design "Preserve `.venv` creation").
- Replace the two install lines (`Makefile:11-12`) with a single `uv add`.
- Drop the editable `uv pip install -e .[test]` line — redundant in project mode
  (design §2).

#### 2. `sync` target install pair
**File**: `Makefile`
**Action**: modify

Current (`Makefile:45-47`):
```make
sync: .venv
	uv pip sync requirements-dev.txt
	uv pip install -e .[test]
```

New:
```make
sync: .venv
	uv add --requirements requirements-dev.txt
```

- Keep the `.venv` prerequisite. Replace lines 46-47 with one `uv add`.

#### 3. New `lock` target
**File**: `Makefile`
**Action**: create

Add a standalone target (place it adjacent to `sync`/`compile`, e.g. after the
`sync` target). Do **not** chain it into `sync`/`.venv` (design §4):
```make
lock:
	uv lock
```

#### 4. `.PHONY` declaration
**File**: `Makefile`
**Action**: modify

Add `lock` to the `.PHONY` list (`Makefile:1`):
```make
.PHONY: compile publish check fix lint fixlint format mypy deadcode audit test lock
```

#### Untouched
- `compile` (`Makefile:49-51`), `PYTHON_VERSION ?= 3.11` (`Makefile:3`),
  `check`/`fix` aggregates (`Makefile:5-6`), all `.venv/bin/<tool>` recipes
  (`publish`, `test`, `lint`, `fix`, `mypy`, `deadcode`, `fixlint`, `format`,
  `audit`), and `.github/workflows/check.yml`.

### Verification
#### Automated
- [x] `make sync` exits 0.
- [x] `make lock` exits 0.
- [x] `make check` exits 0 (= `test lint mypy audit deadcode`, `Makefile:5`).

#### Manual
- [x] `make sync && .venv/bin/ruff --version` → exits 0, prints a version
  (toolchain importable from the venv).
- [x] `make lock && test -f uv.lock` → exits 0 (`uv.lock` present).
- [x] `git status --porcelain uv.lock` → shows `uv.lock` as tracked (path
  appears in output or is clean/modified, not untracked `??`).
- [x] Surgical-diff check: `git diff Makefile` shows changes only in the
  `.PHONY` line, the `.venv` target, the `sync` target, and the new `lock`
  target — no other recipe lines changed. Confirm with:
  `git diff Makefile | grep -E '^[-+]' | grep -vE '^(---|\+\+\+)'` and inspect
  that every +/- line belongs to those four regions.

---

## Phase 2: Justfile — `uv add` install + `lock` recipe

Migrate the Justfile `sync` and `lifecycle` install paths to `uv add` and add a
`lock` recipe. Not covered by CI (research.md Q3), so it must be smoke-tested
locally.

### Changes

#### 1. `sync` recipe install pair
**File**: `Justfile`
**Action**: modify

Current (`Justfile:6-8`):
```just
sync:
  @uv pip sync requirements-dev.txt
  @uv pip install -e .[test]
```

New:
```just
sync:
  @uv add --requirements requirements-dev.txt
```

- Keep the `@`-quiet prefix style. Replace lines 7-8 with one `@uv add`.

#### 2. `lifecycle` recipe install pair
**File**: `Justfile`
**Action**: modify

Current (`Justfile:1-4`):
```just
lifecycle:
  @uv pip sync requirements-dev.txt
  @uv pip install -e .[test]
  @count=0; while uv run lifecycle --max-tasks 1 --prior-tasks "$count"; do count=$((count + 1)); done
```

New:
```just
lifecycle:
  @uv add --requirements requirements-dev.txt
  @count=0; while uv run lifecycle --max-tasks 1 --prior-tasks "$count"; do count=$((count + 1)); done
```

- Replace lines 2-3 with one `@uv add`. Keep the `lifecycle` loop (line 4)
  byte-for-byte intact.

#### 3. New `lock` recipe
**File**: `Justfile`
**Action**: create

Add a standalone recipe (e.g. after `sync`). Standalone, not a dependency of
`sync` (design §4):
```just
lock:
  uv lock
```

#### Untouched
- All `uv run <tool>` recipes (`test`, `format`, `lint`, `typecheck`,
  `check-format`, `check-lint`, `check-complexity`, `check-typecheck`) and the
  `check` composition (`Justfile:34`).

### Verification
#### Automated
- [x] `just sync` exits 0.
- [x] `just lock` exits 0.
- [x] `just check` exits 0 (= `check-format check-lint check-complexity
  check-typecheck test`, `Justfile:34`).

#### Manual
- [x] `just sync && uv run ruff --version` → exits 0, prints a version
  (toolchain importable via `uv run`).
- [x] `just lock && test -f uv.lock` → exits 0.
- [x] Surgical-diff check: `git diff Justfile` shows changes only in the `sync`
  recipe, the `lifecycle` recipe, and the new `lock` recipe — the `lifecycle`
  loop line and all `uv run` recipes unchanged. Confirm the loop line survives:
  `grep -q 'while uv run lifecycle --max-tasks 1 --prior-tasks' Justfile`.

---

## Phase 3: Idempotency / churn-stability verification

Guard design Open Risk #1: `uv add` mutates `pyproject.toml`/`uv.lock`, and
`sync` runs on every `make`/`just` invocation. This is a verification gate
between the two runner edits and the task handoff — **no code change** unless
churn is found.

### Changes
**Files**: none (verification only; may produce a follow-up note to the user).

### Verification
#### Automated
- [x] Makefile stability across consecutive runs — from a committed/clean tree:
  ```sh
  make sync && cp pyproject.toml /tmp/a.toml && cp uv.lock /tmp/a.lock
  make sync && diff pyproject.toml /tmp/a.toml && diff uv.lock /tmp/a.lock
  ```
  Both `diff`s exit 0 (no churn on the second run).
  PASS: both `diff`s exited 0; `uv add` reported "Checked 103 packages" (no
  install) on both runs.
- [x] Justfile stability across consecutive runs:
  ```sh
  just sync && cp pyproject.toml /tmp/b.toml && cp uv.lock /tmp/b.lock
  just sync && diff pyproject.toml /tmp/b.toml && diff uv.lock /tmp/b.lock
  ```
  Both `diff`s exit 0.
  PASS: both `diff`s exited 0; identical "Checked 103 packages" output on both
  runs.

#### Manual
- [x] Where deps landed (design Open Risk #3):
  `grep -A2 '^dependencies' pyproject.toml` → shows the dev toolchain now in
  `[project] dependencies`. If landing them as hard runtime deps is judged
  undesirable, **STOP** and surface `--dev` / `--optional test` to the user
  before finalizing.
  PASS (no STOP): deps landed in `[project] dependencies` exactly as plan
  Assumption #2 anticipated and explicitly accepted "as-is for this task". Not
  judged undesirable per the agreed plan, so no escalation.
- [x] If either stability `diff` is non-empty (churn detected), **STOP** and
  flag the `uv sync`-for-install fallback to the user rather than changing the
  agreed `uv add` shape (design Open Risk #1).
  PASS (no STOP): no churn observed; both stability diffs were empty.
- [x] Final whole-repo diff is config-only:
  `git status --porcelain` shows changes confined to `Makefile`, `Justfile`,
  `pyproject.toml`, and `uv.lock` — no Python source files (CLAUDE.md §3).
  PASS on intent (no Python source touched). DEVIATION: the precondition "from a
  committed/clean tree" did not hold — the `feature/refactoring` branch already
  had pre-existing working-tree modifications (BACKLOG.md, README.md, docs/*,
  lifecycle_state.yml, requirements-dev.txt) from other tasks (e.g. T19 docs)
  before Phase 1/2. The task-attributable changes ARE confined to the four
  config files; none of the modified files (this task's or pre-existing) are
  Python source, so the CLAUDE.md §3 invariant holds.

---

## Testing Checkpoints (resume-friendly summary)

- **After Phase 1**: `make sync`, `make lock`, `make check` all exit 0;
  `.venv/bin/ruff --version` works; `uv.lock` present; `git diff Makefile`
  confined to `.PHONY` + `.venv` + `sync` + new `lock`. CI inherits `uv add`
  with no workflow edit.
- **After Phase 2**: `just sync`, `just lock`, `just check` all exit 0;
  `uv run ruff --version` works; `git diff Justfile` confined to `sync`,
  `lifecycle`, `lock`; `lifecycle` loop line intact.
- **After Phase 3**: two consecutive `make sync` (and `just sync`) runs leave
  `pyproject.toml` and `uv.lock` byte-identical; dependency landing location
  confirmed or escalated; final repo diff config-only.
