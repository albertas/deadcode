# Structure Outline

## Approach

Replace the `uv pip sync requirements-dev.txt` + `uv pip install -e .[test]`
install pair with a single `uv add --requirements requirements-dev.txt` in every
recipe that performs it, and add a standalone `lock` recipe/target running
`uv lock` to each runner. Slices are **per build runner** (Makefile, then
Justfile): each crosses that runner's install path + new lock recipe end-to-end
and is verifiable in isolation via its own CLI. Makefile goes first because CI
exercises only the Makefile (research.md Q3), so it carries the highest value and
is the CI entry point.

There is no database/service/API/UI here — the "layers" a slice crosses are the
recipes within one runner (install path, the new lock recipe, and the recipe's
consumers like `check`).

---

## Phase 1: Makefile — `uv add` install + `lock` target

Migrate the Makefile's `.venv` and `sync` install paths to `uv add` and add a
standalone `lock` target. Delivers the full CI-covered path end-to-end.

**Files**: `Makefile`

**Key changes** (recipe-body edits, not function signatures):
- `.venv` target (`Makefile:8-12`): keep `pip install uv` and
  `uv venv -p $(PYTHON_VERSION) .venv`; replace lines 11-12 with
  `uv add --requirements requirements-dev.txt`. Drop the editable
  `uv pip install -e .[test]` line (redundant in project mode — design §2).
- `sync` target (`Makefile:45-47`): replace lines 46-47 with the same single
  `uv add --requirements requirements-dev.txt`.
- New target `lock:` running `uv lock` (standalone, not chained into
  `sync`/`.venv` — design §4).
- `.PHONY` line (`Makefile:1`): add `lock`.
- Untouched: `compile` (`Makefile:49-51`), `PYTHON_VERSION ?= 3.11`, all
  `.venv/bin/<tool>` recipes, CI workflow.

**Verify**:
- `make sync` exits 0 and leaves the toolchain importable —
  `.venv/bin/ruff --version` exits 0.
- `make lock` exits 0 and `uv.lock` exists/refreshes — `test -f uv.lock`
  passes; `git status --porcelain uv.lock` shows it tracked.
- `make check` (= `test lint mypy audit deadcode`, `Makefile:5`) exits 0.
- Surgical-diff check: `git diff Makefile` touches only the four targeted
  regions above (`.PHONY`, `.venv`, `sync`, new `lock`); no other recipe lines
  change.

---

## Phase 2: Justfile — `uv add` install + `lock` recipe

Migrate the Justfile's `sync` and `lifecycle` install paths to `uv add` and add a
`lock` recipe. Not covered by CI (research.md Q3) — must be smoke-tested locally.

**Files**: `Justfile`

**Key changes**:
- `sync` recipe (`Justfile:6-8`): replace lines 7-8 with one
  `@uv add --requirements requirements-dev.txt` (keep the `@`-quiet prefix style).
- `lifecycle` recipe (`Justfile:1-4`): replace lines 2-3 with the same
  `@uv add --requirements requirements-dev.txt`; keep the
  `uv run lifecycle --max-tasks 1 --prior-tasks "$count"` loop (line 4) intact.
- New recipe `lock:` running `uv lock`.
- Untouched: all `uv run <tool>` recipes and the `check` composition
  (`Justfile:34`).

**Verify**:
- `just sync` exits 0; `uv run ruff --version` exits 0 (toolchain importable via
  `uv run`).
- `just lock` exits 0; `test -f uv.lock` passes.
- `just check` (= `check-format check-lint check-complexity check-typecheck
  test`, `Justfile:34`) exits 0.
- Surgical-diff check: `git diff Justfile` touches only `sync`, `lifecycle`, and
  the new `lock` recipe.

---

## Phase 3: Idempotency / churn-stability verification

Guard Open Risk #1 (`uv add` mutates `pyproject.toml`/`uv.lock` on every run, and
`sync` runs on every `make`/`just` invocation). No code change unless churn is
found; this is a checkpoint between the two sensitive runner edits and the task
handoff.

**Files**: none (verification only; may produce a follow-up note).

**Verify** (each is an unattended scripted assertion):
- Stability across consecutive runs:
  `git stash --include-untracked` to a clean tree (or commit Phases 1-2), then
  ```
  make sync && cp pyproject.toml /tmp/a.toml && cp uv.lock /tmp/a.lock
  make sync && diff pyproject.toml /tmp/a.toml && diff uv.lock /tmp/a.lock
  ```
  Both `diff`s must exit 0 (no churn on the second run). Repeat for `just sync`.
- Where deps landed (Open Risk #3): inspect `pyproject.toml` after migration —
  `grep -A2 '^dependencies' pyproject.toml` shows the dev toolchain now in
  `[project] dependencies`. If landing them as hard runtime deps is undesirable,
  STOP and surface `--dev` / `--optional test` to the user before proceeding
  (design Open Risks).
- If either `diff` is non-empty (churn), STOP and flag the `uv sync`-for-install
  fallback to the user rather than changing the agreed shape (design Open Risk #1).

---

## Testing Checkpoints

Resume-friendly summary of what must hold after each phase:

- **After Phase 1**: `make sync`, `make lock`, `make check` all exit 0;
  `.venv/bin/ruff --version` works; `uv.lock` present; `git diff Makefile`
  confined to the 4 targeted regions. CI (which runs `make .venv` + `make check`)
  now inherits `uv add` with no workflow edit.
- **After Phase 2**: `just sync`, `just lock`, `just check` all exit 0;
  `uv run ruff --version` works; `git diff Justfile` confined to `sync`,
  `lifecycle`, `lock`.
- **After Phase 3**: Two consecutive `make sync` (and `just sync`) runs leave
  `pyproject.toml` and `uv.lock` byte-identical; dependency landing location
  confirmed/escalated. Final `git diff` touches only `Makefile` and `Justfile`
  recipe lines plus the two new `lock` recipes (design Verification, CLAUDE.md §3).

**Note on slicing**: the change is inherently small and config-only, so the
slices are thin. Phases 1 and 2 are independently valuable (each runner works on
its own); Phase 3 is a verification gate, not new functionality. The single item
that cannot be sliced "vertically" in the database/UI sense is the lock recipe —
it is bundled with its runner's install slice so each runner is delivered and
testable as a unit.
