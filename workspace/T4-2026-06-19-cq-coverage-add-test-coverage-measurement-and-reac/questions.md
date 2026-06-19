# Research Questions

## Context
Focus on the `deadcode/` Python package and its `tests/` suite. Relevant areas
include the test runner and coverage configuration (`pyproject.toml`,
`Justfile`, `Makefile`, CI workflows under `.github/`), the layout of the source
modules under `deadcode/` (actions, visitor, utils), and the conventions used by
the existing test files and shared test helpers.

## Questions
1. How is the test suite currently run and configured — what does the
   `[tool.pytest.ini_options]` `addopts` in `pyproject.toml`, the `Justfile`
   test recipe, the `Makefile`, and any CI workflow specify about `pytest-cov`,
   coverage source, omit/exclude rules, and fail-under thresholds?

2. What is the current measured line coverage of the `deadcode/` package, and
   which modules and specific code paths report as uncovered when the suite is
   run with coverage reporting enabled?

3. How are the modules under `deadcode/` organized (actions, visitor, utils,
   cli, constants, data_types), what is each module's public entry point, and
   how does control flow move from the CLI through argument parsing into the
   core analysis actions?

4. How is the existing `tests/` directory structured (subdirectories per
   concern, naming conventions, file layout), and what categories of behavior
   do the current test files exercise?

5. What shared test infrastructure exists — for example
   `deadcode/utils/base_test_case.py`, fixtures, and helper utilities — and what
   patterns do existing tests use to construct inputs and assert on results?

6. Which source files or code paths are explicitly excluded from analysis or
   coverage (for example via `[tool.deadcode]` `exclude`/`ignore_names`,
   `# pragma: no cover`, or coverage omit settings), and where are those
   exclusions declared?
