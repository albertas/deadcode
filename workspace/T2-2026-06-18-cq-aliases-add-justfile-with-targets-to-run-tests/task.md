# Task

Add developer-workflow targets to the project's `Justfile` so contributors can
run tests, `ruff format`, `ruff` lint, `mypy` typecheck, a code-complexity check
(`ruff --select C901`), and a combined `check` target that runs them all. Add
any dev dependencies these targets require (notably `pytest-xdist` for the
parallel `pytest -n` test run) so the targets work out of the box.
