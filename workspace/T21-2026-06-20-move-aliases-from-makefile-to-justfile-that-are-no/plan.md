# Plan

## Phase 1: Port missing aliases to the Justfile and remove the Makefile

### Background

Both `Makefile` and `Justfile` exist at the repo root. The task is to make the
`Justfile` primary: copy over only the Makefile recipes that have no Justfile
counterpart, then delete the `Makefile`. Anything that currently calls `make`
(CI, docs) must be repointed at `just`.

### Alias comparison

Makefile targets: `check, fix, .venv, publish, test, lint, mypy, deadcode,
fixlint, format, audit, sync, lock, compile`.

Justfile recipes: `lifecycle, sync, lock, test, format, lint, typecheck,
check-format, check-lint, check-complexity, check-typecheck, check`.

Already covered (do NOT re-add):
- `test`, `lint`, `format`, `sync`, `lock` — present verbatim.
- `mypy` — covered by the Justfile's `typecheck` recipe (`uv run mypy deadcode/`).
- `check` — present (the Justfile already has its own `check` composition; leave
  it as-is, do not overwrite with the Makefile's `test lint mypy audit deadcode`).
- `.venv` bootstrap — the Justfile's `sync` recipe (`uv add --requirements
  requirements-dev.txt`) is the equivalent install step.

Missing from the Justfile — port these:
- `publish` — `rm -fr dist/*` then `hatch build` + `hatch -v publish`.
- `fix` — runs `format` then `fixlint`.
- `fixlint` — `ruff check --fix ... --unsafe-fixes` then `deadcode ... --fix`.
- `deadcode` — self-run: `deadcode deadcode tests -v`.
- `audit` — `pip-audit`.
- `compile` — the two `uv pip compile` lines for `requirements.txt` and
  `requirements-dev.txt`.

### Implementation steps

1. **Add the missing recipes to `/home/niekas/tools/deadcode/Justfile`**, matching
   the existing Justfile style (lowercase recipe names, `sync` as a dependency
   where the recipe needs the dev environment, `uv run` to invoke tools rather
   than `.venv/bin/...`). Concretely:
   - `audit: sync` → `uv run pip-audit`
   - `deadcode: sync` → `uv run deadcode deadcode/ tests/ -v`
   - `fixlint: sync` → `uv run ruff check --fix deadcode/ tests/ --unsafe-fixes`
     then `uv run deadcode deadcode/ tests/ --fix`
   - `fix: format fixlint` (recipe-dependency form, mirroring how `check`
     composes other recipes)
   - `publish: sync` → `rm -fr dist/*` then `uv run hatch build` and
     `uv run hatch -v publish`
   - `compile:` (no `sync` dep, matching the Makefile which had none) → the two
     `uv pip compile -U -q --python 3.11 --no-strip-markers pyproject.toml ...`
     lines.
   - Keep recipe ordering/grouping consistent with the current Justfile.

2. **Verify `hatch` and `pip-audit` are available** to `uv run` (check they are
   listed in `requirements-dev.txt` / `pyproject.toml` dev extras). If a tool is
   not declared as a dev dependency, note it — the recipe will otherwise fail
   under `uv run`. (The Makefile invoked them from `.venv/bin/`, so they should
   already be present, but confirm.)

3. **Delete `/home/niekas/tools/deadcode/Makefile`.**

4. **Update CI `/home/niekas/tools/deadcode/.github/workflows/check.yml`** so it no
   longer calls `make`:
   - Replace `make .venv PYTHON_VERSION=${{ matrix.python-version }}` with the
     `just sync` equivalent (install `just` + run `just sync`, or invoke `uv`
     directly). Ensure `just` is available on the runner (e.g. install via the
     setup step) since CI currently only has `make`.
   - Replace `make check` with `just check`. NOTE: the Makefile's `check` ran
     `test lint mypy audit deadcode`, while `just check` runs
     `check-format check-lint check-complexity check-typecheck test`. These are
     not identical — `make check` additionally ran `audit` and `deadcode`. To
     preserve CI coverage, either append `just audit just deadcode` to the CI run
     step, or leave `just check` as the gate and accept the (documented)
     difference. Default: preserve coverage by also running `just audit` and
     `just deadcode` in CI so removing the Makefile does not silently drop the
     security audit and self-deadcode check.

5. **Update docs that reference the Makefile** so they describe the Justfile as
   the sole automation entry point:
   - `/home/niekas/tools/deadcode/docs/testing-and-tooling.md` — the "Makefile
     Recipes" section, the `make check` / `make deadcode` dog-fooding line, and
     the "For Makefile equivalents, use `make .venv` ..." line.
   - `/home/niekas/tools/deadcode/docs/invocation.md` — the "Makefile Test
     Target" section and the `uv lock` / Makefile mention.
   - `/home/niekas/tools/deadcode/README.md` — the `make test` line ("both
     `make test` and `just test` ...").
   - NOTE (deviation): `docs/testing-and-tooling.md` and `docs/invocation.md`
     have already diverged — they reference the Justfile only, with no remaining
     `make`/`Makefile` build-tooling mentions. README likewise already uses
     `just test`/`just check`. So no doc edits were needed beyond confirming
     this; the only remaining `Makefile` token is the `--quiet` help-text below.
   - Leave the `--quiet` help-text string in
     `deadcode/actions/parse_arguments.py` and README's options table that says
     "Makefile still fails with exit code 1 ..." — that is user-facing CLI copy
     about exit behavior, unrelated to the build tooling, and out of scope.
     Mention it but do not change it unless the user asks.

### Verification

- [x] `just --list` shows all ported recipes (`publish`, `fix`, `fixlint`,
  `deadcode`, `audit`, `compile`) plus the pre-existing ones, with no duplicates.
- [x] `just audit`, `just deadcode`, `just fix` (and `just fixlint`) run without
  "recipe not found" errors and behave like their former Makefile targets.
  (Verified `audit`, `deadcode`, `fixlint`; `fix` is the `format fixlint`
  composition.)
- [x] `just check` still passes (run it). 207 passed, 24 skipped, 98.57% coverage.
- [x] `grep -rn "make \|Makefile" .github README.md docs/` returns no remaining
  build-tooling references (only the intentional CLI `--quiet` help text may
  remain).
- [x] The `Makefile` no longer exists at the repo root.
- [x] CI workflow YAML is valid and references only `just`/`uv`, not `make`.
