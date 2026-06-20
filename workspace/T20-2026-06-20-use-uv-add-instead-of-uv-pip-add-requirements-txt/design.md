# Design Discussion

## Current State

The repo manages dependencies through uv's **pip-compatibility interface** plus
`uv venv`/`uv run`, not uv's project workflow. The single source of dependency
truth is `pyproject.toml`; the pinned `requirements*.txt` files are generated
artifacts, and `uv.lock` exists but is essentially orphaned.

- **`pyproject.toml`**: runtime `dependencies = []` (`pyproject.toml:21`); the
  whole toolchain lives in `[project.optional-dependencies].test`
  (`pyproject.toml:23-34`). A custom `gitlab` index is declared
  (`pyproject.toml:48-50`) and governs resolution.
- **Makefile** (`Makefile`):
  - `.venv` target (`Makefile:8-12`): `pip install uv` → `uv venv -p
    $(PYTHON_VERSION) .venv` (default `3.11`, `Makefile:3`) →
    `uv pip sync requirements-dev.txt` → `uv pip install -e .[test]`.
  - `sync` target (`Makefile:45-47`): repeats the same two-line install pair.
  - `compile` target (`Makefile:49-51`): `uv pip compile ... -o requirements.txt`
    and `... --all-extras ... -o requirements-dev.txt`.
  - Tool recipes call `.venv/bin/<tool>` directly (`Makefile:21,24,30,33,43`).
- **Justfile** (`Justfile`):
  - `sync` recipe (`Justfile:6-8`): the same `uv pip sync requirements-dev.txt`
    + `uv pip install -e .[test]` pair. No `uv venv`, no Python pin.
  - `lifecycle` recipe (`Justfile:1-4`): same install pair, then a
    `uv run lifecycle` loop.
  - Every other recipe depends on `sync` and runs tools via `uv run`
    (`Justfile:10-34`).
- **`uv.lock`**: a full project lockfile (`uv.lock:1-3`) **not referenced by any
  recipe or CI command**; read only implicitly by `uv run`. No `uv lock`
  invocation exists anywhere.
- **`requirements.txt`** (runtime) is generated but has **no consumer**; only
  `requirements-dev.txt` is consumed (research.md Q2).
- **CI** (`.github/workflows/check.yml`): runs `make .venv
  PYTHON_VERSION=...` then `make check` across Python 3.11–3.14. CI exercises
  **only the Makefile**, never the Justfile (research.md Q3).

Neither file invokes `uv add`, `uv lock`, or project-mode `uv sync` today
(research.md Q1, cross-cutting observations).

## Desired End State

Both build runners adopt uv's project workflow for dependency installation and
locking:

1. The `uv pip sync requirements-dev.txt` + `uv pip install -e .[test]` pair is
   replaced by **`uv add` sourcing the existing `requirements-dev.txt`** in
   every recipe that performs it: Makefile `.venv` (`Makefile:11-12`) and `sync`
   (`Makefile:46-47`); Justfile `sync` (`Justfile:7-8`) and `lifecycle`
   (`Justfile:2-3`).
2. A new **`lock`** recipe/target running `uv lock` is added to both files.

**Verification:**
- `make sync` and `just sync` complete and leave the toolchain importable
  (e.g. `uv run ruff --version` / `.venv/bin/ruff --version` succeed).
