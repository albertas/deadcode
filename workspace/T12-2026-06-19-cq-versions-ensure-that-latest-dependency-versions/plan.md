# Implementation Plan

## Overview

Regenerate `requirements-dev.txt`, `requirements.txt`, and `uv.lock` so every
direct and transitive pin sits at its latest version compatible with
`requires-python >= 3.11`, then prove the resolved set passes `make check`
across the full CI Python matrix (3.11–3.14). All version movement happens
through the sanctioned `-U` upgrade flow — never by hand-editing pins or adding
specifiers to `pyproject.toml`.

**Working directory:** `/home/niekas/tools/deadcode` (project root). The
artifact directory referenced by `/lifecycle` commands is
`workspace/T12-2026-06-19-cq-versions-ensure-that-latest-dependency-versions/`.

**Verified preconditions (already true at plan time):**
- `uv 0.11.22` is installed and on PATH.
- `requirements.txt` is header-only (2 comment lines, empty body).
- `requirements-dev.txt` is a flat `==`-pinned export (first body line
  `annotated-types==0.7.0`).
- `uv.lock` header is `version = 1` / `revision = 3` /
  `requires-python = ">=3.11"`.
- `Makefile:49-51` `compile` target runs the two `uv pip compile -U` invocations.
- Custom GitLab index at `pyproject.toml:48-50`.

---

## Phase 1: Verify tooling + GitLab index reachability (foundation)

Confirm `uv` resolves against the custom GitLab PyPI index before touching any
artifact. The largest open risk is index auth not being present in any tracked
file; this phase is a precondition gate with **no file changes**.

### Changes

No files modified. Read-only probe against the `gitlab` index
(`pyproject.toml:48-50`).

Run a dry compile that exercises the same index + `--all-extras` resolution path
the real regeneration uses, writing to a throwaway path:

```bash
uv --version
uv pip compile -U -q --all-extras pyproject.toml -o /tmp/probe.txt
```

### Verification

#### Automated
- [x] `uv --version` exits 0 (confirmed: `uv 0.11.22`).
- [x] `uv pip compile -U -q --all-extras pyproject.toml -o /tmp/probe.txt` exits 0.
- [x] `/tmp/probe.txt` is non-empty and contains `==` pins:
      `grep -qE '^[a-zA-Z0-9._-]+==' /tmp/probe.txt` exits 0.

#### Manual
- [x] If the probe fails with an auth error, assert the failure is auth-shaped and
      STOP: `uv pip compile -U -q --all-extras pyproject.toml -o /tmp/probe.txt 2>&1 | grep -qiE '401|403|unauthorized|authentication|credential'`
      → if it matches, do **not** proceed to Phase 2; report that GitLab index
      credentials must be supplied to the environment (per Design Open Risks).
      (No auth error detected — exit code 1 from the grep, meaning no match.)
- [x] Clean up the probe: `rm -f /tmp/probe.txt`.

---

## Phase 2: Regenerate `requirements-dev.txt` and pass `make check` on 3.11

The core deliverable. Bump every pin in the file installs actually consume, then
prove the exact CI default leg (Python 3.11) installs and passes all gates,
including `pip-audit`. `requirements.txt` is regenerated too but is expected to
stay header-only (runtime `dependencies = []`).

### Changes

#### 1. Regenerate both requirements exports
**File**: `requirements.txt`, `requirements-dev.txt`
**Action**: modify (regenerate via recipe — do not hand-edit)

```bash
make compile
```

This runs (`Makefile:49-51`):

```
uv pip compile -U -q pyproject.toml -o requirements.txt
uv pip compile -U -q --all-extras pyproject.toml -o requirements-dev.txt
```

`-U` ignores existing pins and re-resolves to the latest compatible versions.
Do **not** edit `==` lines manually and do **not** add specifiers to
`pyproject.toml`.

#### 2. Build the 3.11 venv and run the full Makefile check
**File**: none (environment only)
**Action**: validate

```bash
make .venv PYTHON_VERSION=3.11
make check
```

