# Research Questions

## Context
Focus on the `deadcode/` Python package, which is a command-line tool that
detects (and optionally removes) unused Python code via abstract-syntax-tree
analysis. Relevant areas include the CLI entry point (`cli.py`), the `actions/`
pipeline, the `visitor/` AST-traversal layer, the `utils/` helpers, the shared
`data_types.py`/`constants.py` modules, project configuration in
`pyproject.toml`/`README.md`, and the `tests/` tree. The aim is to understand
how the whole system fits together end to end.

## Questions
1. What is the top-level execution flow from the command-line entry point
   (`cli.py`) through to producing output or modifying files? Trace which
   functions/modules are invoked in order and what each returns.
2. How are command-line arguments and `pyproject.toml` settings parsed, merged,
   and represented (e.g. in `parse_arguments.py` and `data_types.py`)? What
   options exist and how do they flow into the rest of the system?
3. How does the AST-traversal layer in `visitor/` work — how are abstract syntax
   trees parsed, which visitors collect defined vs. used names, and how are
   scopes, `noqa`, and ignore rules handled?
4. How does the tool decide which names are "unused", and how are the various
   ignore/exclude mechanisms (ignore-names, ignore-bodies, ignore-definitions,
   inheritance/decorator-based rules) applied to filter results?
5. How is the fix/output stage implemented — how are unused code locations turned
   into removable file parts, merged, removed from file contents, and rendered as
   error messages or diffs (the `fix_or_show_unused_code`,
   `remove_file_parts_from_content`, `merge_overlaping_file_parts`,
   `get_unused_names_error_message` modules)?
6. What shared data structures and constants (in `data_types.py`, `constants.py`,
   `visitor/code_item.py`) carry state between stages, and what are their key
   fields and roles?
7. How is the codebase organized for testing and tooling — what is the layout of
   the `tests/` tree, what helpers/base cases exist, and what build/run/lint
   commands are defined (`Justfile`, `Makefile`, `pyproject.toml`)?
