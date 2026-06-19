# Design Discussion

## Current State

`deadcode` parses each source file with a single call:
`ast.parse(file_content, filename=filename, type_comments=True)`
(`deadcode/actions/parse_abstract_syntax_tree.py:9`). That call runs on the
**interpreter executing the tool** — there is no version-target option. A bare
`except:` (`parse_abstract_syntax_tree.py:10`) swallows *any* failure, prints
`Error: Failed to parse ...` and returns an empty
`ast.Module(body=[], type_ignores=[])` (`:13`). Consequence: syntax newer than
the running interpreter produces **zero findings**, not an error.

Traversal is fully overridden — `FindUnusedCodeVisitor.visit` (`:588-618`) never
calls `generic_visit`; it pre-dispatches, then **always** recurses into every
child via `_visit_children` (`:570-581`), then post-dispatches. So unknown/new
node types (`Match`, `TypeAlias`, PEP 695 `type_params`, `NamedExpr`) are still
*walked*, but only the enumerated `visit_*` methods do specialized usage
tracking (`find_unused_code_visitor.py:344-523`). `FixUnusedCodeVisitor`
behaves the same (`fix_unused_code_visitor.py:430-451`).

What is **specialized today**: `visit_MatchClass:523` (marks `kwd_attrs` used);
walrus targets land on `visit_Name:497` as Store. What is **not specialized**:
`Match`/`case` patterns (`MatchValue/As/Or/Mapping/Star/Singleton/Sequence`),
`type X = ...` aliases (`ast.TypeAlias`, 3.12), and PEP 695 generics
(`ast.TypeVar/ParamSpec/TypeVarTuple`, 3.12).

Tests use `BaseTestCase` (`deadcode/utils/base_test_case.py:10`): set
`self.files` (fake filename → source), call `main([...])`, assert the return
value and/or `assertFiles`/`assertUpdatedFiles`. `main` returns `None` when
nothing is found *or* on a swallowed syntax error, and a `path:line:col: DCxx`
string otherwise (`base_test_case.py:59-95`). **No existing test** embeds literal
`match`/`case`, walrus, `type` alias, or PEP 695 syntax — the one match test
sidesteps it with `SimpleNamespace`
(`tests/visitor/test_find_unused_code_visitor.py:102-106`).

Version policy is uniformly **3.11**: `requires-python = ">= 3.11"`
(`pyproject.toml:9`), CI matrix `["3.11","3.12","3.13","3.14"]`
(`.github/workflows/check.yml:19`), mypy `python_version = "3.11"`
(`pyproject.toml:165`). The only hard 3.11 floor is `tomllib`
(`parse_arguments.py:6`). No `sys.version_info` branches exist anywhere.

## Desired End State

A new suite of `BaseTestCase` tests that drive real, literal version-specific
syntax through `main(...)` and assert correct dead-code detection for:
`match`/`case` (3.11-safe), walrus `:=` (3.11-safe), `type` aliases (3.12+),
and PEP 695 generic parameters on functions/classes/aliases (3.12+). Any
genuine implementation incompatibility surfaced by these tests is fixed in
`deadcode/`.

**Verification**: `just check` (or `make check`) passes on each interpreter in
the 3.11–3.14 matrix. On 3.11, the 3.12+ tests are skipped (not failed); on
3.12+ they run and pass. Coverage stays ≥ 95% (`pyproject.toml:215`).

## Patterns to Follow

- **Test structure**: subclass `BaseTestCase`, populate `self.files`, call
  `from deadcode.cli import main; main([...])`, assert on the return string.
  Model on `tests/test_imports.py:59-67` and
  `tests/visitor/test_find_unused_code_visitor.py:16` (functional, not
  AST-unit, so the whole parse→visit→report pipeline is exercised).
- **Fixtures as indented triple-quoted strings** — `fix_indent`
  (`deadcode/utils/fix_indent.py:25`) strips the common margin, so write
  fixtures at natural indentation (see `tests/fix/test_assign.py:11-32`).
- **Fix-path tests**: use `--fix` and `assertFiles`/`assertUpdatedFiles`
  (`tests/fix/test_class_def.py:37-59`).
- **Relaxed test lint profile** is already in place for `tests/*` (`S101`,
  `PT009`, `ANN201`, `SLF001`, `D` ignored — `pyproject.toml:153-160`), so bare
  `assert`, no annotations, no docstrings are fine.
- **DO follow** the `@skipIf`/`@skipUnless` precedent: whole-class `@skip`
  already exists (`tests/test_accurate_usage_detection.py:7`,
  `tests/fix/test_scope.py:11`) — version-gate the same way.
