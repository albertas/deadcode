# Task: Audit cyclomatic complexity stays <= 8

Enforce a McCabe cyclomatic complexity ceiling of 8 across the `deadcode/`
package (the project's "app/") and `tests/`, verified via `just check-complexity`
(`ruff check --select C901`). This requires configuring the complexity threshold
to 8 and refactoring the functions that currently exceed it so the check passes
cleanly.

Note: the ticket says "app/" but this project's source package is `deadcode/`;
the Justfile `check-complexity` target already targets `deadcode/ tests/`. At
threshold 8 the offending functions are `remove_file_parts_from_content`,
`visit` (find_unused_code_visitor), `fix_or_show_unused_code`, and `fix_indent`.