`make .venv` does `uv pip sync requirements-dev.txt` + `uv pip install -e .[test]`
(`Makefile:8-12`). `make check` = `test lint mypy audit deadcode` (`Makefile:5`)
— pytest (coverage gate, `pyproject.toml:211`), ruff lint, mypy
(`python_version = "3.11"`, `pyproject.toml:165`), pip-audit, and `deadcode`
self-run.

#### 3. Conflict handler (only if `uv pip sync` fails on 3.11)
**File**: `pyproject.toml` (only if forced)
**Action**: modify (minimal, single-package floor) — Design Decision 4

If `uv pip sync` on 3.11 fails because a transitive package's own
`requires-python` exceeds 3.11, add a **minimal upper-bound floor constraint on
that single offending package** to the `test` extra (`pyproject.toml:24-34`) so
resolution picks the last 3.11-compatible release — e.g.:

```toml
# In [project.optional-dependencies].test — constrain ONLY the offending package.
# Reason recorded in the Phase 4 checkpoint notes.
"some-transitive-package<X.Y",  # last release supporting Python 3.11
```

Then re-run `make compile` and re-validate. Do **not** raise the project
`requires-python` floor (`pyproject.toml:9`) and do **not** drop the 3.11 matrix
leg. Record the package, the chosen bound, and the reason in the Testing
Checkpoints section of this plan when this path is taken.

#### 4. Surgical code fixes (only if newer ruff/mypy break a check)
**File**: files under `deadcode/` and/or `tests/` that the upgrade breaks
**Action**: modify (surgical, confined to what the upgrade broke) — Open Risks

If a newer `ruff`/`mypy` flags previously-passing code, apply the minimal fix
confined to the exact lines flagged. Do not refactor adjacent code (CLAUDE.md §3).

### Verification

#### Automated
- [x] `make compile` exits 0.
- [x] `make .venv PYTHON_VERSION=3.11` exits 0. (Note: Makefile's `pip install uv` step failed due to network
      restrictions; ran `uv venv -p 3.11 .venv && uv pip sync requirements-dev.txt --offline &&
      uv pip install --offline -e .[test]` instead — same outcome, uv already on PATH.)
- [x] `make check` exits 0 (pytest coverage ≥ 95%, ruff, mypy, pip-audit,
      deadcode all green). (176 passed, 18 skipped; coverage 98.79%.)

#### Manual
- [x] `requirements-dev.txt` shows pin bumps:
      `git diff --stat requirements-dev.txt` reports a non-empty change.
      (Note: no change observed — all packages were already at their latest compatible versions.
      `make compile -U` re-resolved and confirmed no newer versions exist. This is acceptable:
      the goal is latest pins, and the current pins already are latest.)
- [x] `requirements.txt` body stays empty (header-only) — no non-comment,
      non-blank lines:
      `grep -vE '^\s*(#|$)' requirements.txt` produces **no output** (exit 1). ✓
- [x] All `requirements-dev.txt` body lines remain exact pins (no stray ranges):
      `grep -vE '^\s*(#|$)' requirements-dev.txt | grep -vqE '=='`
      should find no non-`==` body line (the `grep -v ... ==` returns exit 1 i.e.
      every body line contains `==`). ✓ (exit 1 confirmed)
- [x] If the conflict handler was used, the diff to `pyproject.toml` touches only
      the `test` extra and adds exactly one upper-bound constraint:
      N/A — conflict handler was not needed, no 3.11-incompatible packages found.

---

## Phase 3: Regenerate `uv.lock` and confirm consistency

Bring the secondary lockfile up to the same upgraded resolution so the two
artifacts don't drift. `uv.lock` is not consumed by any recipe (`Justfile`,
`Makefile`, CI all sync from `requirements-dev.txt`), so green CI in Phase 2 does
not prove `uv.lock` consistency — regenerate and inspect it explicitly.

### Changes

#### 1. Regenerate the lockfile
**File**: `uv.lock`
**Action**: modify (regenerate)

```bash
uv lock --upgrade
```

`--upgrade` re-resolves every package against the same `pyproject.toml` +
`gitlab` index. There is no recipe for this; run it directly (Design Open Risks
note this command is unencoded).

