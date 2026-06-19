# Testing & Tooling

This document describes the test suite layout, the `BaseTestCase` helper class, deterministic testing practices, and the build/test/check tooling used in Deadcode. See [index.md](index.md) for the full guide.

## Test Suite Organization

The `tests/` directory mirrors the package structure, with test modules and subdirectories organized by area:

### Test Directories by Area

- **`cli_args/`** — argument parsing and CLI option combinations (`test_parsing.py`, `test_ignore_names.py`, `test_exclude.py`, `test_ignore_names_in_files.py`, `test_no_color.py`, `test_dry.py`, `test_quiet.py`, `test_count.py`, etc.)
- **`fix/`** — fix/removal behavior by code construct (`test_assign.py`, `test_class_def.py`, `test_empty_files.py`, `test_method_def.py`, `test_scope.py`, `test_unreachable_code.py`, `test_unused_imports_in_a_multiple_files.py`, `test_unused_imports_in_a_single_file.py`)
- **`actions/`** — pipeline stages (`test_find_python_filenames.py`, `test_merge_overlaping_file_parts.py`, `test_remove_file_parts_from_content.py`, etc.)
- **`noqa/`** — noqa comment handling (`test_noqa_comments.py`)
- **`nested_scope/`** — scope tracking and nesting
- **`code_item/`** — `CodeItem` type tests (`test_code_item.py`)
- **`utils/`** — utility helper tests

### Test Modules at Top Level

- `test_deadcode.py` — **mixed**: a `BaseTestCase` class using the mock layer plus two real-filesystem integration classes (`DeadCodeIntegrationTests`, `CliEntrypointTests`)
- `test_output.py` — output formatting tests
- `test_accurate_usage_detection.py` — verification of name usage detection
- `test_imports.py` — import handling tests
- `test_line_number_detection.py` — line and column number accuracy
- `test_variable_parsing_from_ast_dump.py` — variable parsing from AST dump representations

### Test Files Directory

`tests/files/` contains fixture Python files used by tests:
- `classes.py`, `functions.py`, `variables.py` — code samples for testing
- `subdir/` — subdirectory samples for path handling tests

### Naming and Style Conventions

- **Modules**: all named `test_<snake_case_subject>.py` (e.g. `tests/fix/test_class_def.py`).
- **Classes**: two forms — the dominant `Test<DescriptiveName>` (e.g. `TestAssignmentExpressionRemoval`) and a minority `<DescriptiveName>Tests` (e.g. `CommandLineArgParsingTests`, `DeadCodeIntegrationTests`).
- **Methods**: uniformly `test_<behavior_in_snake_case>` (e.g. `test_unused_variable_name_found_successfully`).
- **Runner style**: the suite is entirely `unittest`-style classes — no plain pytest functions and **no `conftest.py`** anywhere under `tests/`.
- **`__init__.py`**: present only in `tests/cli_args/` and `tests/utils/` (both empty); other subdirs have none. (`tests/files/subdir/another_subdir/__init__.py` is a fixture, not a package marker.)

## BaseTestCase Helper Class

`BaseTestCase` (`deadcode/utils/base_test_case.py:10`) extends `unittest.TestCase` and provides utilities for testing Deadcode without touching the real filesystem.

### Setup

`setUp()` (`base_test_case.py:37-57`) patches critical I/O and discovery functions:

- `find_python_filenames` (mocked to return `self.files.keys()`)
- `open()` in `deadcode.visitor.find_unused_code_visitor` (mocked to return `self.files[...]`)
- `open()` in `deadcode.visitor.fix_unused_code_visitor` (mocked to return `self.files[...]`)
- `open()` in `deadcode.actions.fix_or_show_unused_code` (mocked to capture writes)
- `os.remove()` (mocked to track deletions)

It also exposes a `patch(path)` helper (`base_test_case.py:15-18`) that wraps `unittest.mock.patch`, starts it, and auto-registers `patcher.stop` via `addCleanup` so each patch is torn down after the test.

Creates a fresh `Args()` for each test.

### File Mocking

Tests define a `files: Dict[str, str]` class attribute mapping filenames to Python code (as strings). The `_read_file_side_effect` (`base_test_case.py:23-35`) serves these via `fix_indent` normalization and captures any writes into `self.updated_files`.

### Assertions

