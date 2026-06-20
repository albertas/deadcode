# Task

Migrate the Makefile and Justfile dependency management from the `uv pip`
(requirements.txt) workflow to the uv-native project workflow: replace the
`uv pip sync requirements*.txt` / `uv pip install -e .[test]` invocations with
`uv add` (sourcing the existing `requirements*.txt`) and add a `uv lock`
command/recipe to both files. The goal is to standardize on uv's project-level
dependency and lockfile management (`uv.lock`) instead of the compiled
requirements-file flow.
