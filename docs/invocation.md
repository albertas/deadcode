# Development Targets & Invocation

This document describes how to invoke the development targets via Just and the Deadcode CLI. See [overview.md](overview.md) for the documentation index.

## Dependency Synchronization

Before running any development target, sync dependencies:

```bash
just sync
```

This runs:
- `uv add --requirements requirements-dev.txt` — Installs pinned dev dependencies from `requirements-dev.txt`

All other targets depend on `sync`, so it runs automatically if needed.

## Dependency Locking

To update and refresh the `uv.lock` lockfile after modifying dependencies:

```bash
just lock
```

This runs `uv lock` to update the lockfile with the latest resolved dependency tree.

## Testing

### Run all tests

```bash
just test
```

Runs pytest via xdist with:
- **Parallel execution** on all-but-one CPU cores via `nproc --ignore=1`
- **Coverage measurement** with reports and enforced 95.0% threshold
- **Deterministic execution** — tests pass regardless of cwd, `PYTHONHASHSEED`, or worker count

### Run specific tests

```bash
just test tests/path/to/test_file.py
just test -- -k "test_name" -vv
```

Coverage and parallel execution still apply. Pass `-- <args>` to forward arguments to pytest.

### Running Tests from Any Directory

All tests are designed to be deterministic and can be run from any working directory:

```bash
cd /tmp && uv run pytest /path/to/deadcode/tests
cd /tmp && PYTHONHASHSEED=random uv run pytest -p xdist -n auto /path/to/deadcode/tests
```

Both commands succeed, confirming deterministic behavior across different environments.

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

The codebase is kept **ruff-clean**: `just check-lint` exits 0 with zero output when the tree is in compliance. Ruff runs with `select = ["ALL"]` and actively enforces ~85% of ruff's rules; the remaining 15% are deliberate policy ignores for docstrings, test utilities, print-based CLI output, and complexity management. All ignore entries are tied to active project policies, not past violations.

### Type checking

```bash
just typecheck
```

Runs `mypy` in strict mode on `deadcode/` (not `tests/`). Reports type errors.

```bash
just check-typecheck
```

Reports type errors without modifying files and must exit with zero errors. This is the gating check; any type error fails the gate.

The codebase is fully type-checked in strict mode: visitor methods use concrete AST node types (e.g., `visit_ClassDef(node: ast.ClassDef)`), all function signatures are annotated with correct return types, and position attributes on AST nodes are accessed via `typing.cast` where needed. The gate enforces zero type errors, zero suppression comments (`# type: ignore`), and correct use of type-equivalent constructs throughout the pipeline.

### Complexity check

```bash
just check-complexity
```

Runs `ruff check --select C901` to report McCabe complexity violations (complexity > 8, per `pyproject.toml`). This check is part of the gating `just check` pipeline. All functions must have a cyclomatic complexity of 8 or less.

## Comprehensive Check Pipeline

```bash
just check
```

Runs all checks in order and fails on any error:

1. `check-format` — Ensures code is formatted
2. `check-lint` — Ensures lint passes
3. `check-complexity` — Ensures no function complexity > 8
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

## Additional Development Targets

In addition to the core targets above, Just provides additional development targets:

### Security Audit

```bash
just audit
```

Runs `pip-audit` to scan for known security vulnerabilities in dependencies.

### Self-Check (Deadcode Detection)

```bash
just deadcode
```

Runs Deadcode on itself to detect unused code in the `deadcode/` and `tests/` directories. This ensures the tool passes its own quality checks.

### Build & Publish

```bash
just publish
```

Builds distribution packages (`uv run hatch build`) and publishes them to PyPI (`uv run hatch publish`). Cleans the `dist/` directory before building.

### Compile Requirements

```bash
just compile
```

Refreshes `requirements.txt` and `requirements-dev.txt` from the current `pyproject.toml` using `uv pip compile`.
