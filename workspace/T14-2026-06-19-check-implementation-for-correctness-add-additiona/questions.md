# Research Questions

## Context
Focus on the `deadcode/` package: the AST-walking visitor that collects defined
names and their usages (`deadcode/visitor/find_unused_code_visitor.py`,
`deadcode/visitor/utils.py`, `deadcode/visitor/lines.py`), the fix/removal
pipeline (`deadcode/visitor/fix_unused_code_visitor.py`,
`deadcode/actions/remove_file_parts_from_content.py`,
`deadcode/actions/merge_overlaping_file_parts.py`), the ignore/noqa layer
(`deadcode/visitor/ignore.py`, `deadcode/visitor/noqa.py`), CLI/config parsing
(`deadcode/actions/parse_arguments.py`), and the `tests/` suite that exercises
them.

## Questions
1. How does the unused-code detection visitor traverse the AST to collect
   defined names and record their usages, and which categories of names
   (functions, classes, methods, variables, imports, attributes, properties)
   does it track and distinguish?

2. By what logic and data structures is a defined name classified as "used"
   versus "unused," and what scoping, string-reference, dunder, or dynamic-usage
   edge cases are explicitly handled or explicitly documented as limitations?

3. How does the fix pipeline turn detected unused code into edits — how are file
   parts (line/column ranges) computed, how are overlapping parts merged, and
   how is the remaining file content reassembled after removal?

4. How do the ignore and noqa mechanisms work — what configuration options,
   name/file patterns, decorators, and inline comment forms suppress findings,
   and at which stage of the pipeline are they applied?

5. How are command-line arguments and configuration (including `pyproject.toml`
   / config files) parsed, validated, and normalized, and which options change
   detection or fix behavior?

6. How is the test suite organized and what assertion conventions does it use —
   how do `BaseTestCase`, the mock filesystem layer, and the per-area test
   directories assert detection accuracy and fix correctness, and what input
   constructs are currently covered versus absent?
