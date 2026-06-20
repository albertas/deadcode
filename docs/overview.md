# Development Documentation Index

This is the index of development and build documentation for Deadcode. For usage of the Deadcode tool itself, see [index.md](index.md).

## Documentation Set

| File | Purpose |
|------|---------|
| [invocation.md](invocation.md) | Development targets via Just: how to run tests, linting, type checks, formatting, and the comprehensive check pipeline. |
| [architecture.md](architecture.md) | The five-stage pipeline that forms the core of the Deadcode analysis tool (code parsing, file discovery, AST analysis, fix/diff generation, error reporting). |
| [cli-and-configuration.md](cli-and-configuration.md) | Deadcode CLI flags, argument parsing, and configuration via `pyproject.toml`. |
| [testing-and-tooling.md](testing-and-tooling.md) | Testing setup, test file organization, test coverage measurement, version-gating for 3.12+ syntax features, and Make/Just integration. |
| [visitor-layer.md](visitor-layer.md) | AST traversal, scope tracking, and ignore rule mechanics. |
| [unused-detection-and-ignoring.md](unused-detection-and-ignoring.md) | How unused code is identified and how to suppress findings. |
| [fix-and-output.md](fix-and-output.md) | The fix/diff generation and output formatting pipeline. |
| [data-types.md](data-types.md) | Type definitions used throughout the codebase. |

## Quick Start

To develop Deadcode:

1. **Sync dependencies:** `just sync` (installs dev dependencies from `requirements-dev.txt`)
2. **Run all checks:** `just check` (tests + lint + format check + type check + complexity check)
3. **Run specific checks:**
   - Tests: `just test`
   - Linting: `just lint` or check-only `just check-lint`
   - Formatting: `just format` or check-only `just check-format`
   - Type checking: `just typecheck` or check-only `just check-typecheck`
   - Complexity: `just check-complexity`
4. **Apply fixes:** `just format` then `just lint -- --fix`
5. **Update lockfile:** `just lock` (refreshes `uv.lock`)

For details on each target, see [invocation.md](invocation.md).
