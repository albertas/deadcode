# Research Questions

## Context
Focus on the test suite under `tests/` (especially the fixture files in
`tests/files/`, the integration tests in `tests/test_deadcode.py`, and the
CLI-option tests in `tests/cli_args/`) and on the analysis core under
`deadcode/visitor/` and `deadcode/actions/`. The relevant concerns are how test
cases are authored and run, how the analyzer decides a name is used vs. unused,
and how decorators and ignore-options influence that decision.

## Questions
1. How are unused-code test cases currently structured and executed — what is the
   role of `tests/files/` fixture modules versus the inline-`files`-dict approach in
   `BaseTestCase`, and how does a test assert which names are reported?
2. How does the visitor layer (`deadcode/visitor/`) decide that a defined name is
   "used"? Trace how definitions and references are collected and matched, including
   how functions, methods, classes, and module-level names are distinguished.
3. How are decorators parsed and handled during analysis — what does
   `get_decorator_name` produce, and how do `visit_FunctionDef`/`visit_ClassDef`
   treat decorated definitions?
4. What command-line and `pyproject.toml` options exist for suppressing false
   positives (e.g. `--ignore-decorators`, `--ignore-names`, `--ignore-names-in-files`,
   `--ignore-definitions`), and how is each one wired from argument parsing through
   to the visitor's matching logic?
5. What kinds of definitions does the analyzer treat as implicitly used or exempt
   from reporting (for example dunder methods, `@property`, names matching built-in
   exemptions), and where in the code are those exemptions applied?
6. What error-code categories (DC01, DC02, DC03, …) does the tool emit, and how is
   the reported message and source location for each finding produced and formatted?
7. What existing documentation or notes describe framework recognition or
   configuration-based handling of framework entrypoints, and what do they say about
   how such cases are expected to be supported?
