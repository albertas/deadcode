# Deadcode Architecture Guide

**Deadcode** is a static analysis tool that detects unused Python code by analyzing abstract syntax trees. Unlike scope-limited checkers like Ruff (which detect unused local variables `F823`, `F841`), Deadcode performs two AST passes to find unused definitions at any scope—functions, classes, imports, module-level variables—and can optionally remove them. It is meant to be used alongside other static analysis tools for comprehensive dead code detection across a codebase.

The tool accepts Python file paths, processes them through a five-stage pipeline (argument parsing, file discovery, AST analysis, optional fix/diff generation, and error reporting), and emits either a list of unused items or a unified diff showing suggested removals.

For installation, usage examples, and CLI reference, see [README](../README.md).

## Documentation index

- [Architecture & pipeline flow](architecture.md) — the five-stage pipeline from `cli.main` to output.
- [CLI & configuration](cli-and-configuration.md) — argument parsing, `pyproject.toml` merge, `Args`.
- [Visitor layer](visitor-layer.md) — AST parsing, defined/used collectors, scopes, noqa.
- [Unused detection & ignoring](unused-detection-and-ignoring.md) — how "unused" is decided; ignore mechanisms.
- [Fix & output](fix-and-output.md) — merge/remove `Part`s, diff rendering, error messages.
- [Data types](data-types.md) — `Args`, `Part`, `CodeItem`, constants & error codes.
- [Testing & tooling](testing-and-tooling.md) — `tests/` layout, `BaseTestCase`, Make/Just.
