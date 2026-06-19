# Research Findings

Project: `deadcode` (v2.3.0, `pyproject.toml:3`). Findings are factual descriptions of
what exists; no recommendations.

## Q1: Where is the supported Python version declared/pinned across config?

### Findings
All Python-version declarations and their values:

| Setting | Location | Value |
|---|---|---|
| `requires-python` | `pyproject.toml:9` | `">= 3.11"` |
| Trove classifiers | `pyproject.toml:16-19` | `3.11`, `3.12`, `3.13`, `3.14` |
| mypy `python_version` | `pyproject.toml:167` | `"3.11"` |
| black `target_version` | `pyproject.toml:209` | `["py38"]` |
| ruff `target-version` | — | **Not declared.** No `target-version` key under `[tool.ruff]` (`pyproject.toml:62-73`); ruff infers target from `requires-python`. |
| isort | `pyproject.toml:176-179` | No version key (only `profile`, `multi_line_output`, `known_third_party`). |
| build-backend | `pyproject.toml:45-47` | `hatchling.build` (`requires = ["hatchling"]`); no Python pin in build-system. |

- The black `target_version` is `py38` (`pyproject.toml:209`) — inconsistent with `requires-python >= 3.11`. Note the project formats with **ruff**, not black (Justfile/Makefile invoke `ruff format`); the `[tool.black]` block is present but unused by the tooling recipes.
- The two values that actually drive type/runtime behavior, `requires-python` (`:9`) and mypy `python_version` (`:167`), both say 3.11. Classifiers extend the advertised range up to 3.14 (`:16-19`).

## Q2: How is the interpreter version selected for local dev/build?

### Findings
- **Makefile `.venv` target** pins the interpreter explicitly: `uv venv -p 3.11 .venv` (`Makefile:8`), then `uv pip sync requirements-dev.txt` and `uv pip install -e .[test]` (`Makefile:9-10`).
- **Justfile** recipes do **not** pin a version. `sync` (`Justfile:6-8`) runs `uv pip sync requirements-dev.txt` + `uv pip install -e .[test]` against whatever interpreter `uv`/the active `.venv` resolves; no `uv venv -p` and no `-p` flag on any recipe. `test`/`format`/`lint`/`typecheck`/`check` all depend on `sync` and run via `uv run` (`Justfile:10-34`).
- The repo already contains a `.venv/` directory (created earlier). `uv run`/`uv pip` use that environment unless told otherwise; the interpreter version there is whatever it was created with.
- `[[tool.uv.index]]` (`pyproject.toml:50-52`) adds a gitlab package index but pins no Python version.
- `Makefile compile` (`:47-49`) regenerates `requirements*.txt` via `uv pip compile` from `pyproject.toml`.

## Q3: CI/CD workflows, Python versions, and matrix?

### Findings
- Exactly **one** workflow file: `.github/workflows/check-deadcode-on-python38.yml`.
- It runs on push/PR to `main` (`:7-10`), `runs-on: ubuntu-latest` (`:18`).
- Named `Checks deadcode package with Python3.8` (`:4`); step "Set up Python 3.8" (`:22`) uses `actions/setup-python@v3` with `python-version: "3.8"` (`:23-25`).
- Install step runs `make .venv` (`:28`) — but `make .venv` itself does `uv venv -p 3.11 .venv` (`Makefile:8`), so the venv is created with 3.11 regardless of the `setup-python` 3.8. Checks run via `make check` (`:31`).
- **No version matrix** — no `strategy.matrix`, single hardcoded version. No multi-version testing mechanism. Uses outdated action versions (`checkout@v3`, `setup-python@v3`).
- The workflow's 3.8 target conflicts with `requires-python >= 3.11` (`pyproject.toml:9`) and with `make .venv` pinning 3.11.

## Q4: How is TOML parsed; which library; TOML deps?

### Findings
- Source imports the **stdlib `tomllib`** (Python 3.11+), unconditionally, with no fallback:
  `import tomllib` at `deadcode/actions/parse_arguments.py:6` (verified directly).
