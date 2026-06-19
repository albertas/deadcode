# Research Questions

## Context
Focus on the `deadcode` package's code-removal and diff-rendering pipeline
(`deadcode/actions/`, `deadcode/visitor/`, `deadcode/utils/`) and the test suite
under `tests/` — especially `tests/cli_args/test_dry.py`,
`tests/cli_args/test_fix.py`, and
`tests/fix/test_unused_imports_in_a_single_file.py`. Also examine the test
runner configuration and shared test helpers.

## Questions
1. How is the test suite configured and run (pytest settings in
   `pyproject.toml`, `just test`, xdist, markers, skipped tests), and what shared
   fixtures, base classes, or helpers (e.g. `base_test_case`, `fix_indent`) do
   the tests rely on to set up files and assert output?

2. Trace the end-to-end flow from invoking `main()` to producing the unused-name
   report and the diff: which modules in `deadcode/actions/` and
   `deadcode/visitor/` are involved, and how do `--dry` and `--fix` change the
   output?

3. How does the code that removes unused code parts from file content work
   (`remove_file_parts_from_content.py`, `merge_overlaping_file_parts.py`,
   and the `fix_unused_code_visitor`), and how are line/column ranges for a
   removal computed?

4. How are `with` statements and their `as <name>` optional-vars handled during
   unused-variable removal — what code identifies the removable span, and what is
   the resulting rewritten line?

5. How are unused imports and aliased imports (`import x as y`,
   `from m import a as b`) detected and removed, particularly within
   parenthesized multi-name `from` imports?

6. How is the colored unified diff generated and formatted
   (`add_colors_to_diff.py` and surrounding code), and how are ANSI color codes
   and empty/blank lines treated in the rendered diff?

7. What exact output do the three failing tests assert versus what the current
   code produces, and which behavior is documented as intended in `docs/`,
   README, or `notes`?