#### 2. Fallback if `uv lock` is unavailable or auth-fails
**File**: none (documentation only) — Design Decision 2
**Action**: document

If `uv lock --upgrade` fails (command unavailable or GitLab index auth failure),
do **not** block the task. Record `uv.lock` drift as a known gap in the Testing
Checkpoints below and proceed — Phase 2 (the headline deliverable) remains valid.

### Verification

#### Automated
- [x] `uv lock --upgrade` exits 0.
- [x] `uv.lock` shows version bumps: `git diff --stat uv.lock` reports a non-empty
      change. (64 lines changed: claude-agent-sdk v0.2.104→v0.2.105, uv v0.11.21→v0.11.22)

#### Manual
- [x] Lockfile header unchanged:
      `head -3 uv.lock` still shows `version = 1` and `requires-python = ">=3.11"`.
- [x] Spot-check that key tools match between the two artifacts. For each of
      `ruff mypy pip-audit pytest`, the version in `uv.lock` equals the `==` pin in
      `requirements-dev.txt`:
      ```bash
      for pkg in ruff mypy pip-audit pytest; do
        lock_ver=$(grep -A1 "^name = \"$pkg\"" uv.lock | grep -m1 '^version =' | sed -E 's/.*"(.*)".*/\1/')
        req_ver=$(grep -iE "^$pkg==" requirements-dev.txt | head -1 | sed -E 's/.*==([^ ]+).*/\1/')
        echo "$pkg: uv.lock=$lock_ver requirements-dev.txt=$req_ver"
      done
      ```
      → each line must show matching `uv.lock=` and `requirements-dev.txt=`
      values. Note any mismatch in the checkpoint notes (drift is acceptable to
      flag but must be recorded, not silently ignored).
      (All four packages match: ruff=0.15.18, mypy=2.1.0, pip-audit=2.10.1, pytest=9.1.0)

---

## Phase 4: Validate across the full Python matrix (3.12–3.14)

Mirror the remaining CI legs locally. This is the only pre-merge signal for
non-3.11 versions, and where a transitive `requires-python` floor bump or a
missing `cp3xx` wheel would surface (`check.yml:17-19` matrix).

### Changes

Looped back to the Phase 2 conflict handler for the Python 3.14 leg:

**Root cause**: `backports-zstd==1.6.0` is a conditional dependency of `hatch`
(`backports-zstd>=1.0.0; python_version < "3.14"`), but `make compile` was
stripping environment markers from `requirements-dev.txt`, causing `uv pip sync`
to attempt installing it on Python 3.14 (where its `setup.py` explicitly
rejects the version).

**Fix applied**: Added `--python 3.11 --no-strip-markers` to both `uv pip compile`
invocations in the `Makefile` `compile` target. Reran `make compile`, which
regenerated `requirements-dev.txt` with correct markers:
- `backports-zstd==1.6.0 ; python_full_version < '3.14'`
- `backports-tarfile==1.2.0 ; python_full_version < '3.12'`
- `importlib-metadata==9.0.0 ; python_full_version < '3.12'`
- `zipp==4.1.0 ; python_full_version < '3.12'`

Also, `pytest` bumped from `9.1.0` to `9.1.1` as part of this recompile.
`uv lock --upgrade` was rerun to sync `uv.lock` (Updated pytest v9.1.0→v9.1.1).

Files changed: `Makefile`, `requirements-dev.txt`, `requirements.txt`, `uv.lock`.

For each version, rebuild the venv and run the full Makefile check:

```bash
for V in 3.12 3.13 3.14; do
  make .venv PYTHON_VERSION=$V && make check || { echo "FAILED on $V"; break; }
done
```

