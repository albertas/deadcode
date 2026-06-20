# Research Questions

## Context
Focus on the `tests/frameworks/` scenario tests, the `BaseTestCase` harness in
`deadcode/utils/`, the argument-parsing layer in `deadcode/actions/`, the visitor
layer in `deadcode/visitor/`, and the testing/tooling documentation under `docs/`.
These areas cover how Deadcode discovers, ignores, and reports unused names, and how
existing framework scenario tests are written.

## Questions
1. How are the existing framework scenario tests in `tests/frameworks/` (FastAPI,
   SQLAlchemy, Alembic) structured — what does each test define as input files, which
   CLI options does it pass, and how does it assert on the resulting output?

2. What does the `BaseTestCase` helper provide for writing in-memory file fixtures,
   and how do mechanisms like `fix_indent`, file mocking, and the `main()` entrypoint
   work together so a test can run Deadcode over synthetic source without touching disk?

3. What suppression and ignore CLI options does the argument-parsing layer expose
   (e.g. `--ignore-names`, `--ignore-names-in-files`,
   `--ignore-definitions-if-decorated-with`, `--ignore-definitions-if-inherits-from`,
   `--ignore-bodies-if-*`), how are their values parsed, and what is the difference in
   effect between each option?

4. How does the visitor layer detect whether a class definition, base class,
   decorator-referenced name, or module-level assignment is used, and how do the
   inheritance-based and decorator-based ignore rules match against the code they
   suppress?

5. How does Deadcode handle references that appear as string literals, dotted
   attribute access, or other indirect/dynamic forms, and what known limitations or
   false-positive sources exist for names that are only referenced dynamically?

6. How are unused-code findings reported — what are the error codes (e.g. `DC01`,
   `DC02`), the message format, and the line/column convention — and what naming,
   grouping, and indentation conventions does the documentation prescribe for adding
   new test modules?