- **`assertFiles(expected_files, removed=None)`** (`base_test_case.py:59-85`) — verifies that file contents (both updated and unchanged) match expectations, and that removed files match the optional `removed` list.
- **`assertUpdatedFiles(expected_updated_files)`** (`base_test_case.py:87-96`) — verifies that only the specified files were modified and have the expected contents.

### Tests Outside BaseTestCase

The suite uses three tiers: (1) mock-backed unit tests via `BaseTestCase` (no disk); (2) real-filesystem integration tests anchored to `REPO_ROOT`; (3) a hybrid that subclasses `BaseTestCase` but uses `tempfile.TemporaryDirectory()` to exercise the real `os.walk` (see Deterministic Testing below). Some tests deliberately bypass the mock layer entirely:

- `tests/code_item/test_code_item.py:7` — tests the `CodeItem` class directly
- `tests/test_deadcode.py` — integration tests using the real filesystem (see Deterministic Testing section below for cwd anchoring)
- `tests/utils/*` — plain `TestCase` tests for utility functions (no mocking needed)

## Deterministic Testing

Tests are designed to pass regardless of the current working directory, `PYTHONHASHSEED`, and xdist worker count. This enables reliable parallel execution and test reproducibility across environments.

### Directory Walk Determinism

The file discovery walk in `find_python_filenames` (`deadcode/actions/find_python_filenames.py:24`) is sorted to ensure stable discovery order across different filesystems and Python hash seeds. The walk uses a LIFO stack, so appended entries determine discovery order. Sorting the `path.glob('*')` results makes this order deterministic, while the final output is still sorted by filename/line in the visitor layer.

### Config Discovery Mocking

`BaseTestCase.setUp` mocks `parse_pyproject_toml` to return an empty dict by default, removing the hidden coupling to the repo's real `[tool.deadcode]` configuration block. This ensures unit tests that call `main()` are not silently affected by the project's own config settings.

```python
self.parse_pyproject_toml_mock = self.patch('deadcode.actions.parse_arguments.parse_pyproject_toml')
self.parse_pyproject_toml_mock.return_value = {}
```

### File System-Bypass Unit Tests

Unit tests that directly import `find_python_filenames` (rather than using the `deadcode.cli` mock) now build controlled directory trees in `tempfile.TemporaryDirectory()` within `setUp`. This preserves behavioral coverage (file detection, directory recursion, exclude rules, missing-path errors, verbose logs) while remaining cwd-independent:

- `tests/actions/test_find_python_filenames.py` — uses a temp tree with `pkg/`, `pkg/utils/`, and sample files
- `tests/cli_args/test_exclude.py` — uses a temp tree to test exclude-by-file and exclude-by-directory logic

### End-to-End Test Anchoring

Integration tests (`DeadCodeIntegrationTests` and `CliEntrypointTests` in `tests/test_deadcode.py`) read real files under `tests/files/` and `deadcode/`, but anchor to the repo root via `chdir` in `setUp`:

```python
REPO_ROOT = Path(__file__).parents[1]  # repo root

def setUp(self):
    self._prev_cwd = os.getcwd()
    os.chdir(REPO_ROOT)
    self.addCleanup(os.chdir, self._prev_cwd)
```

This allows them to pass from any cwd and survive concurrent xdist workers, each of which restores the previous cwd after the test via the cleanup handler.

## Build and Check Commands

The project uses a `Makefile` and a `Justfile` for automation. All common tasks are defined as recipes.

### Makefile Recipes

See `pyproject.toml` for numeric configuration (line-length, coverage targets, etc.) — do not copy these into prose.

- **`test`** (`Makefile:20-21`) — runs `pytest -n "$(nproc --ignore=1)" -vv` with optional `PYTEST_ME_PLEASE` filter (parallel on all-but-one cores via xdist)
- **`lint`** (`Makefile:23-24`) — runs `ruff check deadcode tests`
- **`format`** (`Makefile:39-40`) — runs `ruff format deadcode tests`
- **`mypy`** (`Makefile:29-30`) — runs type-checking on `deadcode/`
- **`deadcode`** (`Makefile:32-33`) — runs Deadcode on itself (self-checking)
- **`audit`** (`Makefile:42-43`) — runs `pip-audit` for security vulnerabilities
- **`check`** (`Makefile:5`) — runs all of the above: `test lint mypy audit deadcode`
- **`fix`** (`Makefile:6`) — runs `format` and `fixlint` (applies automatic fixes)

### Justfile Recipes

The `Justfile` provides these key recipes:

