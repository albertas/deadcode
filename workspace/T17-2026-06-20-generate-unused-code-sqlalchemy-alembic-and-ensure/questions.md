# Research Questions

## Context
Focus on the `deadcode/` package's unused-code detection and ignore/suppression
mechanisms, the `tests/frameworks/` scenario-test directory and the
`BaseTestCase` testing helper, and the `pyproject.toml` / README / `docs/`
configuration surface. The relevant areas are how findings are produced, how the
various ignore options filter them, and how scenario tests are written.

## Questions
1. How are scenario tests under `tests/frameworks/` structured — how do they
   build fixture files, invoke `main()`, pass CLI options, and assert on the
   exact finding output (path:line:col and DC codes)? What does `BaseTestCase`
   provide and how is the assertion format determined?

2. How are the `--ignore-definitions*`, `--ignore-bodies*`, `--ignore-names`,
   and `--ignore-names-in-files` options parsed, stored, and applied to suppress
   findings? Which of the declared ignore options are actually consumed in the
   visitor layer and which are declared but never applied?

3. How does the detector record and match a definition's base classes
   (including imported or multi-level inheritance) for the "inherits-from" style
   filtering? Trace the inheritance-tracking code path.

4. How does the detector record and match decorators on definitions, including
   dotted decorators and decorator calls (e.g. `@x.y(...)`), for the
   "decorated-with" style filtering?

5. How are module-level variable assignments, and functions or methods that are
   never referenced anywhere in the analyzed source, classified by the detector?
   What built-in rules already suppress certain names (test files, dunder
   methods, underscore-prefixed names, star/`__init__` imports, etc.)?

6. How are ignore options expressed in `pyproject.toml` under `[tool.deadcode]`
   and merged with CLI arguments, and how do the README and `docs/` present
   framework-specific configuration guidance?
