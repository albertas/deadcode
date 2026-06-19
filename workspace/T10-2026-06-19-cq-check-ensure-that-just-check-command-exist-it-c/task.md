# Task

Ensure the project's `Justfile` provides a single `check` recipe that combines
all code-quality checks (format check, lint, complexity, typecheck) and the test
suite, and that running `just check` passes cleanly. This gives a one-command
quality gate for contributors and CI.
