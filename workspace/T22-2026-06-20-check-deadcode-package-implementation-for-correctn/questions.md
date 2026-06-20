# Research Questions

## Context
Focus on the `deadcode/` package, primarily the AST visitor layer
(`deadcode/visitor/`) and the analysis actions (`deadcode/actions/`), plus the
test suite under `tests/`. The relevant concerns are how names are classified as
defined versus used, how modern Python syntax nodes are traversed, how
suppression/ignore rules work, and how all of this is exercised by tests.

## Questions
1. In `FindUnusedCodeVisitor`, trace how a name becomes a "definition" versus a
   "use": which `visit_*` methods call `_define()`/`_define_variable()` and which
   call `add_used_name()`, and how AST contexts (`ast.Load`, `ast.Store`,
   `ast.Del`, `ast.Param`) and scope tracking via `NestedScope` route a node to
   each path?

2. How are modern Python syntax constructs handled during traversal — PEP 695
   `type` aliases and generic `[T]` parameters (3.12+), structural pattern
   matching / `match` statements, the walrus operator, f-strings/`JoinedStr`,
   `async def`, and `# type:` comments — and which of these have dedicated
   `visit_*` methods versus relying on generic child traversal to reach inner
   `Name` nodes?

3. What ignore and suppression mechanisms exist (e.g. `_ignore_*` predicates in
   `visitor/ignore.py`, decorator-based ignoring, `--ignore-names`,
   `--ignore-definitions-if-inherits-from`, `__all__` exports, `# noqa`), and at
   what point in the pipeline does each one prevent a definition from being
   reported as unused?

4. How does the code special-case dynamic-usage patterns such as
   `getattr`/`hasattr` string arguments, `"{}".format(**locals())`, and
   `"%(x)s" % locals()`, and what are the boundaries of these heuristics?

5. How is the test suite organized for correctness coverage — the structure of
   `tests/` (including `tests/frameworks/` and the modern-syntax test files), how
   version-specific syntax is gated (e.g. `skipUnless` on `sys.version_info`),
   what the shared `BaseTestCase` provides, and what assertion patterns are used
   to confirm a name is or is not reported?

6. For each supported framework (Django, FastAPI, SQLAlchemy, Alembic), what
   specific definition patterns do the existing tests cover, and which
   suppression mechanism (decorator whitelist, inheritance-based ignore, name/file
   ignore, etc.) is relied upon to avoid false positives for that framework?