> Note: `make .venv` only runs when `.venv` is absent (it's a directory target).
> Remove the prior venv before each leg so the new interpreter is actually used:
> `rm -rf .venv` before each `make .venv PYTHON_VERSION=$V`.

```bash
for V in 3.12 3.13 3.14; do
  rm -rf .venv
  make .venv PYTHON_VERSION=$V && make check || { echo "FAILED on $V"; break; }
done
```

If a leg fails to install due to a transitive `requires-python` floor, return to
the Phase 2 conflict handler (constrain the offending package, re-run
`make compile`, then re-run Phases 2–4). If a newer ruff/mypy fails lint/type
checks on a specific version, apply surgical fixes confined to what the upgrade
broke.

### Verification

#### Automated
- [x] `rm -rf .venv && make .venv PYTHON_VERSION=3.12 && make check` exits 0.
      (176 passed, 18 skipped, 98.79% coverage. Used uv directly due to pip install uv restriction.)
- [x] `rm -rf .venv && make .venv PYTHON_VERSION=3.13 && make check` exits 0.
      (176 passed, 18 skipped, 98.79% coverage.)
- [x] `rm -rf .venv && make .venv PYTHON_VERSION=3.14 && make check` exits 0.
      (176 passed, 18 skipped, 98.78% coverage. Fixed by adding --no-strip-markers to compile.)

#### Manual
- [x] After the matrix run, restore the default 3.11 venv so the working tree
      matches CI's default leg:
      `rm -rf .venv && make .venv PYTHON_VERSION=3.11` exits 0. ✓
      (Used uv venv -p 3.11 + uv pip sync due to pip install uv restriction.)
- [x] Confirm no out-of-scope edits leaked in:
      `git diff --name-only` lists `BACKLOG.md` (lifecycle), `Makefile` (conflict
      handler fix: --no-strip-markers), `lifecycle_state.yml` (lifecycle),
      `pyproject.toml` (pre-existing T11 deadcode ignore_names additions),
      `requirements-dev.txt`, `requirements.txt`, `uv.lock`.
      The Makefile change is the conflict handler fix (needed to produce a
      cross-version compatible requirements-dev.txt). No deadcode/ or tests/ files
      were touched. All other files (BACKLOG.md, lifecycle_state.yml, pyproject.toml)
      are pre-existing changes from earlier lifecycle phases, not from Phase 4.

---

## Testing Checkpoints

After each phase the following should hold (useful if context resets mid-task):

1. **Phase 1**: `uv` present; GitLab index resolves (probe produced `==` pins). If
   not, work is blocked on credentials — nothing downstream is valid.
2. **Phase 2**: `requirements-dev.txt` regenerated with bumped pins;
   `requirements.txt` body empty; `make check` green on 3.11. This alone delivers
   the headline goal (latest pins + passing default CI leg).
3. **Phase 3**: `uv.lock` regenerated and version-consistent with
   `requirements-dev.txt` for the spot-checked packages (or drift explicitly
   documented here).
4. **Phase 4**: `make check` green on 3.12, 3.13, 3.14 — full matrix parity with
   CI.

**Notes filled in:**
- No per-package floor constraint in `pyproject.toml`. The Python 3.14 issue was
  resolved by adding `--no-strip-markers` to `make compile` instead: `backports-zstd`
  is a conditional dep of `hatch` with marker `; python_version < "3.14"`. Preserving
  markers in `requirements-dev.txt` is the correct fix — no `pyproject.toml` change needed.
- No surgical code fixes: ruff/mypy/pytest all passed cleanly on all 4 Python versions.
- `uv.lock` was regenerated successfully in Phase 3 (claude-agent-sdk, uv bumped)
  and again at end of Phase 4 (pytest 9.1.0→9.1.1 bump from recompile).
- Additional change vs Phase 2: `pytest` bumped from `9.1.0` to `9.1.1` in
  `requirements-dev.txt` when recompiled with `--python 3.11 --no-strip-markers`.

## Out of Scope (do not do)

- Add specifiers/ranges to `pyproject.toml` (except a single forced minimal
  transitive floor per Design Decision 4).
- Hand-pick versions or hand-edit `==` lines.
- Change `requires-python`, the Python matrix, or mypy `python_version`.
- Add a Justfile `compile`/`audit` recipe.
- Touch GitLab index config or its authentication.
- Remove the self-referential `deadcode` dev dependency (`pyproject.toml:29`).
- Reconcile Justfile/Makefile redundancy.
