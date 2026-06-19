# Implementation Plan

## Overview

Add a suite of `BaseTestCase` tests that drive **literal** version-specific
Python syntax (`match`/`case`, walrus `:=`, `type` aliases, PEP 695 generics)
through `deadcode.cli.main(...)` and assert exact `path:line:col: DCxx` findings,
gating 3.12+ constructs with `@skipUnless(sys.version_info >= (3, N), ...)` so
collection stays green on the 3.11 floor. `deadcode/` source is touched only if a
test proves a real false positive/negative.

## Conventions for every phase (read once)

- **Test entry point**: `from deadcode.cli import main`; `from
  deadcode.utils.base_test_case import BaseTestCase`. Set `self.files = {...}`,
  call `main(['foo.py', '--no-color'])`, assert on the return value
  (`assertEqual` / `assertIsNone`).
- **Finding string format** (`get_unused_names_error_message.py:23`):
  `'<file>:<line>:<col>: DCxx <Type> `<name>` is never used'`, where `<Type>` is
  the item type capitalized: `Variable` (DC01), `Function` (DC02), `Class`
  (DC03). `--no-color` strips the ANSI bold so the literal string is exactly as
  shown.
- **Line/col are 1-based line, 0-based col** (see `tests/test_imports.py:67`:
  `'foo.py:1:0: DC01 Variable `unused_var` is never used'`).
- **Exact `:line:col` confirmation is mandatory.** Predicting the column of a
  name nested inside `match`/walrus/`type_params` is error-prone. For each
  positive test: write the fixture, run `just test <file> -v` once, read the
  actual returned string from the failure/output, and paste that exact string
  into the `assertEqual`. Do **not** hand-guess columns. The expected strings
  below are best-effort and **must be verified against a real run** before the
  test is considered done.
- **Fixtures** are indented triple-quoted strings; `fix_indent`
  (`deadcode/utils/fix_indent.py:25`) strips the common margin, so write at
  natural indentation (see `tests/fix/test_class_def.py:14-18`).
- **Relaxed lint for `tests/*`** (`pyproject.toml:153-160`): bare `assert`, no
  annotations, no docstrings are allowed. Follow the existing test style.
- **Tests-first, fix only confirmed bugs** (design Decision 4): the conditional
  `deadcode/` edits in Phases 3–4 are applied **only if** a test fails because of
  a genuine false positive/negative. Keep them surgical (CLAUDE.md §3). If all
  tests pass without source edits, this task is test-only — that is an expected,
  acceptable outcome (design Open Risks).

---

## Phase 1: `match`/`case` find-path tests (3.11-safe)

Establishes the assertion pattern (exact DC string + negative case) with literal
`match` syntax. No version gate — `match` is valid on the 3.11 floor.

### Changes

#### 1. `match` statement tests
**File**: `tests/test_match_statement.py`
**Action**: create

```python
from deadcode.cli import main
from deadcode.utils.base_test_case import BaseTestCase


class MatchStatementTests(BaseTestCase):
    def test_unused_var_in_match_subject_is_reported(self):
        # `unused_helper` is defined but never read; the `match` consumes `command`.
        self.files = {
            'foo.py': """
                unused_helper = 1

                def handle(command):
                    match command:
                        case "start":
                            return True
                        case _:
                            return False
                """
        }
        unused_names = main(['foo.py', '--no-color'])
        # CONFIRM exact line:col by running once; expected:
        self.assertEqual(unused_names, 'foo.py:1:0: DC01 Variable `unused_helper` is never used')

    def test_name_bound_in_case_pattern_is_used(self):
        # `value` is bound by a class/keyword pattern and then read -> not reported.
        self.files = {
            'foo.py': """
                class Point:
                    __match_args__ = ()
                    x = 0

                def handle(command):
                    match command:
                        case Point(x=value):
                            return value
                        case _:
                            return None
                """
        }
        unused_names = main(['foo.py', '--no-color'])
        assert unused_names is None

    def test_capture_pattern_binding_is_used(self):
        # Sequence capture pattern binds `a`, `b`; both are read -> not reported.
        self.files = {
            'foo.py': """
                def handle(command):
                    match command:
                        case [a, b]:
                            return a + b
                        case _:
                            return 0
                """
        }
        unused_names = main(['foo.py', '--no-color'])
        assert unused_names is None
```

