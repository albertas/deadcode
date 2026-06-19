# Research Questions

## Context
Focus on this Python project's metadata, tooling configuration, build/dev
workflow, and CI. Relevant areas include `pyproject.toml`, the `Makefile` and
`Justfile`, the `requirements*.txt` files, the `.github/workflows/` directory,
the `README.md`/`docs/`, and any source code that depends on standard-library
behavior that varies by interpreter version.

## Questions
1. Across all project configuration (`pyproject.toml` and any other config
   files), where is the supported Python version declared or pinned — including
   `requires-python`, trove classifiers, mypy `python_version`, ruff/black
   `target-version`, and build-backend settings — and what value does each hold?
2. How is the Python interpreter version selected for the local development and
   build environment (e.g. `Makefile`, `Justfile`, `uv`, virtualenv creation),
   and which version(s) do those recipes pin or assume?
3. What CI/CD workflows exist under `.github/workflows/`, which Python
   version(s) do they install and run checks against, and is there any
   version matrix or multi-version testing mechanism?
4. How does the codebase parse TOML configuration, which module/library does it
   import for that, and what TOML-related entries appear in the dependency lists
   (`pyproject.toml` dependencies, `requirements.txt`, `requirements-dev.txt`)?
5. Does any source or test code branch on or otherwise depend on the Python
   interpreter version (e.g. `sys.version_info`, `__future__` imports,
   try/except-guarded stdlib imports, version-specific syntax), and if so where?
6. What do the `README.md`, `docs/`, and changelog say about which Python
   versions are supported, and what is the history of adding or dropping
   version support?