- `make lock` / `just lock` produce/refresh `uv.lock` with no error.
- `make check` (CI's entry point) still passes across Python 3.11–3.14.
- `git diff` touches only the targeted recipe lines plus the two new `lock`
  recipes — no incidental edits (CLAUDE.md §3).

## Patterns to Follow

- **Source only `requirements-dev.txt`.** It is the only requirements file with
  a consumer; `requirements.txt` is runtime-empty and unreferenced
  (`requirements.txt:1-2`, research.md Q2). Match the existing single-file usage
  rather than globbing both.
- **Honor the custom index.** `[[tool.uv.index]]` `gitlab`
  (`pyproject.toml:48-50`) is respected automatically by `uv add`/`uv lock`; do
  not pass index flags on the command line.
- **Keep each runner's existing tool-execution style.** Makefile uses
  `.venv/bin/<tool>` (`Makefile:21`); Justfile uses `uv run <tool>`
  (`Justfile:11`). The migration touches install/lock only, not execution.
- **Preserve `.venv` creation in the Makefile.** `uv venv -p $(PYTHON_VERSION)`
  (`Makefile:10`) stays — Makefile recipes shell out to `.venv/bin`, so the
  venv must exist (research.md Q6).
- **Pattern NOT to follow:** do not wire `uv lock` into `.venv`/`sync` install
  paths or replace `sync` with project-mode `uv sync`. The task asks for `uv
  add` + a separate `uv lock` recipe; keep them distinct.

## Design Decisions

1. **Replacement command — `uv add --requirements requirements-dev.txt`**:
   Faithful to the task's "uv add (sourcing the existing requirements*.txt)".
   `uv add` resolves, records the deps in `pyproject.toml`, updates `uv.lock`,
   and installs into the environment in one step.
2. **Drop the editable `-e .[test]` line**: In uv project mode the current
   project is installed automatically on `uv add`/`uv run`/`uv sync`, so the
   explicit editable install becomes redundant. Removing it is the orphan
   cleanup that the replacement directly causes (CLAUDE.md §3).
3. **Source `requirements-dev.txt`, not `requirements.txt`**: `requirements.txt`
   has no package lines and no consumer (research.md Q2); adding it would be a
   no-op. Documented here so the `*` glob in the task is not read literally.
4. **`uv lock` as a standalone recipe**: Add `lock:` to the Makefile
   (`.PHONY`) and a `lock:` recipe to the Justfile, each running `uv lock`.
   Standalone (not chained into `sync`) to stay surgical and match the task's
   "add a uv lock command/recipe".
5. **Keep `compile` (`Makefile:49-51`) for now**: `requirements-dev.txt` remains
   the input to `uv add`, so the recipe that regenerates it stays. Removing the
   requirements-file flow entirely is out of scope (see below).
6. **CI left untouched**: `check.yml` calls `make .venv` + `make check`; since
   `.venv` is edited in place, CI inherits the new behavior with no workflow
   change (research.md Q3).
7. **Python-version pin unchanged**: `PYTHON_VERSION ?= 3.11` (`Makefile:3`) and
   the matrix in CI are untouched; `uv add`/`uv lock` honor
   `requires-python = ">= 3.11"` (`pyproject.toml:9`).

## What We're NOT Doing

- Not deleting `requirements.txt` / `requirements-dev.txt` or removing the
  `compile` recipe — the requirements file stays as the `uv add` source.
- Not migrating tool execution from `.venv/bin/<tool>` (Makefile) or `uv run`
  (Justfile) to anything else.
- Not unifying the divergent `check` compositions between the two runners
  (research.md Q6) — out of scope.
- Not adding `[tool.uv]` config beyond what exists, and not changing the
  `gitlab` index.
- Not editing `.github/workflows/check.yml`.
- Not adding a `.python-version` file (none exists today; research.md Open Areas).

## Open Risks

- **`uv add` mutates `pyproject.toml` on every run.** Because `sync`/`.venv`/
  `lifecycle` run on every `make`/`just` invocation, `uv add -r
  requirements-dev.txt` will re-resolve and may churn `pyproject.toml`'s
  `dependencies` and `uv.lock` each time. uv dedupes already-present deps, so
  repeated runs should converge, but the implementer must verify the file is
  stable across consecutive `make sync` runs (write a quick before/after diff
  check). If churn is unacceptable, fall back to `uv sync` for install and keep
  `uv add` as a one-time migration step — flag back to the user before changing
  the agreed shape.
- **Dependency duplication.** After migration the same dev deps live in three
  places: `requirements-dev.txt`, `pyproject.toml` (via `uv add`), and
  `uv.lock`. This is inherent to the "source from requirements while moving to
  lock" transition and may warrant a follow-up to drop the requirements flow.
- **Where the deps land.** `uv add -r requirements-dev.txt` writes to the
  `[project] dependencies` array, not `[project.optional-dependencies].test`.
  This shifts the toolchain from an optional extra to hard runtime deps of the
  package. If that is undesirable for a published package, `--dev` (dependency
  group) or `--optional test` should be considered — surface this to the user.
- **CI exercises only the Makefile**; the Justfile `lock`/`uv add` paths are not
  covered by CI and must be smoke-tested locally.
