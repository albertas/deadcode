# Research Questions

## Context
Focus on the `deadcode/` Python package and its sibling `tests/` suite, plus the
project's tooling configuration in `pyproject.toml` and `Justfile`. Relevant
areas include type-annotation usage across modules, the `# noqa` directive
parser in `deadcode/visitor/`, exception/error-raising conventions, and the
test harness that drives the modules. The package targets Python 3.11+.

## Questions
1. How are type annotations expressed across the package? Which modules import
   names such as `Optional`, `Union`, `List`, `Dict`, `Tuple` from the `typing`
   module, where do these annotations appear (function signatures, variables,
   class attributes), and does any module rely on `from __future__ import
   annotations` or on annotations being evaluated at runtime?

2. How does `deadcode/visitor/noqa.py` define and parse `# noqa` directives?
   What regular expression and code formats does it accept (including the
   project's own `DC0x`-style error codes), how do the visitor modules consume
   `parse_noqa` / `ignore_line`, and where do intentionally malformed or
   fixture-like noqa strings appear in the source and tests?

3. What conventions does the codebase use for raising and handling exceptions —
   how are error messages constructed and passed to exception constructors, are
   there custom exception classes, and where are broad `except` clauses (e.g. in
   AST parsing) used and why?

4. Where do imports, local variables, or unpacked assignments exist that are not
   subsequently referenced, and are any of them intentional (re-exports,
   placeholder unpacking, or names deliberately kept)? How do the package's
   `__init__.py` files and public surface relate to this?

5. How is the project's static-analysis and quality tooling configured and
   invoked? Describe the structure of the Ruff configuration in `pyproject.toml`
   (the `select`/`ignore` lists and `per-file-ignores`), and the `Justfile`
   recipes used to run lint, format, type-check, and test the codebase.

6. What patterns exist for string and collection manipulation and simple
   control flow — for example splitting static string literals, building lists
   or sets, and functions that return boolean values via if/else branches?

7. How is the test suite structured and how does it verify module behavior?
   Describe the `BaseTestCase` harness, the inline source-string fixtures, the
   directory layout under `tests/`, and how a contributor runs the full suite.