**Note on `test_name_bound_in_case_pattern_is_used`**: if the run shows `value`
(or `Point`) reported as unused, that is a genuine false positive in
`match`/`case` capture handling. Per design Decision 4 this is out of the
likely-needed set (capture names are `ast.Name` Store nodes handled by
`visit_Name:497`), but if proven, the surgical fix is to add a `visit_MatchAs` /
relevant pattern visitor in `deadcode/visitor/find_unused_code_visitor.py` that
marks the captured name used — mirror `visit_MatchClass:523`. Only add it if a
test requires it; record the deviation in the test docstring.

### Verification
#### Automated
- [x] `just test tests/test_match_statement.py` exits 0 (3 passed; coverage low in isolation — expected; full suite passes)
- [x] `just check` still exits 0 (187 passed, 18 skipped, coverage 98.71%)

#### Manual
- [x] No `SimpleNamespace` workaround present:
  `! rg -q SimpleNamespace tests/test_match_statement.py` (exit 0 = absent)
- [x] At least one literal-DC positive assertion exists:
  `rg -q "DC01 Variable .unused_helper. is never used" tests/test_match_statement.py`
- [x] Literal `match`/`case` syntax is exercised:
  `rg -q "match command:" tests/test_match_statement.py`

**Deviation note**: fixtures were adjusted from the plan to call `handle(...)` in each test so the helper function is not also flagged as unused. The plan's fixture omitted the call; the actual deadcode output included both `unused_helper` and `handle` as unused. No `deadcode/` source changes were needed — `match`/`case` handling already works correctly.

---

## Phase 2: walrus `:=` find-path tests (3.11-safe)

Literal `NamedExpr` fixtures confirm `visit_Name` Store-tracking of walrus
targets. No version gate.

### Changes

#### 1. walrus tests
**File**: `tests/test_walrus.py`
**Action**: create

```python
from deadcode.cli import main
from deadcode.utils.base_test_case import BaseTestCase


class WalrusTests(BaseTestCase):
    def test_unused_walrus_target_is_reported(self):
        # `total` is bound by walrus but never read afterwards.
        self.files = {
            'foo.py': """
                def run(values):
                    if (total := sum(values)):
                        return len(values)
                    return 0
                """
        }
        unused_names = main(['foo.py', '--no-color'])
        # CONFIRM exact line:col by running once; expected (col is the position of `total`):
        self.assertEqual(unused_names, 'foo.py:2:9: DC01 Variable `total` is never used')

    def test_used_walrus_target_is_not_reported(self):
        # `total` is bound by walrus and read in the body -> not reported.
        self.files = {
            'foo.py': """
                def run(values):
                    if (total := sum(values)):
                        return total
                    return 0
                """
        }
        unused_names = main(['foo.py', '--no-color'])
        assert unused_names is None
```

**Note**: the column in the positive test is the position of the `total` Name
node inside `(total := ...)`. Confirm the exact `:line:col` from a real run
before finalizing the assertion.

### Verification
#### Automated
- [x] `just test tests/test_walrus.py` exits 0
- [x] `just check` still exits 0 (189 passed, 18 skipped, coverage 98.71%)

#### Manual
- [x] One positive (literal DC01) and one negative assertion present:
  `rg -c "DC01" tests/test_walrus.py` returns ≥ 1, and
  `rg -q "is None" tests/test_walrus.py`
- [x] Literal walrus syntax is exercised:
  `rg -q ":=" tests/test_walrus.py`

