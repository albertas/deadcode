# Structure Outline

## Approach

Add one `BaseTestCase` test file per version-specific construct, each driving
**literal** syntax through `deadcode.cli.main(...)` and asserting the exact
`path:line:col: DCxx` finding plus a negative (used → `None`) companion. Each
construct is its own vertical slice: write the fixture, run it, and — only if a
test proves a false positive/negative — add surgical `visit_*` handling in
`deadcode/`, then re-verify. 3.11-safe constructs run unconditionally; 3.12+
constructs are gated with `@unittest.skipUnless(sys.version_info >= (3, N), ...)`
so collection stays green on 3.11. No config, Justfile, or CI changes.

Each slice crosses the full pipeline already exercised by `BaseTestCase`:
fixture I/O seam → `parse_abstract_syntax_tree` → `FindUnusedCodeVisitor` (and
`FixUnusedCodeVisitor` for `--fix` slices) → report string. The "layers" here
are parse → find → fix → report; every slice touches all that its construct
needs.

---

## Phase 1: `match`/`case` find-path tests (3.11-safe)

Literal `match` statement fixtures with a known-unused symbol and a used
companion. Establishes the assertion pattern (exact DC string + negative case).
No version gate — `match` is valid on the 3.11 floor.

**Files**: `tests/test_match_statement.py` (new)
**Key changes**:
- `class MatchStatementTests(BaseTestCase)` — new
- `test_unused_var_in_match_subject_is_reported(self)` — fixture defines an
  unused module-level var consumed by a `match`; asserts `'foo.py:L:C: DC01 ...'`
- `test_name_bound_in_case_pattern_is_used(self)` — `case Point(x=value):` /
  `MatchClass kwd_attrs` path; asserts `None`
- `test_capture_pattern_binding_is_tracked(self)` — `case [a, b]:` capture names;
  assert correct used/unused outcome

**Verify**: `just test tests/test_match_statement.py` exits 0; grep the file to
confirm at least one `assertEqual(..., 'foo.py:` literal-DC assertion exists and
no `SimpleNamespace` is used (`! rg SimpleNamespace tests/test_match_statement.py`).

---

## Phase 2: walrus `:=` find-path tests (3.11-safe)

Literal `NamedExpr` fixtures: a walrus target that is never read (→ DC01) and
one that is read (→ `None`). Confirms `visit_Name` Store-tracking of walrus
targets. No version gate.

**Files**: `tests/test_walrus.py` (new)
**Key changes**:
- `class WalrusTests(BaseTestCase)` — new
- `test_unused_walrus_target_is_reported(self)` — `if (n := compute()): pass`
  where `n` is otherwise unused; assert the DC01 string
- `test_used_walrus_target_is_not_reported(self)` — target later read; assert `None`

**Verify**: `just test tests/test_walrus.py` exits 0; confirm one positive
(literal DC01 string) and one `assertIsNone`/`None` assertion via
`rg -c 'DC01' tests/test_walrus.py`.

---

## Phase 3: `type` alias tests + gating machinery (3.12+)

Introduces the project's first `sys.version_info` gate. Literal
`type Alias = int` fixtures, find-path **and** fix-path (`--fix`), because
`FixUnusedCodeVisitor` re-walks `ast.TypeAlias` independently.

**Files**: `tests/test_type_alias.py` (new)
**Key changes**:
- `import sys`, `from unittest import skipUnless`
- `@skipUnless(sys.version_info >= (3, 12), 'type alias syntax requires 3.12+')`
  on `class TypeAliasTests(BaseTestCase)` — new
- `test_unused_type_alias_is_reported(self)` — assert exact DC string for the
  unused alias name
- `test_used_type_alias_is_not_reported(self)` — alias referenced in an
  annotation; assert `None`
- `test_fix_removes_unused_type_alias(self)` — `main([..., '--fix'])` +
  `assertFiles`/`assertUpdatedFiles` showing the alias line removed
- **Conditional `deadcode/` fix** (only if a test fails): add
  `visit_TypeAlias(self, node: ast.TypeAlias) -> None` to
  `find_unused_code_visitor.py` / `fix_unused_code_visitor.py`, mirroring
  existing name-tracking; or adjust `visitor/lines.py` if `:line:col` is wrong.

