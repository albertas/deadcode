# Testing & Tooling

This document describes the test suite layout, the `BaseTestCase` helper class, and the build/test/check tooling used in Deadcode. See [index.md](index.md) for the full guide.

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

- `test_deadcode.py` — full integration tests (uses real filesystem)
- `test_output.py` — output formatting tests
- `test_accurate_usage_detection.py` — verification of name usage detection
- `test_imports.py` — import handling tests
- `test_line_number_detection.py` — line and column number accuracy
- `test_variable_parsing_from_ast_dump.py` — variable parsing from AST dump representations

### Test Files Directory

`tests/files/` contains fixture Python files used by tests:
- `classes.py`, `functions.py`, `variables.py` — code samples for testing
- `subdir/` — subdirectory samples for path handling tests

## BaseTestCase Helper Class

`BaseTestCase` (`deadcode/utils/base_test_case.py:10-93`) extends `unittest.TestCase` and provides utilities for testing Deadcode without touching the real filesystem.

### Setup

`setUp()` (`base_test_case.py:37-54`) patches critical I/O and discovery functions:

- `find_python_filenames` (mocked to return `self.files.keys()`)
- `open()` in `deadcode.visitor.find_unused_code_visitor` (mocked to return `self.files[...]`)
- `open()` in `deadcode.visitor.fix_unused_code_visitor` (mocked to return `self.files[...]`)
- `open()` in `deadcode.actions.fix_or_show_unused_code` (mocked to capture writes)
- `os.remove()` (mocked to track deletions)

Creates a fresh `Args()` for each test.

### File Mocking

Tests define a `files: Dict[str, str]` class attribute mapping filenames to Python code (as strings). The `_read_file_side_effect` (`base_test_case.py:23-35`) serves these via `fix_indent` normalization and captures any writes into `self.updated_files`.

### Assertions

- **`assertFiles(expected_files, removed=None)`** (`base_test_case.py:56-82`) — verifies that file contents (both updated and unchanged) match expectations, and that removed files match the optional `removed` list.
- **`assertUpdatedFiles(expected_updated_files)`** (`base_test_case.py:84-93`) — verifies that only the specified files were modified and have the expected contents.

### Tests Outside BaseTestCase

Some tests bypass the mock layer:

- `tests/code_item/test_code_item.py:7` — tests the `CodeItem` class directly
- `tests/test_deadcode.py:7` — integration tests using the real filesystem
- `tests/utils/*` — plain `TestCase` tests for utility functions (no mocking needed)

## Build and Check Commands

The project uses a `Makefile` and a `Justfile` for automation. All common tasks are defined as recipes.

### Makefile Recipes

See `pyproject.toml` for numeric configuration (line-length, coverage targets, etc.) — do not copy these into prose.

- **`test`** (`Makefile:18-19`) — runs `pytest -vv` with optional `PYTEST_ME_PLEASE` filter
- **`lint`** (`Makefile:21-22`) — runs `ruff check deadcode tests`
- **`format`** (`Makefile:37-38`) — runs `ruff format deadcode tests`
- **`mypy`** (`Makefile:27-28`) — runs type-checking on `deadcode/`
- **`deadcode`** (`Makefile:30-31`) — runs Deadcode on itself (self-checking)
- **`audit`** (`Makefile:40-41`) — runs `pip-audit` for security vulnerabilities
- **`check`** (`Makefile:3`) — runs all of the above: `test lint mypy audit deadcode`
- **`fix`** (`Makefile:4`) — runs `format` and `fixlint` (applies automatic fixes)

### Justfile Recipe

The `Justfile` contains a single `lifecycle` recipe that runs `uv pip sync` and installs the package in editable mode, used for dependency management.

## Configuration Files

### pyproject.toml

- **Entry point** (`pyproject.toml:38`): `deadcode = "deadcode.cli:main"` — defines the CLI command (the entry is on line 37; line 38 is the blank that follows)
- **Pytest options** (`pyproject.toml:209`): `addopts` includes coverage settings; cite `pyproject.toml` for numeric gates rather than copying them into docs
- **Ruff configuration** (`pyproject.toml:61-160`): line-length, lint rules, format style
- **MyPy configuration** (`pyproject.toml:162-170`): strict mode enabled
- **`[tool.deadcode]`** (`pyproject.toml:178-201`): the project's own Deadcode configuration, demonstrating self-usage; ignores inert decorator options, test utilities, and internal visit methods

The project **dog-foods itself**: it runs `make check` (which includes `make deadcode`) to ensure the codebase passes its own unused-code detection.

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