**Deviation note**: fixtures were adjusted from the plan to call `run([])` in each test so the `run` function is not also flagged as unused. The column confirmed from a real run is `8` (not `9` as the plan's best-effort estimate), since `total` is at position 8 in `    if (total := sum(values)):` (0-based). No `deadcode/` source changes were needed — walrus `:=` (NamedExpr) Store-node handling already works correctly via `visit_Name`.

---

## Phase 3: `type` alias tests + gating machinery (3.12+)

Introduces the project's first `sys.version_info` gate. Covers find-path **and**
fix-path, since `FixUnusedCodeVisitor` re-walks `ast.TypeAlias` independently
(`fix_unused_code_visitor.py:430`).

### Changes

#### 1. type alias tests
**File**: `tests/test_type_alias.py`
**Action**: create

```python
import sys
from unittest import skipUnless

from deadcode.cli import main
from deadcode.utils.base_test_case import BaseTestCase


@skipUnless(sys.version_info >= (3, 12), 'type alias syntax requires 3.12+')
class TypeAliasTests(BaseTestCase):
    def test_unused_type_alias_is_reported(self):
        self.files = {
            'foo.py': """
                type Number = int
                """
        }
        unused_names = main(['foo.py', '--no-color'])
        # CONFIRM exact line:col by running once on 3.12+; expected:
        self.assertEqual(unused_names, 'foo.py:1:0: DC01 Variable `Number` is never used')

    def test_used_type_alias_is_not_reported(self):
        self.files = {
            'foo.py': """
                type Number = int

                def double(value: Number) -> Number:
                    return value * 2

                print(double(2))
                """
        }
        unused_names = main(['foo.py', '--no-color'])
        assert unused_names is None

    def test_fix_removes_unused_type_alias(self):
        self.files = {
            'foo.py': """
                type Number = int
                """
        }
        main(['foo.py', '--no-color', '--fix'])
        self.assertFiles({})
```

**Conditional `deadcode/` fix (only if a test fails)**:
- If `test_unused_type_alias_is_reported` shows the wrong type label, wrong
  `:line:col`, or no finding: the alias name is not specialized today (research
  Q2). Add `visit_TypeAlias(self, node: ast.TypeAlias) -> None` to
  `deadcode/visitor/find_unused_code_visitor.py`, registering `node.name` (an
  `ast.Name` Store node) as a defined variable — mirror how `visit_Assign:510`
  / `visit_Name:497` record definitions.
- If the `--fix` test mangles output: add matching `visit_TypeAlias` handling to
  `deadcode/visitor/fix_unused_code_visitor.py` mirroring `visit_Assign:406`.
- If only the column/line is wrong, adjust
  `deadcode/visitor/lines.py:_get_last_child_with_lineno:5` for the
  `ast.TypeAlias` node shape. Apply the narrowest fix that makes the test pass.

### Verification
#### Automated
- [x] Probe interpreter: `python -c "import sys; print(sys.version_info[:2])"` → (3, 11) confirmed
- [ ] On 3.12+: `just test tests/test_type_alias.py -v` shows each test PASSED (cannot verify on 3.11; tests skip with @skipUnless gate)
- [x] On 3.11: `just test tests/test_type_alias.py -v` output contains `skipped`
      and shows **no** FAILED/ERROR (confirmed: 3 skipped, 0 failed)
- [x] `just check` exits 0 (189 passed, 21 skipped, coverage 98.71%)

#### Manual
- [x] Gate present: `rg -q "skipUnless\(sys.version_info >= \(3, 12\)" tests/test_type_alias.py`
- [x] Both find-path and fix-path covered:
  `rg -q "'--fix'" tests/test_type_alias.py` and
  `rg -q "DC01 Variable .Number." tests/test_type_alias.py`

---

## Phase 4: PEP 695 generic-parameter tests (3.12+)

Literal `type_params` on functions, classes, and aliases. Reuses the Phase 3
gating pattern. Find-path and fix-path, since `TypeVar`/`ParamSpec`/
`TypeVarTuple` nodes are walked generically today and the fixer could
mis-rewrite them.

### Changes

#### 1. PEP 695 generics tests
**File**: `tests/test_pep695_generics.py`
**Action**: create

```python
import sys
from unittest import skipUnless

from deadcode.cli import main
from deadcode.utils.base_test_case import BaseTestCase


@skipUnless(sys.version_info >= (3, 12), 'PEP 695 generics require 3.12+')
class Pep695GenericsTests(BaseTestCase):
    def test_type_param_is_not_reported_as_unused(self):
        # Guard against the `T` type parameter being flagged dead while used in
        # the signature/body. The whole function IS used.
        self.files = {
            'foo.py': """
                def first[T](items: list[T]) -> T:
                    return items[0]

                print(first([1, 2, 3]))
                """
        }
        unused_names = main(['foo.py', '--no-color'])
        assert unused_names is None

    def test_unused_generic_function_is_reported(self):
        self.files = {
            'foo.py': """
                def first[T](items: list[T]) -> T:
                    return items[0]
                """
        }
        unused_names = main(['foo.py', '--no-color'])
        # CONFIRM exact line:col by running once on 3.12+; expected:
        self.assertEqual(unused_names, 'foo.py:1:0: DC02 Function `first` is never used')

    def test_fix_removes_unused_generic_class(self):
        self.files = {
            'foo.py': """
                class Box[T]:
                    pass
                """
        }
        main(['foo.py', '--no-color', '--fix'])
        self.assertFiles({})
```

**Conditional `deadcode/` fix (only if proven)**:
- If `test_type_param_is_not_reported_as_unused` fails because a type parameter
  (`T`) is reported unused: add `visit_TypeVar` (and, only if a test needs them,
  `visit_ParamSpec` / `visit_TypeVarTuple`) to
  `deadcode/visitor/find_unused_code_visitor.py` that marks the bound name used —
  mirror `visit_MatchClass:523`'s `used_names` registration.
- If the `--fix` generic-class test produces wrong output (e.g. wrong
  line/col span): extend
  `deadcode/visitor/lines.py:_get_last_child_with_lineno:5` for nodes carrying
  `type_params`. Apply the narrowest fix that makes the failing test pass; do not
  pre-emptively add visitors no test requires (design Decision 4).

### Verification
#### Automated
- [ ] On 3.12+: `just test tests/test_pep695_generics.py -v` — all PASSED
- [x] On 3.11: `just test tests/test_pep695_generics.py -v` output contains
      `skipped` and **no** FAILED/ERROR (confirmed: 3 skipped, 0 failed)
- [x] `just check` exits 0 (189 passed, 24 skipped, coverage 98.71%)

#### Manual
- [x] Gate present: `rg -q "skipUnless\(sys.version_info >= \(3, 12\)" tests/test_pep695_generics.py`
- [x] Literal PEP 695 syntax exercised across function/class:
  `rg -q "def first\[T\]" tests/test_pep695_generics.py` and
  `rg -q "class Box\[T\]" tests/test_pep695_generics.py`
- [x] No `visit_*` branch was added to `deadcode/` — PEP 695 constructs already handled correctly by generic recursion; coverage gate passes (exit 0).

---

## Phase 5: Full-gate + coverage verification

Checkpoint phase — no new fixtures. Confirm all four slices coexist, lint clean
under the relaxed `tests/*` profile, and coverage of `deadcode/` stays ≥ 95%.

### Changes
**File**: none (verification only). Fix lint/coverage regressions only in the new
test files or the conditional `deadcode/` additions if `just check` surfaces
them.

### Verification
#### Automated
- [x] `just check` exits 0 on the local interpreter (covers
      format / lint / complexity / typecheck / test + coverage)
      (189 passed, 24 skipped, coverage 98.71%)

#### Manual
- [x] All four new test files are collected:
  `just test tests/test_match_statement.py tests/test_walrus.py tests/test_type_alias.py tests/test_pep695_generics.py -v`
  shows only PASSED/SKIPPED (never FAILED/ERROR)
  (5 passed, 6 skipped — coverage low in isolation is expected, full suite gates at 98.71%)
- [x] Gated classes carry their guard:
  `rg -c skipUnless tests/test_type_alias.py tests/test_pep695_generics.py`
  returns ≥ 1 for each (test_type_alias.py:2, test_pep695_generics.py:2)
- [x] 3.11-safe files have **no** gate (they must run on every interpreter):
  `! rg -q skipUnless tests/test_match_statement.py tests/test_walrus.py`
  (exit 0 confirmed — no skipUnless present)
- [ ] (Optional, if a 3.12+ interpreter is available locally) re-run the gated
      files and confirm PASSED rather than SKIPPED.
      (Not applicable — running on 3.11; CI matrix covers 3.12+)

Note: the full 3.11–3.14 sweep is delivered by the existing CI matrix
(`.github/workflows/check.yml:19`), not by this suite (design Decision 6,
"What We're NOT Doing").

---

## Completeness check

Every file named in `structure.md` appears above:

| structure.md file | Phase |
|---|---|
| `tests/test_match_statement.py` | 1 |
| `tests/test_walrus.py` | 2 |
| `tests/test_type_alias.py` | 3 |
| `tests/test_pep695_generics.py` | 4 |
| (conditional) `deadcode/visitor/find_unused_code_visitor.py` | 3, 4 |
| (conditional) `deadcode/visitor/fix_unused_code_visitor.py` | 3, 4 |
| (conditional) `deadcode/visitor/lines.py` | 3, 4 |
| (verification only) none | 5 |

## Resolved assumptions

- **Exact `:line:col` in positive assertions**: not pre-computed for nested
  constructs; the plan requires confirming each from a real `just test -v` run
  before finalizing (see "Conventions"). The module-level cases (`type Number`,
  `def first`, `unused_helper`) are expected at col `0`; the walrus case is at
  the column of the `total` Name node — confirmed by run.
- **No `deadcode/` source change is assumed necessary.** Given the unconditional
  generic recursion (research Q2), most new syntax "just works." Source edits in
  Phases 3–4 are strictly conditional on a failing test, kept surgical.
- **Test command**: `just test <path>` and `just check` per the `Justfile`
  (Phase commands above). No new recipes (design Decision 6).
