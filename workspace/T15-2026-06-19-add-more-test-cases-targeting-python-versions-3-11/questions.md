# Research Questions

## Context
Focus on the `deadcode/` package — especially the AST parsing entry point and
the visitor classes that walk parsed syntax trees — together with the `tests/`
suite, its shared `BaseTestCase` harness, and the project's build/CI
configuration (`pyproject.toml`, `Makefile`, `Justfile`, `.github/workflows/`).
The relevant concern is how source code is parsed and analyzed, and how the
test suite and tooling are configured around interpreter versions.

## Questions
1. How does the tool turn a source file into an abstract syntax tree
   (`parse_abstract_syntax_tree.py`) and which `ast` APIs, node types, and
   parsing options does it rely on?
2. Which AST node types and visitor methods does
   `find_unused_code_visitor.py` (and the other visitors) implement, and how are
   newer syntax constructs such as `match` statements, `type` alias statements,
   and PEP 695 generic parameters currently handled or skipped?
3. How is the `tests/` suite organized — what does `BaseTestCase` provide, how
   are source-code fixtures declared and run through the tool, and what
   conventions exist for adding a new test case?
4. Where in the codebase are Python-version assumptions encoded (declared
   minimum version, type-annotation syntax, standard-library calls, and any
   `sys.version_info` branches), and what is the lowest version the code targets?
5. How do the build and CI configurations (`Makefile`, `Justfile`,
   `.github/workflows/check.yml`, `pyproject.toml`) select and pin Python
   versions, and how is the test matrix wired to interpreter versions?
6. What coverage, lint, and type-check gates does `pyproject.toml` define
   (coverage threshold, mypy `python_version`, ruff target), and how would
   adding new test files interact with those gates?
