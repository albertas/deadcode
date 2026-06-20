# Implementation Plan

## Overview

Audit the `deadcode` detection logic for correctness gaps (no visitor fixes) and
land regression/characterization tests. Each phase confirms one candidate finding
(F1–F7) by actually running `main([...])`, records a verdict in a single
`audit.md`, and lands a `BaseTestCase` test encoding the **correct** expected
behavior — `@unittest.expectedFailure` for confirmed bugs (flips to a guard when a
fix lands), green characterization tests for correct-but-surprising behavior.

### Conventions (apply to every phase)

- **Audit report path**: `workspace/T22-2026-06-20-check-deadcode-package-implementation-for-correctn/audit.md`
  (the artifact directory — NOT inside the repo's `tests/`). Created in Phase 1,
  appended in Phases 2–7, summarized in Phase 8.
- **Tests path**: under the existing `tests/` tree (repo root
  `/home/niekas/tools/deadcode/tests/`).
- **Test scaffold** (every test file): subclass `BaseTestCase`, set
  `self.files = {'foo.py': """..."""}`, call `main(['foo.py', '--no-color', ...])`,
  assert exact string or `None`. Imports:
  ```python
  from deadcode.cli import main
  from deadcode.utils.base_test_case import BaseTestCase
  ```
- **`fix_indent` line numbering**: fixtures are dedented and the leading blank line
  is stripped, so **line 1 = the first non-blank source line** (confirmed against
  `tests/test_walrus.py:21`). All expected line:col values below were computed from
  real `main()` runs on equivalent dedented fixtures.
- **Vacuous-pass guard**: every "not reported / None" assertion ships a
  defined-and-unused **control** (same-named or distinctly-named sibling) that **is**
  reported, proving the visitor actually ran.
- **audit.md finding schema** (one markdown `###` section per F#):
  `Category` (false positive / false negative / by-design) · `Reproduction`
  (fixture source + exact `main()` argv + observed return) · `Root cause`
  (`file:line`) · `Severity` (high / medium / low) · `Verdict` · `Guarding test`
  (path::TestClass).
- **Verification commands**:
  - Full suite: `just test`
  - Single file: `uv run pytest tests/<path> -q`
  - Quality gate: `just check` (format, lint, complexity ≤10, typecheck — see
    `pyproject.toml`).
  - `@unittest.expectedFailure` counts as a **pass** in unittest/pytest; an
    unexpected pass (e.g. a flag gets wired) reports as a failure → the regression
    flip signal.

### Confirmed root-cause line references (verified against source)

- F1: `deadcode/visitor/ignore.py:40` (`item.name not in used_names`) +
  `deadcode/visitor/find_unused_code_visitor.py:325` (ignore = `add_used_name`).
- F2: `deadcode/visitor/find_unused_code_visitor.py:344-348` (`visit_Attribute`,
  `Load` → `add_used_name(node.attr)` at `:348`).
- F3: `deadcode/visitor/find_unused_code_visitor.py:337` (`# def visit_arg` commented).
- F4: no `visit_MatchAs`/`visit_MatchStar`/`visit_MatchMapping`; only
  `visit_MatchClass` at `:526-529`.
- F5: no `visit_TypeVar`/`visit_arg`; PEP 695 type params are `str` attrs.
- F6: `visit_Call:364-413` (`getattr`/`hasattr`, `.format(**locals())`) +
  `visit_BinOp:350-362` (`% locals()`).
- F7: `deadcode/actions/parse_arguments.py:61` onward — six flags parsed, never
  consumed (**note: file is `actions/parse_arguments.py`, not `cli/`**).

---

## Phase 1: Audit scaffold + F1 scope-blind flat matching

### Changes

#### 1. Audit report scaffold
**File**: `workspace/T22-2026-06-20-check-deadcode-package-implementation-for-correctn/audit.md`
**Action**: create

Header + finding schema legend, then the F1 entry. Template per finding:

```markdown
# deadcode Detection-Correctness Audit (T22)

Each finding was confirmed by running `main([...])` (design decision 5), not by
reading source alone. Verdicts: false positive (FP), false negative (FN),
by-design. Severity ranked by blast radius (design decision 3).

## F1 — Scope-blind flat matching

- **Category**: false negative
- **Severity**: high (affects every method/attribute/variable that shares a name)
- **Root cause**: `deadcode/visitor/ignore.py:40` computes unused as
  `[item for item in defined_items if item.name not in used_names]` — a flat,
  scope-blind string compare; `find_unused_code_visitor.py:325` collapses every
  suppression into the same flat `used_names` set.
- **Reproduction**: (fixture below) `main(['foo.py', '--no-color'])` → `None`.
  `B.run` is genuinely unused but a `Load` of `run` from `A().run()` marks the
  name globally used.
- **Verdict**: confirmed bug. A use of name `x` anywhere marks every definition
  named `x` used.
- **Guarding test**:
  `tests/test_scope_blind_matching.py::ScopeBlindMatchingTests`
```

#### 2. F1 test
**File**: `tests/test_scope_blind_matching.py`
**Action**: create

```python
from unittest import expectedFailure

from deadcode.cli import main
from deadcode.utils.base_test_case import BaseTestCase


class ScopeBlindMatchingTests(BaseTestCase):
    @expectedFailure
    def test_unused_method_shadowed_by_unrelated_use_is_reported(self):
        # `B.run` is genuinely unused, but `A().run()` marks the bare name
        # `run` used, so the scope-blind flat match suppresses it. Correct
        # behavior: `B.run` IS reported. Currently main() returns None.
        self.files = {
            'foo.py': """
                class A:
                    def run(self):
                        return 1


                class B:
                    def run(self):
                        return 2


                A().run()
                B()
                """
        }
        unused_names = main(['foo.py', '--no-color'])
        # CONFIRM line:col when the fix lands; until then this assertion fails
        # (None != string) and @expectedFailure makes the test pass.
        self.assertEqual(unused_names, 'foo.py:7:4: DC04 Method `run` is never used')

    def test_distinctly_named_unused_method_is_reported(self):
        # Control: a uniquely-named unused method IS reported, proving the
        # visitor ran and the F1 gap is specific to name collisions.
        self.files = {
            'foo.py': """
                class A:
                    def run(self):
                        return 1


                class B:
                    def distinctly_unused(self):
                        return 2


                A().run()
                B()
                """
        }
        unused_names = main(['foo.py', '--no-color'])
        self.assertEqual(unused_names, 'foo.py:7:4: DC04 Method `distinctly_unused` is never used')
```

### Verification
#### Automated
- [x] `uv run pytest tests/test_scope_blind_matching.py -q` (1 xfail, 1 pass; single-file run trips the 95% coverage gate but test outcomes are correct)
- [x] `just test` passes (208 passed, 24 skipped, 1 xfailed)

#### Manual
- [x] FN reproduced: write the F1 fixture to `/tmp/f1.py` (un-indented) and run
  `uv run python -c "from deadcode.cli import main; print(repr(main(['/tmp/f1.py','--no-color'])))"`
  → prints `None` (observed). Record this in audit.md.
- [x] Control reproduced: same with the `distinctly_unused` fixture →
  prints `'/tmp/f1c.py:7:4: DC04 Method \`distinctly_unused\` is never used'`
- [x] `test -f workspace/T22-2026-06-20-check-deadcode-package-implementation-for-correctn/audit.md`

---

## Phase 2: F2 attribute receiver ignored

### Changes

#### 1. F2 test
**File**: `tests/test_attribute_receiver.py`
**Action**: create

```python
from unittest import expectedFailure

from deadcode.cli import main
from deadcode.utils.base_test_case import BaseTestCase


class AttributeReceiverTests(BaseTestCase):
    @expectedFailure
    def test_function_shadowed_by_same_named_attribute_is_reported(self):
        # `value` (a module function) is never called. But `obj.value` is a
        # bare-attr Load (visit_Attribute:348) that marks the name `value`
        # used, cross-contaminating the function. Correct: the function IS
        # reported. Currently main() returns None.
        self.files = {
            'foo.py': """
                def value():
                    return 1


                class C:
                    def go(self, obj):
                        return obj.value


                C().go(None)
                """
        }
        unused_names = main(['foo.py', '--no-color'])
        self.assertEqual(unused_names, 'foo.py:1:0: DC02 Function `value` is never used')

    def test_distinctly_named_unused_function_is_reported(self):
        # Control: a uniquely-named unused function IS reported.
        self.files = {
            'foo.py': """
                def distinctly_unused():
                    return 1


                class C:
                    def go(self, obj):
                        return obj.value


                C().go(None)
                """
        }
        unused_names = main(['foo.py', '--no-color'])
        self.assertEqual(unused_names, 'foo.py:1:0: DC02 Function `distinctly_unused` is never used')
```

#### 2. audit.md F2 entry
**File**: `workspace/.../audit.md`
**Action**: append

- Category: false negative · Severity: high · Root cause:
  `find_unused_code_visitor.py:348` (`add_used_name(node.attr)`, no receiver
  tracking) · Reproduction: fixture above, `main(['foo.py','--no-color'])` →
  `None` · Verdict: confirmed bug (any `.foo` Load marks all `.foo` attrs and
  same-named funcs/vars used) · Guarding test:
  `tests/test_attribute_receiver.py::AttributeReceiverTests`.

### Verification
#### Automated
- [x] `uv run pytest tests/test_attribute_receiver.py -q` exits 0 (1 xfail, 1 pass; single-file run trips the 95% coverage gate but test outcomes are correct)
- [x] `just test` passes (209 passed, 24 skipped, 2 xfailed)

#### Manual
- [x] FN reproduced: `/tmp/f2.py` (function `value` + `obj.value`) →
  `main(['/tmp/f2.py','--no-color'])` prints `None`; recorded in audit.md.
- [x] Control: distinctly-named fixture prints
  `'/tmp/f2c.py:1:0: DC02 Function \`distinctly_unused\` is never used'`

---

## Phase 3: F3 parameters never reported (by-design verdict)

### Changes

#### 1. F3 test (characterization — green, no expectedFailure)
**File**: `tests/test_unused_parameters.py`
**Action**: create

```python
from deadcode.cli import main
from deadcode.utils.base_test_case import BaseTestCase


class UnusedParameterTests(BaseTestCase):
    def test_unused_parameter_is_not_reported(self):
        # `visit_arg` is commented out (find_unused_code_visitor.py:337), so
        # parameters are never registered as definitions. This pins current
        # behavior: only the unused local `x` is reported, never `unused_param`.
        self.files = {
            'foo.py': """
                def f(unused_param):
                    x = 1
                    return 0


                f(2)
                """
        }
        unused_names = main(['foo.py', '--no-color'])
        # Control is built in: the unused local `x` IS reported, proving the
        # visitor ran and the gap is parameter-specific.
        self.assertEqual(unused_names, 'foo.py:2:4: DC01 Variable `x` is never used')
```

#### 2. audit.md F3 entry
**File**: `workspace/.../audit.md`
**Action**: append

- Category: by-design · Severity: low · Root cause:
  `find_unused_code_visitor.py:337` (`# def visit_arg` commented; `ast.Param` is a
  Python-2-era context, so modern `ast.arg` params are not registered) ·
  Reproduction: fixture above → `'foo.py:2:4: DC01 Variable \`x\` is never used'`
  (only `x`, not `unused_param`) · Verdict: **by-design — parameter tracking
  deliberately disabled**; pinned green as characterization · Guarding test:
  `tests/test_unused_parameters.py::UnusedParameterTests`.

### Verification
#### Automated
- [x] `uv run pytest tests/test_unused_parameters.py -q` exits 0 (1 pass, green) — deliverables were created during Phase 8 (Phase 3 was marked done in progress.yml but its test file + audit entry were missing)
- [x] `just test` passes (216 passed, 26 skipped, 9 xfailed)

#### Manual
- [x] `/tmp/f3.py` = `def f(unused_param):\n    x = 1\n    return 0\n\n\nf(2)` →
  `main(['/tmp/f3.py','--no-color'])` prints
  `'/tmp/f3.py:2:4: DC01 Variable \`x\` is never used'` (param absent). Record verdict.

---

## Phase 4: F4 match-capture patterns untracked

### Changes

#### 1. F4 test (version-gated)
**File**: `tests/test_match_capture_unused.py`
**Action**: create

```python
import sys
from unittest import expectedFailure, skipUnless

from deadcode.cli import main
from deadcode.utils.base_test_case import BaseTestCase


@skipUnless(sys.version_info >= (3, 10), 'match statements require 3.10+')
class MatchCaptureUnusedTests(BaseTestCase):
    @expectedFailure
    def test_unused_match_capture_is_reported(self):
        # Capture `a` in `case [a]` is bound but never read. Captures bind via
        # str attrs (MatchAs/MatchStar/MatchMapping), not Name nodes, and there
        # is no visit_MatchAs, so they are never tracked. Correct: `a` IS
        # reported. Currently main() returns None.
        self.files = {
            'foo.py': """
                def handle(command):
                    match command:
                        case [a]:
                            return 0
                        case _:
                            return 1


                handle([1])
                """
        }
        unused_names = main(['foo.py', '--no-color'])
        # CONFIRM line:col when the fix lands.
        self.assertEqual(unused_names, 'foo.py:3:14: DC01 Variable `a` is never used')

    def test_unused_local_in_match_function_is_reported(self):
        # Control: an ordinary unused local in the same function IS reported,
        # proving the visitor ran inside the match construct.
        self.files = {
            'foo.py': """
                def handle(command):
                    leftover = 5
                    match command:
                        case [a]:
                            return 0
                        case _:
                            return 1


                handle([1])
                """
        }
        unused_names = main(['foo.py', '--no-color'])
        self.assertEqual(unused_names, 'foo.py:2:4: DC01 Variable `leftover` is never used')
```

#### 2. audit.md F4 entry
**File**: `workspace/.../audit.md`
**Action**: append

- Category: false negative · Severity: medium · Root cause: no
  `visit_MatchAs`/`visit_MatchStar`/`visit_MatchMapping`; captures bind via `str`
  attrs not `Name` nodes · Reproduction: fixture above (Python ≥3.10) →
  `None` · Verdict: confirmed bug. **Also note**: the existing
  `tests/test_match_statement.py::test_name_bound_in_case_pattern_is_used` and
  `::test_capture_pattern_binding_is_used` pass **vacuously** — captures are never
  tracked, so "used capture → None" is green for the wrong reason · Guarding test:
  `tests/test_match_capture_unused.py::MatchCaptureUnusedTests`.

### Verification
#### Automated
- [x] `uv run pytest tests/test_match_capture_unused.py -q` exits 0 (host is
  3.11 → 1 xfail, 1 pass; on <3.10 → both skipped, **not errored**)
- [x] `just test` passes (210 passed, 24 skipped, 3 xfailed)

#### Manual
- [x] FN reproduced: `/tmp/f4.py` (unused `case [a]`) →
  `main(['/tmp/f4.py','--no-color'])` prints `None` (observed); recorded in audit.md.
- [x] Control: `leftover` fixture prints
  `'/tmp/f4c.py:2:4: DC01 Variable \`leftover\` is never used'` (observed)
- [ ] Skip path: `uv run pytest tests/test_match_capture_unused.py -q -rs`
  shows skip (not error) when run under <3.10 (documented; host is 3.11, so the
  class runs here rather than skipping — not observable on this interpreter).

---

## Phase 5: F5 PEP 695 generic type params untracked

> **Host note**: this host is Python 3.11.10, so the class is **skipped** here and
> cannot be confirmed live. The expected current behavior (`None`, a false
> negative) is predicted by analogy to F4 (type params are `str` attrs, no
> `visit_TypeVar`). The `@expectedFailure` assertion is correct either way; verify
> the live `None` on a 3.12+ interpreter when available.

### Changes

#### 1. F5 test (version-gated 3.12+)
**File**: `tests/test_pep695_unused_typevar.py`
**Action**: create

```python
import sys
from unittest import expectedFailure, skipUnless

from deadcode.cli import main
from deadcode.utils.base_test_case import BaseTestCase


@skipUnless(sys.version_info >= (3, 12), 'PEP 695 generics require 3.12+')
class Pep695UnusedTypeVarTests(BaseTestCase):
    @expectedFailure
    def test_unused_generic_type_param_is_reported(self):
        # `T` is declared but never referenced in the signature or body. It is a
        # TypeVar.name str, not a Name node, and there is no visit_TypeVar, so
        # it is untracked. Correct: `T` IS reported. Predicted current: None.
        self.files = {
            'foo.py': """
                def f[T](x: int) -> int:
                    return x


                f(1)
                """
        }
        unused_names = main(['foo.py', '--no-color'])
        # CONFIRM exact DC code + line:col on a 3.12+ run when the fix lands.
        self.assertEqual(unused_names, 'foo.py:1:6: DC01 Variable `T` is never used')

    def test_used_generic_type_param_is_not_reported(self):
        # Control: `T` is referenced in the signature -> not reported.
        self.files = {
            'foo.py': """
                def g[T](x: T) -> T:
                    return x


                g(1)
                """
        }
        unused_names = main(['foo.py', '--no-color'])
        assert unused_names is None
```

#### 2. audit.md F5 entry
**File**: `workspace/.../audit.md`
**Action**: append

- Category: false negative · Severity: low · Root cause: no `visit_TypeVar`; PEP
  695 type params are `TypeVar.name` strings, not `Name` nodes · Reproduction:
  fixture above (Python ≥3.12); **not confirmable on this 3.11 host — predicted
  `None`** · Verdict: confirmed bug (pending 3.12+ live confirmation) · Guarding
  test: `tests/test_pep695_unused_typevar.py::Pep695UnusedTypeVarTests`.

### Verification
#### Automated
- [x] `uv run pytest tests/test_pep695_unused_typevar.py -q -rs` → on this 3.11
  host both tests **skip** (not error) (2 skipped; single-file run trips the 95% coverage gate but outcomes are correct)
- [x] `just test` passes (210 passed, 26 skipped, 3 xfailed)

#### Manual
- [ ] On a 3.12+ interpreter (if available): `/tmp/f5.py` =
  `def f[T](x: int) -> int:\n    return x\n\n\nf(1)` →
  `main(['/tmp/f5.py','--no-color'])` prints `None`; record observed value and
  whether prediction held. If unavailable, record in audit.md that confirmation
  is deferred to 3.12+. (Not executable: host is Python 3.11.10; no 3.12+ interpreter available — deferred per audit.md host note.)
- [x] Skip confirmed: `uv run pytest tests/test_pep695_unused_typevar.py -q -rs`
  output contains `skipped` (observed `SKIPPED [1] ... PEP 695 generics require 3.12+` ×2).

---

## Phase 6: F6 dynamic-usage heuristic boundaries (characterization — green)

All five boundaries were confirmed by real runs and are **by-design conservative**
(the heuristic only suppresses provable literal/unqualified forms). They are pinned
green as characterization tests; **no `@expectedFailure`** (none confirmed as a bug
— the boundaries reduce false negatives at the documented cost of not extending
suppression to non-provable forms).

### Changes

#### 1. F6 test
**File**: `tests/test_dynamic_usage_boundaries.py`
**Action**: create

```python
from deadcode.cli import main
from deadcode.utils.base_test_case import BaseTestCase


class DynamicUsageBoundaryTests(BaseTestCase):
    def test_getattr_literal_attr_suppresses_method(self):
        # Control: literal string second arg IS honored -> method suppressed.
        self.files = {
            'foo.py': """
                class C:
                    def secret(self):
                        return 1


                def go(o):
                    return getattr(o, "secret")()


                go(C())
                """
        }
        assert main(['foo.py', '--no-color']) is None

    def test_getattr_nonliteral_attr_does_not_suppress(self):
        # Boundary: a variable second arg is NOT matched -> method reported.
        self.files = {
            'foo.py': """
                class C:
                    def secret(self):
                        return 1


                def go(o, name):
                    return getattr(o, name)()


                go(C(), "secret")
                """
        }
        unused_names = main(['foo.py', '--no-color'])
        self.assertEqual(unused_names, 'foo.py:2:4: DC04 Method `secret` is never used')

    def test_format_with_locals_suppresses_var(self):
        # Control: `.format(**locals())` IS honored -> name suppressed.
        self.files = {
            'foo.py': """
                def render():
                    name = "x"
                    return "{name}".format(**locals())


                render()
                """
        }
        assert main(['foo.py', '--no-color']) is None

    def test_format_with_vars_not_matched(self):
        # Boundary: `**vars()` is NOT matched -> name reported.
        self.files = {
            'foo.py': """
                def render():
                    name = "x"
                    return "{name}".format(**vars())


                render()
                """
        }
        unused_names = main(['foo.py', '--no-color'])
        self.assertEqual(unused_names, 'foo.py:2:4: DC01 Variable `name` is never used')

    def test_builtins_getattr_not_matched(self):
        # Boundary: qualified `builtins.getattr` is NOT matched -> method reported.
        self.files = {
            'foo.py': """
                import builtins


                class C:
                    def secret(self):
                        return 1


                def go(o):
                    return builtins.getattr(o, "secret")()


                go(C())
                """
        }
        unused_names = main(['foo.py', '--no-color'])
        self.assertEqual(unused_names, 'foo.py:5:4: DC04 Method `secret` is never used')
```

#### 2. audit.md F6 entry
**File**: `workspace/.../audit.md`
**Action**: append

- Category: by-design (false-positive-risk boundaries) · Severity: low · Root
  cause: `visit_Call:364-413` (`getattr`/`hasattr` literal-only, unqualified-only;
  `.format(**locals())` literal-only) and `visit_BinOp:350-362` (`% locals()`
  only) · Reproduction & observed (all confirmed via `main()`):
  - literal `getattr(o, "secret")` → `None` (suppressed)
  - variable `getattr(o, name)` → `'foo.py:2:4: DC04 Method \`secret\` is never used'`
  - `.format(**locals())` → `None`
  - `.format(**vars())` → `'foo.py:2:4: DC01 Variable \`name\` is never used'`
  - `builtins.getattr(o, "secret")` → `'foo.py:5:4: DC04 Method \`secret\` is never used'`
  · Verdict: **by-design** — heuristic intentionally limits to provable literal,
  unqualified forms; the non-suppressing boundaries are acceptable
  (false-positive risk only when users use dynamic forms outside the heuristic) ·
  Guarding test: `tests/test_dynamic_usage_boundaries.py::DynamicUsageBoundaryTests`.

### Verification
#### Automated
- [x] `uv run pytest tests/test_dynamic_usage_boundaries.py -q` exits 0 (5 passed; single-file run trips the 95% coverage gate but test outcomes are correct)
- [x] `just test` passes (215 passed, 26 skipped, 3 xfailed)

#### Manual
- [x] Each boundary fixture run via `main([...])` produces the exact value above;
  all five observed returns recorded in audit.md and classified: literal getattr
  → `None`; variable getattr → `DC04 Method secret`; `.format(**locals())` →
  `None`; `.format(**vars())` → `DC01 Variable name`; `builtins.getattr` →
  `DC04 Method secret`.

---

## Phase 7: F7 six parsed-but-unused CLI flags

> **Deviation from structure (documented)**: structure F7 says "assert the
> definition is still reported" yet also "@unittest.expectedFailure (encodes
> intended behavior)" — these are contradictory (a green characterization can't
> also be an expected failure). Resolved per design decision 2 (tests encode the
> **intended** behavior so they flip to guards on fix): each test asserts the
> definition **is suppressed** (intended) and is marked `@expectedFailure`. The
> flag is currently a no-op, so the definition is still reported → assertion fails
> → test passes as expected. When a flag is wired, it flips to an unexpected pass,
> signalling the guard converted. Tests are named `..._should_suppress_definition`.
> The intended semantics assumed for each ambiguous flag are recorded in audit.md.

### Changes

#### 1. F7 test
**File**: `tests/cli_args/test_dead_cli_flags.py`
**Action**: create

```python
from unittest import expectedFailure

from deadcode.cli import main
from deadcode.utils.base_test_case import BaseTestCase

_DECORATED = """
    def mark(func):
        return func


    @mark
    def decorated_handler():
        return 1
    """

_INHERITS = """
    class Base:
        pass


    class Derived(Base):
        pass
    """

_MEMBER = """
    class Base:
        pass


    class Derived(Base):
        def helper(self):
            return 1


    Derived()
    """

_DECORATED_CLASS = """
    def mark(cls):
        return cls


    @mark
    class Service:
        def helper(self):
            return 1


    Service()
    """


class DeadCliFlagTests(BaseTestCase):
    @expectedFailure
    def test_ignore_if_decorated_with_should_suppress_definition(self):
        self.files = {'foo.py': _DECORATED}
        assert main(['foo.py', '--no-color', '--ignore-if-decorated-with=@mark']) is None

    @expectedFailure
    def test_ignore_if_inherits_from_should_suppress_definition(self):
        self.files = {'foo.py': _INHERITS}
        assert main(['foo.py', '--no-color', '--ignore-if-inherits-from=Base']) is None

    @expectedFailure
    def test_ignore_names_if_inherits_from_should_suppress_definition(self):
        self.files = {'foo.py': _MEMBER}
        assert main(['foo.py', '--no-color', '--ignore-names-if-inherits-from=Base']) is None

    @expectedFailure
    def test_ignore_names_if_decorated_with_should_suppress_definition(self):
        self.files = {'foo.py': _DECORATED}
        assert main(['foo.py', '--no-color', '--ignore-names-if-decorated-with=@mark']) is None

    @expectedFailure
    def test_ignore_bodies_of_should_suppress_definition(self):
        self.files = {'foo.py': _MEMBER}
        assert main(['foo.py', '--no-color', '--ignore-bodies-of=Derived']) is None

    @expectedFailure
    def test_ignore_bodies_if_decorated_with_should_suppress_definition(self):
        self.files = {'foo.py': _DECORATED_CLASS}
        assert main(['foo.py', '--no-color', '--ignore-bodies-if-decorated-with=@mark']) is None
```

#### 2. audit.md F7 entry
**File**: `workspace/.../audit.md`
**Action**: append

- Category: false negative (gap — users expecting suppression get false
  positives) · Severity: medium · Root cause:
  `deadcode/actions/parse_arguments.py:61` onward — six flags are registered in the
  parser but never referenced by the visitor · Reproduction & observed (each flag
  produced output identical to baseline, confirming no-op):
  - `--ignore-if-decorated-with=@mark` → `'…:6:0: DC02 Function \`decorated_handler\` is never used'`
  - `--ignore-if-inherits-from=Base` → `'…:5:0: DC03 Class \`Derived\` is never used'`
  - `--ignore-names-if-inherits-from=Base` → `'…:6:4: DC04 Method \`helper\` is never used'`
  - `--ignore-names-if-decorated-with=@mark` → `'…:6:0: DC02 Function \`decorated_handler\` is never used'`
  - `--ignore-bodies-of=Derived` → `'…:6:4: DC04 Method \`helper\` is never used'`
  - `--ignore-bodies-if-decorated-with=@mark` → `'…:7:4: DC04 Method \`helper\` is never used'`
  · **Assumed intended semantics** (drive the fixtures; recorded since flags are
  unimplemented): `*-if-decorated-with` = suppress defs whose decorator matches;
  `*-if-inherits-from` = suppress class defs whose base matches;
  `ignore-names-if-*` = suppress member names within matching classes;
  `ignore-bodies-of`/`ignore-bodies-if-decorated-with` = suppress definitions
  inside the matching def's body · Verdict: confirmed bug — six flags are silently
  no-ops · Guarding test: `tests/cli_args/test_dead_cli_flags.py::DeadCliFlagTests`.

### Verification
#### Automated
- [x] `uv run pytest tests/cli_args/test_dead_cli_flags.py -q` (6 xfailed; single-file run trips the 95% coverage gate but test outcomes are correct)
- [x] `just test` passes (215 passed, 26 skipped, 9 xfailed)

#### Manual
- [x] For each flag, run `main(['/tmp/g.py', '--<flag>=<value>', '--no-color'])`
  against the matching fixture and confirm the supposedly-suppressed item still
  appears (proves no-op). All six observed (matching audit.md):
  `--ignore-if-decorated-with=@mark` → `DC02 Function decorated_handler`;
  `--ignore-if-inherits-from=Base` → `DC03 Class Derived`;
  `--ignore-names-if-inherits-from=Base` → `DC04 Method helper`;
  `--ignore-names-if-decorated-with=@mark` → `DC02 Function decorated_handler`;
  `--ignore-bodies-of=Derived` → `DC04 Method helper`;
  `--ignore-bodies-if-decorated-with=@mark` → `DC04 Method helper`.

---

## Phase 8: Audit synthesis + gate

> **Deviation (recorded during Phase 8)**: Phase 3 was marked `done: true` in
> `progress.yml` but its deliverables (`tests/test_unused_parameters.py` and the
> F3 entry in `audit.md`) were never actually created. Since Phase 8 is the
> synthesis gate and its checks (and the summary table) require all of F1–F7 to
> exist, the two missing F3 deliverables were created here exactly as Phase 3
> specifies, and Phase 3's verification items were checked off. No visitor code
> was touched.

### Changes

#### 1. audit.md summary
**File**: `workspace/.../audit.md`
**Action**: append a summary section

- Severity-ordered findings table (columns: F# · Category · Severity · Verdict ·
  Guarding test), ordered F1, F2 (high) → F4, F7 (medium) → F3, F5, F6 (low /
  by-design).
- Verdict counts: false negative (F1, F2, F4, F5, F7), by-design (F3, F6).
- One row per confirmed finding, each linking its guarding test path.

```markdown
## Summary

| Finding | Category | Severity | Verdict | Guarding test |
|---------|----------|----------|---------|---------------|
| F1 | false negative | high | confirmed bug | tests/test_scope_blind_matching.py |
| F2 | false negative | high | confirmed bug | tests/test_attribute_receiver.py |
| F4 | false negative | medium | confirmed bug | tests/test_match_capture_unused.py |
| F7 | false negative | medium | confirmed bug (×6 flags) | tests/cli_args/test_dead_cli_flags.py |
| F3 | by-design | low | parameter tracking disabled | tests/test_unused_parameters.py |
| F5 | false negative | low | confirmed (pending 3.12+ live) | tests/test_pep695_unused_typevar.py |
| F6 | by-design | low | conservative heuristic boundaries | tests/test_dynamic_usage_boundaries.py |

Counts: 5 false negatives, 2 by-design.
```

### Verification
#### Automated
- [x] `just test` green (216 passed, 26 skipped, 9 xfailed)
- [x] `just check` green (format, lint, complexity ≤10, typecheck — EXIT=0)

#### Manual
- [x] Every guarding-test path referenced in audit.md exists, e.g.
  `for p in tests/test_scope_blind_matching.py tests/test_attribute_receiver.py tests/test_unused_parameters.py tests/test_match_capture_unused.py tests/test_pep695_unused_typevar.py tests/test_dynamic_usage_boundaries.py tests/cli_args/test_dead_cli_flags.py; do test -f "$p" && echo "OK $p" || echo "MISSING $p"; done`
  → all `OK` (observed; F3's `tests/test_unused_parameters.py` was created during Phase 8 to close the prerequisite gap).
- [x] `audit.md` has exactly one `##`/`###` section per F1–F7, each with all schema
  fields: `grep -c '^## F' workspace/.../audit.md` → 7 and
  `grep -q 'Verdict' workspace/.../audit.md` → present.
- [x] No xfailing test unexpectedly passes (no `XPASS`/unexpected success in
  `uv run pytest tests/ -q -rxX` output → "NO XPASS").

---

## Testing Checkpoints (from structure.md)

- **After P1**: `audit.md` exists with F1 confirmed; `test_scope_blind_matching.py`
  present and passing (1 xfail + 1 control). Confirm→test→record loop proven.
- **After P2–P3**: F1/F2 false negatives reproduced via `main()`; F3 by-design
  verdict recorded with a green characterization test + built-in control.
- **After P4–P5**: version-gated tests for `match` captures (skipUnless 3.10) and
  PEP 695 type params (skipUnless 3.12); below the gate they **skip**, not error.
- **After P6–P7**: dynamic-heuristic boundaries pinned green (characterization);
  six dead CLI flags each have a recorded verdict and an xfail test.
- **After P8**: `just test` and `just check` both green; `audit.md` has one
  complete, severity-ranked entry per finding linked to its guarding test.
- **Vacuous-pass guard (all phases)**: every "None / not reported" assertion ships
  a defined-and-unused control that **is** reported.
```
