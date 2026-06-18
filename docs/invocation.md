# Development Targets & Invocation

This document describes how to invoke the development targets via Just and the Deadcode CLI. See [overview.md](overview.md) for the documentation index.

## Dependency Synchronization

Before running any development target, sync dependencies:

```bash
just sync
```

This runs:
- `uv pip sync requirements-dev.txt` — Installs pinned dev dependencies
- `uv pip install -e .[test]` — Installs Deadcode in editable mode with test extras

All other targets depend on `sync`, so it runs automatically if needed.

## Testing

### Run all tests

```bash
just test
```

Runs pytest with parallel execution (using all but one CPU core via `nproc --ignore=1`) and coverage measurement. Coverage report is printed and the run fails if coverage drops below 88%.

### Run specific tests

```bash
just test tests/path/to/test_file.py
```

### Run tests with custom pytest args

```bash
just test -- -k "test_name" -vv
```

Coverage and parallel execution still apply. Pass `-- <args>` to forward arguments to pytest.

## Code Quality Checks

### Formatting

```bash
just format
```

Runs `ruff format` on `deadcode/` and `tests/` directories.

### Formatting check (no changes)

```bash
just check-format
```

Reports formatting issues without modifying files. Use before committing to ensure code passes the check phase.

### Linting

```bash
just lint
```

Runs `ruff check` on `deadcode/` and `tests/` directories without fixing. Use this to report all lint issues.

### Linting check (no auto-fix)

```bash
just check-lint
```

Reports linting issues without auto-fixing. Part of the comprehensive `just check` pipeline.

### Type checking

```bash
just typecheck
```

Runs `mypy` in strict mode on `deadcode/` (not `tests/`, per Makefile convention). Reports type errors.

### Type checking check (no changes)

```bash
just check-typecheck
```

Reports type errors without modifying files. Part of the comprehensive `just check` pipeline.

### Complexity check

```bash
just check-complexity
```

Runs `ruff check --select C901` to report McCabe complexity violations (complexity > 10, per `pyproject.toml`). This check is part of the gating `just check` pipeline.

## Comprehensive Check Pipeline

```bash
just check
```

Runs all checks in order and fails on any error:

1. `check-format` — Ensures code is formatted
2. `check-lint` — Ensures lint passes
3. `check-complexity` — Ensures no function complexity > 10
4. `check-typecheck` — Ensures type check passes
5. `test` — Runs full test suite with coverage

This is the gating check run before merging and is recommended before any commit.

## Deadcode CLI

The main Deadcode command-line tool for analyzing code:

```bash
uv run deadcode .
```

For full CLI reference and configuration via `pyproject.toml`, see [cli-and-configuration.md](cli-and-configuration.md).

### Common operations

```bash
# Find unused code
uv run deadcode .

# Show what would be removed without making changes
uv run deadcode . --dry

# Automatically remove unused code
uv run deadcode . --fix

# Analyze specific file
uv run deadcode . --dry foo.py

# Exclude directories
uv run deadcode . --exclude=venv,migrations

# Suppress false positives
uv run deadcode . --ignore-names="BaseTestCase,*Mixin"
```

For all options, see [cli-and-configuration.md](cli-and-configuration.md) or run `uv run deadcode --help`.

## Makefile (Legacy)

A `Makefile` exists for backwards compatibility. The Just targets mirror the Makefile commands. Use Just targets instead of Make.
