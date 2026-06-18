# Plan

## Phase 1: Add Justfile dev targets and required dev dependencies

### Context (already verified)

- Source package lives in `deadcode/`; tests live in `tests/`. The example
  Justfile in the ticket targets `app/` — adapt all paths to `deadcode/` (and
  `tests/` where the example uses `app/ tests/`).
- The project uses `uv`. The existing `Makefile` `sync` step is:
  `uv pip sync requirements-dev.txt` then `uv pip install -e .[test]`. The
  current `Justfile` only has a `lifecycle` target that inlines this.
- Dev tools are declared in `pyproject.toml` under
  `[project.optional-dependencies] test` (`ruff`, `mypy`, `pytest`,
  `pytest-cov`, etc.) and pinned in `requirements-dev.txt`, which is generated
  by the `Makefile` `compile` target (`uv pip compile --all-extras pyproject.toml
  -o requirements-dev.txt`).
- `pytest-xdist` (needed for `pytest -n`) is **not** currently a dependency —
  it is absent from both `pyproject.toml` and `requirements-dev.txt`.
- `pyproject.toml` already configures ruff (line-length 120) and mypy (strict).
  `C901` is in the global ruff `ignore` list, so the complexity target must use
  `ruff check --select C901` to re-enable it explicitly.
- `[tool.pytest.ini_options] addopts` adds coverage flags
  (`--cov=. --no-cov-on-fail --cov-fail-under=88.0`); these run automatically
  under the `test` target.

### Steps

1. **Add `pytest-xdist` dev dependency.**
   - Add `"pytest-xdist"` to the `test` list in
     `[project.optional-dependencies]` in `pyproject.toml`.
   - Verify: `grep pytest-xdist pyproject.toml`.

2. **Regenerate `requirements-dev.txt`** so the new dependency is pinned and the
   `sync` step installs it.
   - Run `uv pip compile -U -q --all-extras pyproject.toml -o requirements-dev.txt`
     (mirrors the `Makefile` `compile` target).
   - Verify: `grep -i "pytest-xdist\|execnet" requirements-dev.txt` returns
     matches.

3. **Add the dev targets to `Justfile`** without removing the existing
   `lifecycle` target. Mirror the ticket's example, adapting paths and adding a
   `sync` target the others depend on:
   - `sync`: `uv pip sync requirements-dev.txt` + `uv pip install -e .[test]`
     (reuse the commands already in `lifecycle`/`Makefile`).
   - `test *args: sync` → `uv run pytest -n "$(nproc --ignore=1)" {{args}}`
   - `format: sync` → `uv run ruff format deadcode/ tests/`
   - `lint: sync` → `uv run ruff check deadcode/ tests/`
   - `typecheck: sync` → `uv run mypy deadcode/`
   - `check-format: sync` → `uv run ruff format --check deadcode/ tests/`
   - `check-lint: sync` → `uv run ruff check deadcode/ tests/`
   - `check-complexity: sync` → `uv run ruff check --select C901 deadcode/ tests/`
   - `check-typecheck: sync` → `uv run mypy deadcode/`
   - `check: check-format check-lint check-complexity check-typecheck test`
   - Note: the `Makefile` runs `mypy` only on `deadcode/` (strict mode), so the
     typecheck targets follow that scope rather than including `tests/`.

4. **Verify the targets work.**
   - `just check-format` and `just check-lint` succeed (or report only
     pre-existing issues — do not "fix" unrelated code).
   - `just check-complexity` runs and reports C901 findings without error.
   - `just typecheck` runs `mypy deadcode/`.
   - `just test` runs the suite in parallel via xdist.
   - `just check` chains all of the above.
   - Confirm `just lifecycle` is still present and unchanged.

### Notes / risks

- `nproc --ignore=1` is GNU-coreutils specific (fine for this Linux project).
- Running `pytest -n` together with the existing coverage `addopts` works via
  `pytest-cov` + `pytest-xdist`; if coverage measurement misbehaves under
  xdist, that is a follow-up concern, not part of this target-wiring task.
- Keep changes surgical: add targets and the one dependency; do not reformat or
  refactor existing code, and do not remove the `Makefile`.
