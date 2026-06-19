# Research Questions

## Context
Focus on the `deadcode/` Python package — specifically `deadcode/actions/`
(notably `remove_file_parts_from_content.py` and `fix_or_show_unused_code.py`)
and `deadcode/visitor/` (notably `find_unused_code_visitor.py` and the
`fix_indent` helper) — plus the project's ruff configuration in `pyproject.toml`
and the `Justfile` recipes. Also look at how `tests/` exercises these modules.

## Questions
1. How is ruff's lint configuration set up in `pyproject.toml` (including any
   mccabe / `max-complexity` setting, the `select`/`ignore` lists, and
   per-file ignores), and how do the `Justfile` recipes — particularly
   `check-complexity` — invoke ruff?

2. Trace the control flow of `remove_file_parts_from_content` in
   `deadcode/actions/remove_file_parts_from_content.py`: what inputs does it
   take, what branches and loops does it contain, and what helper functions or
   data types (e.g. `Part`) does it rely on?

3. Trace the `visit` method in
   `deadcode/visitor/find_unused_code_visitor.py`: what node types and
   conditions does it dispatch on, what other methods does it call, and how
   does it fit into the AST-visiting flow of the class?

4. Trace `fix_or_show_unused_code` in
   `deadcode/actions/fix_or_show_unused_code.py`: what decisions and branches
   does it make, and which other actions/functions does it coordinate?

5. Where is `fix_indent` defined, what does it do, and what branching logic
   does it contain? What other helpers live alongside it in the same module?

6. How do tests in `tests/` cover these four functions/modules — which test
   files target them, what behaviors are asserted, and what fixtures or helper
   utilities (e.g. base test cases) are used?
