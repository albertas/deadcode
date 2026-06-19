# Task

Make `ruff check deadcode/ tests/` pass cleanly while keeping most of Ruff's
lint rules enabled, so the project's lint gate (`just check-lint`) is green.
The Ruff config already selects `ALL` rules with a large `ignore` list; the work
is to fix the outstanding violations across the package and tests and to trim
that ignore list down so that "most" checks remain active rather than broadly
suppressed.

Why: this is the lint half of an ongoing code-quality audit (sibling to the
already-completed `ruff format` audit), establishing a clean, enforceable lint
baseline for the codebase.
