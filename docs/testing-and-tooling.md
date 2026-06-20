# Testing & Tooling

This document describes the test suite layout, the `BaseTestCase` helper class, deterministic testing practices, and the build/test/check tooling used in Deadcode. See [index.md](index.md) for the full guide.

## Test Suite Organization

The `tests/` directory mirrors the package structure, with test modules and subdirectories organized by area:

### Test Directories by Area

- **`cli_args/`** — argument parsing and CLI option combinations (`test_parsing.py`, `test_ignore_names.py`, `test_exclude.py`, `test_ignore_names_in_files.py`, `test_no_color.py`, `test_dry.py`, `test_quiet.py`, `test_count.py`, `test_ignore_definitions_if_decorated_with.py`, etc.)
- **`fix/`** — fix/removal behavior by code construct (`test_assign.py`, `test_class_def.py`, `test_empty_files.py`, `test_method_def.py`, `test_scope.py`, `test_unreachable_code.py`, `test_unused_imports_in_a_multiple_files.py`, `test_unused_imports_in_a_single_file.py`)
- **`frameworks/`** — framework-specific scenario tests (`test_fastapi.py`, `test_sqlalchemy.py`, `test_alembic.py`, `test_django.py`) demonstrating Deadcode with FastAPI, Pydantic, SQLAlchemy, Alembic, Django, and other framework patterns
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
- `test_match_statement.py` — `match`/`case` statement detection (3.11-safe, no version gate)
- `test_walrus.py` — walrus operator (`:=`) detection (3.11-safe, no version gate)
- `test_type_alias.py` — `type` alias detection (3.12+, gated with `@skipUnless(sys.version_info >= (3, 12))`)
- `test_pep695_generics.py` — PEP 695 generic-parameter detection (3.12+, gated with `@skipUnless(sys.version_info >= (3, 12))`)

### Test Files Directory

`tests/files/` contains fixture Python files used by tests:
- `classes.py`, `functions.py`, `variables.py` — code samples for testing
- `subdir/` — subdirectory samples for path handling tests

### Naming and Style Conventions

- **Modules**: all named `test_<snake_case_subject>.py` (e.g. `tests/fix/test_class_def.py`).
- **Classes**: two forms — the dominant `Test<DescriptiveName>` (e.g. `TestAssignmentExpressionRemoval`) and a minority `<DescriptiveName>Tests` (e.g. `CommandLineArgParsingTests`, `DeadCodeIntegrationTests`).
- **Methods**: uniformly `test_<behavior_in_snake_case>` (e.g. `test_unused_variable_name_found_successfully`).
- **Runner style**: the suite is entirely `unittest`-style classes — no plain pytest functions and **no `conftest.py`** anywhere under `tests/`.
- **`__init__.py`**: present in `tests/cli_args/`, `tests/utils/`, and `tests/frameworks/` (all empty); other subdirs have none. (`tests/files/subdir/another_subdir/__init__.py` is a fixture, not a package marker.)

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

### Testing New Syntax Features

Tests for Python 3.11+ features (`match`/`case`, walrus, type aliases, PEP 695 generics) use literal syntax in fixtures and assert exact `path:line:col: DCxx` findings:

- **Format**: `'<file>:<line>:<col>: DCxx <Type> `<name>` is never used'` where `<Type>` is capitalized (`Variable`, `Function`, `Class`).
- **Line/column precision**: Line numbers are 1-based; column numbers are 0-based. Exact column positions for complex constructs (e.g., `total` in `(total := ...)`  or nested names in `type_params`) are confirmed by running the test once and reading the actual output.
- **Negative cases**: Each positive assertion is accompanied by a companion test asserting `None` when the same construct is used (not unused), ensuring false negatives are caught.
- **Fix-path coverage**: Type alias and generic-parameter tests include `--fix` variants to validate both detection and removal paths.

### Version-Gating for Python 3.12+ Syntax

