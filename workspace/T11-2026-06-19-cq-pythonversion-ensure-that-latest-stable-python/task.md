# Task

Ensure the `deadcode` project targets and is validated against the latest stable
Python version. Today the project's Python-version declarations are scattered and
inconsistent across metadata and tooling (e.g. `requires-python`, trove
classifiers, mypy `python_version`, ruff/black `target-version`, the Makefile
venv pin, and CI that still runs only Python 3.8), so these need to be reconciled
to a single up-to-date supported version range with the latest stable Python
included and verified in CI.
