# Design Discussion

## Current State

`deadcode` detects unused definitions with a single-pass AST visitor. Names are
sorted into two sinks: definitions via `_define()`
(`find_unused_code_visitor.py:273-327`) and uses via `add_used_name()` (`:88-96`).
The final report is computed by `_get_unused_items` (`ignore.py:39-42`) as
`[item for item in defined_items if item.name not in used_names]` — a **flat,
scope-blind string comparison**. `NestedScope` tracks usage counts and base-class
resolution but does **not** gate the reported set (`research.md` Cross-Cutting).

Routing is name-context driven (`visit_Name:501-505`): `Load`/`Del` → used;
`Param`/`Store` → defined as variable. Attributes match by **bare attr string**,
ignoring the receiver (`visit_Attribute:344-348`). Function parameters are **not**
registered — `visit_arg` is commented out (`:337-339`). Modern syntax has only one
dedicated handler, `visit_MatchClass` (`:526-529`); PEP 695 aliases/generics,
`match` captures, walrus, and f-strings rely on generic child traversal to reach
inner `Name` nodes (`research.md` Q2).

Suppression collapses into one mechanism: every ignore path adds the name to
`used_names` (`:325`), so membership in `used_names` is the single output filter.
Built-in heuristics (`ignore.py:74-106`), CLI flags via
`should_ignore_new_definitions` (`:531-558`), `__all__` (`:507-512`), `# noqa`
(`noqa.py`), and dynamic-usage heuristics (`getattr`/`hasattr`, `.format(**locals())`,
`% locals()`) all funnel through it. Six CLI flags are parsed but never consumed by
the visitor (`research.md` Open Areas).

Tests use `BaseTestCase` (`deadcode/utils/base_test_case.py`) with in-memory
`self.files` dicts; correctness is asserted on `main([...])`'s return string or
`None` (`research.md` Q5). Version gating is `@skipUnless(sys.version_info >= ...)`
on test classes, applied inconsistently (gated for PEP 695 at `test_type_alias.py:8`,
absent for `match`/walrus).

## Desired End State

A correctness audit report (`audit.md` or equivalent, decided in structure phase)
that enumerates each confirmed gap with: category (false positive / false
negative), reproduction, root cause with `file:line`, and severity. Each finding is
backed by a test in `tests/` that encodes the **correct** expected behavior.

Verification: `just test` runs green; new characterization tests pass and pin
current behavior; tests that expose real bugs are marked `@unittest.expectedFailure`
(or `@skip` with a finding reference) so they convert to regression guards the
moment a fix lands. `just check` (format, lint, complexity, typecheck) stays green.

## Patterns to Follow

- **Test scaffolding**: subclass `BaseTestCase`, set `self.files = {'foo.py': """..."""}`,
  call `main(['foo.py', '--no-color', ...])`, assert exact string or `None`
  (`tests/test_walrus.py:6-21`, `tests/test_match_statement.py`).
- **Positive + negative pair per construct**: one "is reported" + one "is not
  reported" test, as in `test_walrus.py` (`test_unused_walrus_target_is_reported`
  vs `test_used_walrus_target_is_not_reported`).
- **Version gating**: `@skipUnless(sys.version_info >= (3, 12), ...)` on the class
  for PEP 695 (`tests/test_type_alias.py:8`); add gates for any 3.10+/3.12+ syntax
  newly under test (the missing `match`/walrus gates are a pattern NOT to repeat).
- **Framework tests**: feed framework-shaped defs + one deliberately-unused helper,
  assert only the helper is reported, suppress via CLI flags
  (`tests/frameworks/test_django.py`), never the unwired `ignore_decorators`.
- **Exact-string assertion format**: `'foo.py:L:C: DCNN Type `name` is never used'`
  (`research.md` Q5); columns confirmed from real runs.

