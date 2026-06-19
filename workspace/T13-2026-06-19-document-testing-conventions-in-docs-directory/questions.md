# Research Questions

## Context
Focus on the `tests/` directory, the test-support helpers (e.g.
`deadcode/utils/base_test_case.py`), the existing `docs/` directory, and the
project's automation files (`Makefile`, `Justfile`, `pyproject.toml`). The aim
is to understand how tests are currently organized, written, and executed, and
what is already documented about them.

## Questions
1. How is the `tests/` directory structured — what subdirectories and top-level
   test modules exist, and what naming patterns are used for test files,
   classes, and test methods across them?
2. What does the `BaseTestCase` helper provide, and how do test modules use it
   to define input files, mock filesystem/IO seams, and assert on results? Which
   tests deliberately bypass it and why?
3. What fixture data exists under `tests/files/`, and how do tests reference it
   (inline string files vs. on-disk fixtures vs. temporary directories)?
4. What practices keep the test suite deterministic and parallel-safe — for
   example handling of working directory, hash seed, sorting, and pytest-xdist
   worker behavior?
5. How are tests, coverage, linting, type checking, and complexity checks
   defined and invoked across the `Makefile`, `Justfile`, and `pyproject.toml`,
   and what are the relevant pytest/coverage settings?
6. What testing-related content already exists in the `docs/` directory (such as
   `docs/testing-and-tooling.md` and `docs/index.md`), and how are documents
   organized, cross-linked, and indexed there?