New test files for Python 3.12+ features (type aliases, PEP 695 generics) use `unittest.skipUnless` decorators to gate them by Python version:

```python
@skipUnless(sys.version_info >= (3, 12), 'type alias syntax requires 3.12+')
class TypeAliasTests(BaseTestCase):
    # test methods here
```

This allows:
- **3.11**: 3.12+ test classes are automatically skipped (not failed), keeping the test suite green on the 3.11 floor
- **3.12+**: full test coverage including gated tests
- **CI matrix**: the existing CI workflow (`.github/workflows/check.yml:19`) runs across 3.11–3.14, validating both skipped and active tests

Tests for 3.11-safe constructs (`match`/`case`, walrus `:=`) have no version gate and run on all supported versions.

### Audit Testing: Verifying Detection Correctness

Audit tests verify correctness gaps and boundary behaviors in the detection logic. They encode the **correct/intended** expected behavior and use three patterns:

**1. Confirmed Bugs via `@expectedFailure`**

Tests that expose confirmed false negatives or false positives use `@unittest.expectedFailure`. This allows tests to assert the correct expected behavior (what *should* happen) while the implementation still produces the wrong result:

```python
@expectedFailure
def test_unused_method_shadowed_by_unrelated_use_is_reported(self):
    # Currently returns None (a false negative), but should report the method.
    self.files = {'foo.py': """
        class A:
            def run(self): return 1
        class B:
            def run(self): return 2
        A().run()
        B()
    """}
    unused = main(['foo.py', '--no-color'])
    self.assertEqual(unused, 'foo.py:7:4: DC04 Method `run` is never used')
```

When a fix lands, the assertion passes and pytest reports an "unexpected pass" — the regression guard that signals the bug is fixed. The test automatically converts to a guard without code changes.

**2. By-Design Behavior via Green Tests**

Tests for intentionally disabled or limited features (e.g., parameter tracking disabled, conservative heuristic boundaries) are green characterization tests with no `@expectedFailure`:

```python
def test_unused_parameter_is_not_reported(self):
    # By-design: visit_arg is commented out, so parameters never tracked.
    self.files = {'foo.py': """
        def f(unused_param):
            x = 1
            return 0
        f(2)
    """}
    unused = main(['foo.py', '--no-color'])
    # Only the unused local x is reported, not the parameter.
    self.assertEqual(unused, 'foo.py:2:4: DC01 Variable `x` is never used')
```

These pin current behavior as intentional; audits later can reclassify as bugs if requirements change.

**3. Vacuous-Pass Guard: Control Tests**

Every "None / not reported" audit assertion is paired with a **control** — a similar fixture that *should* be reported, proving the visitor actually ran:

```python
def test_distinctly_named_unused_method_is_reported(self):
    # Control: a uniquely-named unused method IS reported, proving
    # the visitor ran and the F1 gap is specific to name collisions.
    self.files = {'foo.py': """
        class A:
            def run(self): return 1
        class B:
            def distinctly_unused(self): return 2
        A().run()
        B()
    """}
    unused = main(['foo.py', '--no-color'])
    self.assertEqual(unused, 'foo.py:7:4: DC04 Method `distinctly_unused` is never used')
```

Without the control, a `None` assertion might pass for the wrong reason (e.g., the entire visitor is broken). The control proves the mechanism is running.

**4. Version-Gating for Version-Dependent Bugs**

Bugs tied to version-dependent syntax (e.g., `match` captures in 3.10+, PEP 695 type params in 3.12+) use `@skipUnless`:

```python
@skipUnless(sys.version_info >= (3, 10), 'match statements require 3.10+')
class MatchCaptureUnusedTests(BaseTestCase):
    @expectedFailure
    def test_unused_match_capture_is_reported(self):
        # Python 3.10+: captures bind via str attrs, not Name nodes.
        self.files = {'foo.py': """
            match command:
                case [a]:
                    return 0
            handle([1])
        """}
        unused = main(['foo.py', '--no-color'])
        self.assertEqual(unused, 'foo.py:3:14: DC01 Variable `a` is never used')
```

