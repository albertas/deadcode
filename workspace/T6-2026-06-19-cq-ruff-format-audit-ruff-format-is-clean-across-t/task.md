# Task

Audit that `ruff format` is clean across the codebase by running `just check-format`
(`uv run ruff format --check deadcode/ tests/`). The goal is to confirm every Python
source file is already formatted, and to apply `just format` and commit any fixes only
if the check reports unformatted files.
