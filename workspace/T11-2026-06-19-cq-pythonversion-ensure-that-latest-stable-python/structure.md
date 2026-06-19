# Structure Outline

## Approach

Reconcile a *single* supported range — Python **3.11 floor → 3.14 latest stable** —
across config, CI, deps, and docs. Floor/classifiers/mypy are already correct, so
this is pure cleanup of three stale artifacts plus a real CI matrix. Each phase is a
self-contained config change with its own verification; phases are independent and
ordered so the env builder lands before the CI matrix that consumes it.

> Note on "vertical slices": this task has no DB/service/API/UI layers — it is a
> tooling/config reconciliation. Each phase below is sliced as one *end-to-end
> reconciliation concern* (config + the artifact it drives + its verification),
> which is the analogous unit here. Phases 1–2 are coupled (the Makefile param is
> what makes the CI matrix meaningful); the rest stand alone.

---

## Phase 1: Parametrize the env builder

Make the Makefile `.venv` target accept an interpreter version so the same recipe can
build any version in the range. Default stays 3.11 for local dev.

**Files**: `Makefile`

**Key changes**:
- New variable at top: `PYTHON_VERSION ?= 3.11`
- `Makefile:8` `uv venv -p 3.11 .venv` → `uv venv -p $(PYTHON_VERSION) .venv`

**Verify**:
- `rm -rf .venv && make .venv PYTHON_VERSION=3.12 && .venv/bin/python --version`
  prints `Python 3.12.x`.
- `rm -rf .venv && make .venv && .venv/bin/python --version` prints `Python 3.11.x`
  (default unchanged).
- `grep -c 'uv venv -p 3.11' Makefile` returns `0` (no hardcoded version left).

---

## Phase 2: Replace 3.8 CI workflow with a version matrix

Delete the misnamed single-version workflow and add a matrix workflow that builds a
venv per interpreter via the Phase-1 param and runs `make check` on each.

**Files**: delete `.github/workflows/check-deadcode-on-python38.yml`; create
`.github/workflows/check.yml`

**Key changes** (`check.yml`):
- `name: Checks`
- `strategy.matrix.python-version: ["3.11", "3.12", "3.13", "3.14"]`
- `actions/checkout@v4`, `actions/setup-python@v5` with
  `python-version: ${{ matrix.python-version }}`
- Install step: `make .venv PYTHON_VERSION=${{ matrix.python-version }}`
- Checks step: `make check`

**Verify**:
- `ls .github/workflows/check-deadcode-on-python38.yml` → "No such file".
- YAML parses + matrix present:
  `python -c "import yaml,sys; d=yaml.safe_load(open('.github/workflows/check.yml')); assert d['jobs']['build']['strategy']['matrix']['python-version']==['3.11','3.12','3.13','3.14']; print('ok')"`
- `grep -rE '3\.8|py38|checkout@v3|setup-python@v3' .github/workflows/` returns no
  matches.
- (CI confirmation) push branch; all 4 matrix jobs go green. If 3.14 genuinely
  fails, log the exclusion in the workflow comment per design Open Risks — do not
  silently drop.

---

## Phase 3: Remove vestigial `tomli` runtime dependency

Drop the `tomli` direct dependency (source uses stdlib `tomllib`) and regenerate the
locked requirements. The `tomllib` seam and tests are untouched.

**Files**: `pyproject.toml`, `requirements.txt`, `requirements-dev.txt`

**Key changes**:
- Remove `"tomli>=2.0.1"` from `[project].dependencies` (`pyproject.toml:21-23`).
- Regenerate locks: `make compile`.

**Verify**:
- `grep -n 'tomli' pyproject.toml` → no match in `[project].dependencies`.
- `grep -n '^tomli==' requirements.txt` → no match (was `tomli==2.0.1`).
- `make check` passes (tomllib parsing still works; TOML tests green):
  `make test PYTEST_ME_PLEASE=tests/cli_args/test_parsing.py` passes.
- Sanity that source still imports stdlib:
  `grep -n 'import tomllib' deadcode/actions/parse_arguments.py` returns line 6.
- Review `git diff requirements-dev.txt` — `tomli` may remain transitively (via
  pip-audit/hatch); confirm only the *direct* pin removal, no unexpected churn.

---

## Phase 4: Align black `target_version` to the floor

Update the unused-but-named `[tool.black]` target from `py38` to `py311`. Block is
kept (deletion is out of scope per CLAUDE.md §3), only the value the task names is
changed.

**Files**: `pyproject.toml`

**Key changes**:
- `pyproject.toml:209` `target_version = ["py38"]` → `target_version = ["py311"]`

**Verify**:
- `grep -n 'target_version' pyproject.toml` → `["py311"]`, and
  `grep -c 'py38' pyproject.toml` returns `0`.
- `python -c "import tomllib; tomllib.load(open('pyproject.toml','rb')); print('ok')"`
  (file still valid TOML).
- `just check` passes (formatting via ruff is unaffected).

---

## Phase 5: State supported Python range in README

Add a concise "Requires Python 3.11+" line near the install section. No badge; the
historical "Release notes" wording is left alone.

**Files**: `README.md`

**Key changes**:
- One line near `README.md:12-15`, e.g. `**Requires Python 3.11+** (tested on
  3.11–3.14).`

**Verify**:
- `grep -niE 'requires python 3\.11' README.md` returns a match within ~15 lines of
  the install section.
- `git diff README.md` shows only the added line — release-notes block (`:249-261`)
  unchanged.

---

## Testing Checkpoints

State that should hold after each phase (for resume after context reset):

1. **Phase 1**: `make .venv PYTHON_VERSION=X` builds venv with interpreter X;
   default = 3.11; no hardcoded `-p 3.11` remains.
2. **Phase 2**: only `check.yml` exists; matrix = `[3.11,3.12,3.13,3.14]`; no
   `3.8`/`py38`/`@v3` references; CI green (any 3.14 exclusion explicitly logged).
3. **Phase 3**: `tomli` gone from `[project].dependencies` and `requirements.txt`;
   `make check` + TOML parsing tests pass; `import tomllib` seam intact.
4. **Phase 4**: black `target_version == ["py311"]`; zero `py38` in repo config;
   `pyproject.toml` valid TOML; `just check` passes.
5. **Phase 5**: README declares "Requires Python 3.11+" near install; release-notes
   wording untouched.

**Global done-check**: `grep -rE 'py38|3\.8|python3\.8' pyproject.toml Makefile
.github/ Justfile` returns nothing; `make check` and `just check` pass on 3.11.