- Single parse site: `tomllib.load(f)` in `parse_pyproject_toml()`, `parse_arguments.py:220-221`; docstring references `tomllib.TOMLDecodeError` (`:213`). Called from `parse_arguments()` at `:195`.
- **No** `try/except`-guarded `tomllib`/`tomli` fallback anywhere in source or tests.
- Tests patch the stdlib seam: `deadcode.actions.parse_arguments.tomllib.load` (`tests/cli_args/test_parsing.py:13`); direct call asserting `{}` at `:124`; `base_test_case.py:54-55` patches `parse_pyproject_toml` to return `{}`.
- **Dependency-list TOML entries (mismatch with source):**
  - `pyproject.toml:21-23` runtime dependency: `"tomli>=2.0.1"`.
  - `requirements.txt:3`: `tomli==2.0.1`.
  - `requirements-dev.txt:173-180`: `tomli==2.4.1` (via deadcode + pip-audit), `tomli-w==1.2.0`, `tomlkit==0.15.0` (the latter two via hatch/pip-audit transitively).
  - The declared `tomli` runtime dependency is **not imported by the source** — source uses stdlib `tomllib`. The `tomli` dep appears vestigial relative to the code.

## Q5: Does source/test code branch on interpreter version?

### Findings
- **No runtime version branching.** No `sys.version_info`, no `platform.python_version`, no live `from __future__ import ...`, no `try/except`-guarded stdlib imports, no `skipIf`/`skipif` version gates anywhere in `deadcode/` or `tests/`.
- `__future__` appears only as an AST filter value (not a live import): `node.module != '__future__'` at `find_unused_code_visitor.py:482` and `fix_unused_code_visitor.py:328`.
- `sys` is imported but used only for non-version purposes: `sys.maxsize` (`utils/fix_indent.py:6`), `sys.argv[1:]` (`parse_arguments.py:22`), `sys.stdout` (`find_unused_code_visitor.py:203`); unused import in `tests/test_deadcode.py:3`.
- `sys.version` strings in `tests/fix/test_unused_imports_in_a_single_file.py:176,201` and `tests/cli_args/test_fix.py:303,316` are source-code fixtures, not runtime checks.
- Implicit version coupling: the code uses `tomllib` (3.11+, Q4) and `ast.unparse()` (3.9+, per README note Q6) — features that gate the minimum interpreter without explicit version checks.

## Q6: What do README/docs/changelog say about supported versions & history?

### Findings
- **README.md:** No Python-version requirement, badge, or supported-versions table. Install section only `pip install deadcode` (`README.md:12-15`); the three badges (`:6-9`) are License, PyPI version, Downloads — none version-related.
- **Only changelog is README "Release notes"** (`README.md:249-261`). Single version-history entry: `README.md:253` (under v2.4.0): "Dropped Python3.8 support, since it does not support `ast.unparse()` function, which is now used in automatic code fixing." Context at `:250-252`. No mention of 3.9–3.14 anywhere in README.
- **docs/:** No statement of supported versions and no changelog. Every "Python" mention refers to the source language analyzed, not interpreter support (e.g. `docs/index.md:3`, `docs/visitor-layer.md:5-7`, `docs/architecture.md:29-31`, `docs/testing-and-tooling.md`).
- **No CHANGELOG/HISTORY/NEWS file** in the repo. `enhancement_proposals/` and `notes` contain no version-support history (`notes:401` only "deadcode release:").

## Cross-Cutting Observations

- **Stated minimum is 3.11, advertised up to 3.14:** `requires-python >= 3.11` (`pyproject.toml:9`) + classifiers 3.11–3.14 (`:16-19`) + mypy 3.11 (`:167`) + `make .venv` `-p 3.11` (`Makefile:8`) are mutually consistent on the 3.11 floor.
- **Three stale/contradictory artifacts point at older versions:** (a) black `target_version = ["py38"]` (`pyproject.toml:209`, tool unused), (b) CI workflow named/targeting Python 3.8 (`check-deadcode-on-python38.yml:4,25`), (c) README note that 3.8 was dropped in v2.4.0 (`README.md:253`) — while `pyproject.toml` version is `2.3.0` (`:3`).
- **`tomllib` (stdlib) vs `tomli` (declared dep):** code path enforces 3.11+ via `import tomllib`, yet `tomli>=2.0.1` remains a declared runtime dependency (`pyproject.toml:22`, `requirements.txt:3`) that the source does not import.
- **Tooling recipes diverge:** Makefile pins 3.11 and runs the legacy lint/test set; Justfile (newer, per CLAUDE.md `just` convention) pins no version and relies on the ambient `.venv`/`uv` resolution.

## Open Areas
- The interpreter version inside the existing `.venv/` was not introspected (recipe-declared values only). Q2 answered from recipe pins, not the live venv contents.
- No `ruff target-version` is set; the exact version ruff infers at runtime from `requires-python` was not executed/confirmed, only that the key is absent (`pyproject.toml:62-73`).