- **`test`** (`Justfile:10-11`) — runs `uv run pytest -n "$(nproc --ignore=1)"` (parallel on all-but-one cores via xdist, matching the Makefile)
- **`sync`** — syncs dependencies and installs the package in editable mode
- **`format`**, **`lint`**, **`typecheck`**, **`check-*`** — individual check targets
- **`check`** (`Justfile:34`) — runs all checks (format, lint, complexity, typecheck, test) in sequence
- **`lifecycle`** — orchestrates workflow tasks via the `lifecycle` command

Both `Makefile` and `Justfile` run `pytest -n "$(nproc --ignore=1)"`, keeping parallel behavior identical across runners. They diverge on extras: the `Makefile` `check` adds `audit` (`pip-audit`) and a self-`deadcode` run, while the `Justfile` `check` adds an explicit `check-complexity` gate (`ruff check --select C901`).

## Configuration Files

### pyproject.toml

- **Entry point**: `deadcode = "deadcode.cli:main"` — defines the CLI command
- **Pytest options** (`pyproject.toml:215`): `addopts` includes coverage settings; cite `pyproject.toml` for numeric gates rather than copying them into docs
- **Ruff configuration** (`pyproject.toml`): line-length 120, all rules enabled with ~70 deliberate policy ignores (see Ruff Code Quality section below)
- **MyPy configuration** (`pyproject.toml`): strict mode enabled (`strict = true`); type checking is run on the `deadcode/` package only (not `tests/`)
- **`[tool.deadcode]`** (`pyproject.toml`): the project's own Deadcode configuration, demonstrating self-usage; ignores inert decorator options, test utilities, and internal visit methods

The project **dog-foods itself**: it runs `make check` (which includes `make deadcode`) to ensure the codebase passes its own unused-code detection.

### Type Checking in Strict Mode

All code in the `deadcode/` package is fully type-checked under mypy's strict mode (`strict = true`). The type-checking gate requires:

- **Zero type errors** — no `[error]` diagnostics reported by mypy
- **No type suppression** — no `# type: ignore` comments (except where justified and documented)
- **Correct node types in visitors** — visitor methods use concrete AST node types (e.g., `visit_ClassDef(node: ast.ClassDef)`, not generic `ast.AST`)
- **Strict return/argument typing** — all function signatures are fully annotated with correct return types
- **Position attribute safety** — AST position attributes (`lineno`, `col_offset`, `end_lineno`, `end_col_offset`) are accessed via `typing.cast` where the static type is too broad

The command `just check-typecheck` runs `uv run mypy deadcode/ --strict` and must exit with zero errors. Tests are not type-checked (mypy targets `deadcode/` only).

### Ruff Code Quality

The codebase is kept **ruff-clean** by enforcing a policy-based ignore list:

- **All rules active** — `select = ["ALL"]` enables all ruff rules by default
- **Policy ignores only** — the `ignore` list (~70 entries) contains only deliberate project policies, not fixes for historical violations:
  - **Docstring rules** (`D1xx`, `D2xx`, `D4xx`) — permissive per project preference
  - **Style & formatting** (`COM812`, `ISC001`) — handled by ruff formatter, not lint
  - **Asserts & print** (`S101`, `T201`) — allowed in tests and CLI output
  - **Type hints** (`ANN001`, `ANN002`, `ANN401`) — permissive where type contracts are clear
  - **Complexity** (`C901`, `PLR0912/0913/0915/2004`) — managed by `check-complexity` (separate gate)
  - **False positives** (`ARG001/002`, `PTH*` family) — rules too strict for this codebase
  - **TODO/FIX/FIXME style** (`FIX002`, `TD002/003/005`) — project convention

- **Tests module** — additional per-file ignores for `tests/*`:
  - `S101` — allow assert statements in tests
  - `PT009` — unittest assertion style permitted
  - `ANN201` — return type hints optional in tests
  - `SLF001` — tests legitimately read private members (e.g. `visitor._log`)
  - `D` — docstring requirements waived in tests

## Development Workflow

A typical contributor flow:

```bash
# Set up environment
make .venv

# Run tests
make test

# Run the full check suite (tests, lint, type checking, audits, self-check)
make check

# Apply automatic fixes
make fix

# Run Deadcode locally
.venv/bin/deadcode deadcode tests -v
```

The `check` recipe is the regression guard ensuring no changes break tests, linting, typing, or Deadcode's own analysis.