On hosts below the gate, tests **skip** (not fail), keeping the test suite green on the minimum supported Python version.

**Running Audit Tests**

Audit tests run as part of the standard `just test` command. To run only audit tests:

```bash
# Run a single audit test file
uv run pytest tests/test_scope_blind_matching.py -q

# Run all audit test files (by convention, top-level test_*.py files in tests/)
uv run pytest tests/test_*.py -q

# Run with verbose xfail output to see expected failures
uv run pytest tests/ -q -rxX
```

The `-rxX` flag prints expected failures (`x`) and unexpected passes (`X`), useful for tracking which bugs have been fixed (unexpected passes flip the guard).

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

The project uses a `Justfile` for all automation. All common tasks are defined as recipes via Just.

### Justfile Recipes

See `pyproject.toml` for numeric configuration (line-length, coverage targets, etc.) — do not copy these into prose.

Core recipes:

- **`sync`** — installs development dependencies from `requirements-dev.txt` via `uv add`
- **`lock`** — refreshes `uv.lock` via `uv lock`
- **`test`** — runs `uv run pytest -n "$(nproc --ignore=1)"` with optional test filter (parallel on all-but-one cores via xdist)
- **`format`** — runs `uv run ruff format` on `deadcode/` and `tests/`
- **`lint`** — runs `uv run ruff check` on `deadcode/` and `tests/`
- **`typecheck`** — runs `uv run mypy deadcode/` for type checking
- **`check-format`**, **`check-lint`**, **`check-complexity`**, **`check-typecheck`** — individual check targets (no auto-fix variants)
- **`check`** — runs all checks in sequence (format, lint, complexity, typecheck, test)
- **`publish`** — removes old dist files and publishes to PyPI via `uv run hatch build` and `uv run hatch publish`
- **`fix`** — runs `format` then `fixlint` to apply automatic fixes
- **`fixlint`** — runs `uv run ruff check --fix --unsafe-fixes` then `uv run deadcode --fix` for comprehensive linting fixes
- **`deadcode`** — runs Deadcode on itself for self-checking (unused-code detection)
- **`audit`** — runs `uv run pip-audit` for security vulnerability scanning
- **`compile`** — refreshes `requirements.txt` and `requirements-dev.txt` via `uv pip compile`
- **`lifecycle`** — orchestrates workflow tasks via the `lifecycle` command

All recipes use `uv run` to invoke tools rather than direct `.venv/bin/` invocation, ensuring the dev environment is properly activated.

## Configuration Files

### pyproject.toml

- **Entry point**: `deadcode = "deadcode.cli:main"` — defines the CLI command
- **Pytest options** (`pyproject.toml:215`): `addopts` includes coverage settings; cite `pyproject.toml` for numeric gates rather than copying them into docs
- **Ruff configuration** (`pyproject.toml`): line-length 120, all rules enabled with ~70 deliberate policy ignores (see Ruff Code Quality section below)
- **MyPy configuration** (`pyproject.toml`): strict mode enabled (`strict = true`); type checking is run on the `deadcode/` package only (not `tests/`)
- **`[tool.deadcode]`** (`pyproject.toml`): the project's own Deadcode configuration, demonstrating self-usage; ignores inert decorator options, test utilities, and internal visit methods

The project **dog-foods itself**: it runs `just check` (which includes `just deadcode`) to ensure the codebase passes its own unused-code detection.

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
just sync

# Run tests
just test

# Run the full check suite (tests, lint, type checking, complexity)
just check

# Apply automatic fixes
just format && just lint -- --fix

# Update the lockfile if dependencies change
just lock

# Run Deadcode locally
uv run deadcode deadcode tests -v
```

The `check` recipe is the regression guard ensuring no changes break tests, linting, typing, or complexity limits. For any development task, use the corresponding Just recipe (e.g. `just sync`, `just test`, `just check`).