**Verify**: `just test tests/test_type_alias.py -v` shows each test PASSED (on a
3.12+ interpreter) or SKIPPED (on 3.11) — **never** FAILED/ERROR. Probe the
interpreter first: `python -c "import sys;print(sys.version_info[:2])"`. On 3.11
additionally confirm the gate fires: `just test tests/test_type_alias.py -v`
output contains `skipped`. Whole suite `just check` still exits 0.

---

## Phase 4: PEP 695 generic-parameter tests (3.12+)

Literal `type_params` on functions, classes, and aliases
(`def f[T](...)`, `class C[T]:`, `type A[T] = ...`). Reuses the Phase 3 gating
pattern. Find-path and fix-path, since `TypeVar`/`ParamSpec`/`TypeVarTuple`
nodes are walked generically today and the fixer could mis-rewrite them.

**Files**: `tests/test_pep695_generics.py` (new)
**Key changes**:
- `@skipUnless(sys.version_info >= (3, 12), 'PEP 695 generics require 3.12+')`
  on `class Pep695GenericsTests(BaseTestCase)` — new
- `test_type_param_is_not_reported_as_unused(self)` — guards against a `TypeVar`
  being flagged dead while used in the signature; assert `None`
- `test_unused_generic_function_is_reported(self)` — `def f[T](x: T): ...`
  unused; assert exact DC02 string (verifies `:line:col` with `type_params`
  present)
- `test_fix_removes_unused_generic_class(self)` — `--fix` + `assertFiles`
- **Conditional `deadcode/` fix** (only if proven): add
  `visit_TypeVar` / `visit_ParamSpec` / `visit_TypeVarTuple` (mark the bound
  name used) and/or extend `visitor/lines.py:_get_last_child_with_lineno` for
  generic node shapes. Keep surgical; add only what a failing test requires.

**Verify**: `just test tests/test_pep695_generics.py -v` — all PASSED on 3.12+
or SKIPPED on 3.11, never FAILED. If any `deadcode/` `visit_*` branch was added,
confirm it is exercised: `just test` then inspect coverage did not drop below
95% (`just check` aggregates the `--cov-fail-under=95.0` gate and exits non-zero
on regression).

---

## Phase 5: Full-gate + coverage verification

No new fixtures — a checkpoint phase. Run the complete gate to confirm all four
slices coexist, lint clean under the relaxed `tests/*` profile, and coverage of
`deadcode/` stays ≥ 95% (including any new `visit_*` branches added in Phases
3–4).

**Files**: none (verification only)
**Key changes**: none, unless `just check` surfaces a lint/coverage regression
to fix in the new test files or the conditional `deadcode/` additions.

**Verify**: `just check` exits 0 on the local interpreter (covers
format/lint/complexity/typecheck/test + coverage). Confirm CI-matrix intent by
checking that gated classes skip on 3.11 and would run on 3.12–3.14:
`rg -c skipUnless tests/test_type_alias.py tests/test_pep695_generics.py`
returns ≥ 1 each. Note: the 3.11–3.14 sweep itself is delivered by the existing
CI matrix (`.github/workflows/check.yml`), not by this suite.

---

## Testing Checkpoints

- **After Phase 1**: `tests/test_match_statement.py` passes on every
  interpreter; literal `match` syntax is exercised (no `SimpleNamespace`); at
  least one exact DC01 assertion plus a negative case.
- **After Phase 2**: `tests/test_walrus.py` passes; walrus target reported when
  unused, silent when used.
- **After Phase 3**: `type` alias find + fix covered; gating verified to SKIP on
  3.11 and PASS on 3.12+; `just check` green. First `sys.version_info` gate is
  in place and proven not to break collection on 3.11.
- **After Phase 4**: PEP 695 generics find + fix covered behind the same gate;
  no `TypeVar` false positives; any added `deadcode/` `visit_*` branch is
  coverage-exercised.
- **After Phase 5**: `just check` exits 0; coverage ≥ 95%; gated classes skip on
  3.11; full matrix delegated to CI. Each phase's file is independently valuable
  — a later phase failing does not invalidate earlier slices.

## Slicing note

Per-interpreter execution (3.11 vs 3.12+) cannot be sliced *within* a single
local run — one agent runs one interpreter. The vertical slices above are
construct-based and each is fully testable on whatever interpreter is present
(running or skipping as gated); cross-version coverage is the CI matrix's job,
per design Decision 6 and "What We're NOT Doing."
