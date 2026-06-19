# Research Questions

## Context
Focus on the `tests/` directory, the shared test infrastructure in
`deadcode/utils/base_test_case.py`, and the test/coverage configuration in
`pyproject.toml`, the `Justfile`, and the `Makefile`. Also examine the I/O
boundaries in the `deadcode/` source package (file reading/writing, directory
walking, and configuration discovery).

## Questions
1. How is the test suite invoked and configured across the project (runner
   commands, parallelism flags, coverage options), and in which files are those
   settings defined?
2. How does the shared base test case set up its mocks (file I/O, filesystem
   helpers, removal), what assertion helpers does it provide, and which test
   modules inherit from it versus defining their own setup?
3. Which test modules read or write real files, depend on the current working
   directory, or otherwise touch the live filesystem, and how do they locate the
   inputs they operate on?
4. Where in the `deadcode/` source package do I/O boundaries occur (opening
   files, walking directories, discovering and reading configuration), and does
   any source or test code contact the network or external services?
5. What sources of non-determinism exist in the source's runtime data
   structures and produced output (e.g. set/dict iteration order, sorting,
   reliance on hash ordering)?
6. How are test input fixtures and sample files organized and shared, and is
   there any shared mutable state (class-level attributes, module globals,
   caches) that persists across individual tests?