Patterns to flag as NOT to follow / suspect:
- `test_match_statement.py` "used capture" tests pass **vacuously** — match
  captures (`MatchAs`/`MatchStar`/`MatchMapping`) bind via `str` attrs, not `Name`
  nodes, so they are never tracked at all; the test is green for the wrong reason.
- Unconditional `@skip` on `test_accurate_usage_detection.py:7` hides intended
  coverage — investigate before relying on it.

## Design Decisions

1. **Scope = audit + regression tests, not fixes**: Per `task.md` ("so they can be
   fixed"), this effort confirms gaps and lands tests. Fixes are a separate effort,
   except trivial/safe ones may be proposed in the report. Avoids scope creep into
   risky visitor rewrites.
2. **Failing tests use `@expectedFailure`, not deletion/xskip-forever**: encodes
   desired behavior so the test flips to a guard on fix. Chosen over leaving the bug
   undocumented or asserting wrong behavior.
3. **Prioritize by blast radius**: rank flat-string scope-blindness (affects all
   methods/attrs/vars) highest; treat PEP 695 generic type-param and match-capture
   false negatives as lower severity. Audit covers all, tests focus on confirmed,
   reproducible cases.
4. **Characterization tests for correct-but-surprising behavior** (e.g. params never
   reported, attr bare-string matching) pin current behavior green, so an audit
   "is this a bug or by-design?" verdict is recorded either way.
5. **Confirm every claim by running `main()`**, not by reading source alone — the
   visitor's flat-set + suppression interactions are non-obvious; only execution
   proves a false positive/negative.
6. **No new dependencies, no source-layout changes** during audit; tests go in the
   existing `tests/` subdirectories matching their concern.

## Candidate Findings to Confirm (drive the audit)

- **F1 — Scope-blind flat matching** (`ignore.py:40`, `:325`): a use of name `x`
  anywhere marks every definition named `x` used. → false negatives across vars,
  methods, attributes. Highest severity.
- **F2 — Attribute receiver ignored** (`visit_Attribute:344-348`): any `.foo` Load
  marks all `.foo` attrs (and same-named funcs/vars) used. Cross-contamination.
- **F3 — Parameters never reported** (`visit_arg` commented, `:337-339`): unused
  function params undetected. Likely by-design; record verdict.
- **F4 — `match` captures untracked**: `MatchAs`/`MatchStar`/mapping rest bind via
  `str` attrs → genuinely unused captures undetected; existing tests vacuous.
- **F5 — PEP 695 generic type params**: `def f[T]` `T` is a `TypeVar.name` str, not
  a `Name` → unused type params undetected (false negative). Low severity.
- **F6 — Dynamic-usage heuristic boundaries** (`visit_Call:364-413`): non-literal
  `getattr` attr args, `format(**vars())`, qualified `builtins.getattr` → false
  positives possible.
- **F7 — Six parsed-but-unused CLI flags** (`parse_arguments.py:60-149`): silently
  no-op; users expecting suppression get false positives. Report as a gap.

## What We're NOT Doing

- Not rewriting the visitor into a two-pass / scope-resolved analyzer.
- Not fixing confirmed bugs in this effort (separate, gated by the audit).
- Not wiring up the six dead CLI flags.
- Not auditing `--fix` removal correctness (separate concern from detection).
- Not adding new frameworks beyond Django/FastAPI/SQLAlchemy/Alembic.
- Not changing CI, packaging, or the `Justfile`.

## Open Risks

- **Vacuous-pass tests**: some new "not reported" assertions may pass for the wrong
  reason (as F4 shows). Mitigate by also asserting a *defined-and-unused* sibling of
  the same name **is** reported, proving the mechanism actually ran.
- **Version-dependent syntax**: `match`/PEP 695 tests need correct `skipUnless`
  gates; the host interpreter version determines what `ast.parse` accepts.
- **Column-number assertions** are brittle; confirm each from a real run before
  hardcoding (per `test_walrus.py:20` note).
- **By-design vs bug ambiguity** (F3 especially): some "gaps" may be intentional;
  the audit must state a verdict rather than assume a bug.
