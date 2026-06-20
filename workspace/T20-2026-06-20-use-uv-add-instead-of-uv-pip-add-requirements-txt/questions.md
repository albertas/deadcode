# Research Questions

## Context
Focus on the project's build and dependency-management tooling: the `Makefile`,
the `Justfile`, the GitHub Actions workflow under `.github/workflows/`, and the
dependency-related configuration in `pyproject.toml` (including `uv.lock`,
`requirements.txt`, and `requirements-dev.txt`). The area of interest is how
the environment is created and how dependencies are installed, synchronized,
locked, and compiled.

## Questions
1. Which `uv` subcommands does each recipe in the `Makefile` and `Justfile`
   invoke for environment creation, dependency installation, synchronization,
   and compilation, and what are the exact arguments and target files?
2. What is the relationship between `pyproject.toml`, `requirements.txt`,
   `requirements-dev.txt`, and `uv.lock` — how is each file generated, what
   consumes it, and how do they stay in sync?
3. How does the GitHub Actions CI workflow set up its environment and install
   dependencies, and which `Makefile`/`Justfile` recipes (and arguments) does
   it rely on?
4. How is the project's own package (editable install) and its optional `test`
   extras made available to the test, lint, type-check, and `check` recipes?
5. What `uv`-related configuration exists in `pyproject.toml` (for example,
   custom package indexes, `tool.uv` settings) that affects dependency
   resolution, installation, or locking?
6. Where do the `Makefile` and `Justfile` overlap or diverge in their
   dependency-management recipes (for example, Python-version pinning, `.venv`
   creation, and the `sync`/`lifecycle` recipes)?