- **Patterns to AVOID**: do **not** copy the `SimpleNamespace` workaround at
  `test_find_unused_code_visitor.py:102-106` — the whole point of this task is
  to exercise *literal* syntax. Do not rely on the silent-parse-failure path as
  "passing": a test that asserts `None` could be green either because nothing is
  unused *or* because the file failed to parse — those must be disambiguated by
  version-gating (see Decisions).

## Design Decisions

1. **Version-gate with `unittest.skipUnless(sys.version_info >= (3, N), ...)`**
   per test/class — chosen over a single try/except or runtime feature probe.
   Rationale: literal 3.12+ syntax raises `SyntaxError` *at file import/compile
   time* on 3.11, which would break collection, not just the test. Gating keeps
   3.11 green by skipping, and lets 3.12+ run the real fixture. This introduces
   the project's first `sys.version_info` usage — acceptable in tests (research
   Q4 notes none exist; that constraint applies to `deadcode/`, not `tests/`).

2. **Group by feature, one file per construct** under `tests/` (per CLAUDE.md §7
   "split, don't compress"): `tests/test_match_statement.py`,
   `tests/test_walrus.py`, `tests/test_type_alias.py`,
   `tests/test_pep695_generics.py`. Mirrors the existing per-topic layout
   (`test_imports.py`, etc.).

3. **Assert real detection outcomes, never just "no crash."** Each test defines
   a fixture with a *known* unused symbol and asserts the exact
   `path:line:col: DCxx` string, plus a companion case where the symbol *is*
   used and asserts `None`. This guards against the silent-degradation trap and
   makes false negatives visible.

4. **Tests-first, then fix only confirmed incompatibilities.** Write the tests,
   run across 3.12/3.13/3.14, and add `visit_*` handling in `deadcode/` *only*
   where a test proves a false positive/negative (e.g. a PEP 695 `TypeVar`
   reported as unused, or a `type` alias name mis-tracked). Keep changes
   surgical (CLAUDE.md §3) — do not pre-emptively add visitors that no test
   requires.

5. **Cover both find and fix paths for at least the alias/generics cases**,
   since `FixUnusedCodeVisitor` independently re-walks the tree
   (`fix_unused_code_visitor.py:430`) and could mis-handle the new nodes when
   rewriting. `match`/walrus get find-path coverage (they are statements/exprs
   the fixer is unlikely to rewrite).

6. **No new Justfile/Makefile recipes.** `just test` / `make test` already run
   the whole suite per interpreter via CI; the new files are picked up
   automatically (research Q5/Q6). Use existing recipes only (CLAUDE.md §5).

7. **Leave Ruff's implicit `target-version` alone** for now (research Open
   Areas). It is a real latent risk but out of this task's scope; flag under
   Open Risks rather than change config silently.

## What We're NOT Doing

- Not changing the silent bare-`except` parse-failure behavior in
  `parse_abstract_syntax_tree.py` — that is existing, intentional degradation;
  altering it is a separate decision beyond "add tests + fix incompatibilities."
- Not lowering or raising `requires-python`, nor touching the CI matrix.
- Not pinning Ruff `target-version` or adding `[tool.ruff] target-version`.
- Not adding `match`/`type`/PEP 695 syntax to `deadcode/`'s own source.
- Not un-skipping the pre-existing `@skip`ped test classes.
- Not building a multi-interpreter test runner inside the suite — version
  coverage comes from the existing CI matrix, not from spawning subinterpreters.

## Open Risks

- **Silent parse-failure masking**: if a 3.12+ fixture is *not* correctly gated,
  it parses to an empty Module on 3.11 and the test may pass for the wrong
  reason. Mitigated by Decision 3 (assert specific findings) + Decision 1
  (gating). Reviewers should double-check every 3.12+ fixture has its guard.
- **Unknown extent of real bugs**: the generic recursion means most new syntax
  "just works," so it is possible *no* `deadcode/` fix is needed and the task is
  test-only. Conversely, `column`/`lineno` reporting via
  `visitor/lines.py:_get_last_child_with_lineno:5` (special-cases `ast.Call`
  only) may produce wrong positions for new node shapes — watch the exact
  `:line:col` assertions on 3.12+.
- **Coverage interaction**: new tests can only *raise* coverage of `deadcode/`
  (research Q6); but if a fix adds new `visit_*` branches, those must themselves
  be exercised to stay ≥ 95%.
- **3.14/3.15 availability**: CI tops out at 3.14; 3.15 syntax (task mentions
  "if available") may not be installable, so any 3.15-specific test must gate on
  `sys.version_info` and degrade to skip — no hard dependency on 3.15.
