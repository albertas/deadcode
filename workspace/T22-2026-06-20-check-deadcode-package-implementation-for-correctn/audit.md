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
- **Reproduction**: (fixture below) `main(['/tmp/f1.py', '--no-color'])` → `None`
  (observed). `B.run` is genuinely unused but a `Load` of `run` from `A().run()`
  marks the name globally used.

  ```python
  class A:
      def run(self):
          return 1


  class B:
      def run(self):
          return 2


  A().run()
  B()
  ```

  Control (distinctly-named unused method) →
  `'/tmp/f1c.py:7:4: DC04 Method \`distinctly_unused\` is never used'` (observed),
  proving the visitor ran and the gap is specific to name collisions.
- **Verdict**: confirmed bug. A use of name `x` anywhere marks every definition
  named `x` used.
- **Guarding test**:
  `tests/test_scope_blind_matching.py::ScopeBlindMatchingTests`

## F2 — Attribute receiver ignored

- **Category**: false negative
- **Severity**: high (any `.foo` Load marks all `.foo` attrs and same-named
  funcs/vars used)
- **Root cause**: `deadcode/visitor/find_unused_code_visitor.py:348`
  (`visit_Attribute`, `Load` → `add_used_name(node.attr)`) — only the bare
  attribute name is recorded, with no receiver tracking, so the name string
  cross-contaminates unrelated definitions.
- **Reproduction**: (fixture below) `main(['/tmp/f2.py', '--no-color'])` → `None`
  (observed). The module function `value` is never called, but the bare-attr Load
  `obj.value` marks the name `value` used globally.

  ```python
  def value():
      return 1


  class C:
      def go(self, obj):
          return obj.value


  C().go(None)
  ```

  Control (distinctly-named unused function) →
  `'/tmp/f2c.py:1:0: DC02 Function \`distinctly_unused\` is never used'` (observed),
  proving the visitor ran and the gap is specific to attribute-name collisions.
- **Verdict**: confirmed bug. Any `.foo` Load marks all `.foo` attributes and
  same-named functions/variables used.
- **Guarding test**:
  `tests/test_attribute_receiver.py::AttributeReceiverTests`

## F3 — Parameters never reported

- **Category**: by-design
- **Severity**: low (unused function/method parameters are never flagged)
- **Root cause**: `deadcode/visitor/find_unused_code_visitor.py:337`
  (`# def visit_arg` commented out; `ast.Param` is a Python-2-era context, so
  modern `ast.arg` parameters are not registered as definitions).
- **Reproduction**: (fixture below) `main(['/tmp/f3.py', '--no-color'])` →
  `'/tmp/f3.py:2:4: DC01 Variable \`x\` is never used'` (observed) — only the
  unused local `x` is reported, never the unused parameter `unused_param`.

  ```python
  def f(unused_param):
      x = 1
      return 0


  f(2)
  ```

  The built-in control is the unused local `x`, which IS reported — proving the
  visitor ran and the gap is parameter-specific.
- **Verdict**: by-design — parameter tracking is deliberately disabled. Pinned
  green as a characterization test (no `@expectedFailure`).
- **Guarding test**:
  `tests/test_unused_parameters.py::UnusedParameterTests`

## F4 — Match-capture patterns untracked

- **Category**: false negative
- **Severity**: medium (every `match`/`case` capture that is bound but never read
  goes unreported on Python ≥3.10)
- **Root cause**: there is no `visit_MatchAs`/`visit_MatchStar`/`visit_MatchMapping`
  in `deadcode/visitor/find_unused_code_visitor.py` (only `visit_MatchClass` at
  `:526-529`). Capture patterns bind names via `str` attributes
  (`MatchAs.name`, `MatchStar.name`, `MatchMapping.rest`), not `Name` nodes, so
  generic recursion never records them as definitions.
- **Reproduction**: (fixture below, Python ≥3.10) `main(['/tmp/f4.py', '--no-color'])`
  → `None` (observed on host Python 3.11.10). The capture `a` in `case [a]` is
  bound but never read, yet it is not reported.

  ```python
  def handle(command):
      match command:
          case [a]:
              return 0
          case _:
              return 1


  handle([1])
  ```

  Control (ordinary unused local `leftover` in the same function) →
  `'/tmp/f4c.py:2:4: DC01 Variable \`leftover\` is never used'` (observed), proving
  the visitor ran inside the `match` construct and the gap is capture-specific.
- **Also note**: the existing
  `tests/test_match_statement.py::test_name_bound_in_case_pattern_is_used` and
  `::test_capture_pattern_binding_is_used` pass **vacuously** — captures are never
  tracked, so "used capture → None" is green for the wrong reason.
- **Verdict**: confirmed bug. Match-capture bindings are never registered as
  definitions and so can never be reported as unused.
- **Guarding test**:
  `tests/test_match_capture_unused.py::MatchCaptureUnusedTests`

## F5 — PEP 695 generic type params untracked

- **Category**: false negative
- **Severity**: low (only affects unused PEP 695 type parameters, a niche
  3.12+ construct)
- **Root cause**: there is no `visit_TypeVar` (nor any handling of `type_params`)
  in `deadcode/visitor/find_unused_code_visitor.py`. PEP 695 type parameters are
  exposed as `TypeVar.name` strings, not `ast.Name` nodes, so they are never
  registered as definitions and can never be reported as unused.
- **Reproduction**: (fixture below, Python ≥3.12) `main(['foo.py', '--no-color'])`
  → predicted `None`. `T` is declared in `def f[T](...)` but never referenced.

  ```python
  def f[T](x: int) -> int:
      return x


  f(1)
  ```

  **Host note**: this host is Python 3.11.10, so the construct does not parse and
  the guarding test class is **skipped** here. Live confirmation of the `None`
  return is deferred to a 3.12+ interpreter; the prediction is by analogy to F4
  (type params bind via `str` attrs, with no specialized visitor).

  Control (`T` referenced in the signature, `def g[T](x: T) -> T`) → `None`
  (not reported), which is the correct behavior whether or not the bug is fixed.
- **Verdict**: confirmed bug (pending 3.12+ live confirmation). PEP 695 type
  parameters are never tracked, so an unused type param is a false negative.
- **Guarding test**:
  `tests/test_pep695_unused_typevar.py::Pep695UnusedTypeVarTests`

## F6 — Dynamic-usage heuristic boundaries

- **Category**: by-design (false-positive-risk boundaries)
- **Severity**: low (the heuristic only suppresses provable literal/unqualified
  forms; non-provable dynamic forms fall outside it by design)
- **Root cause**: `deadcode/visitor/find_unused_code_visitor.py` `visit_Call`
  (`:364-413`) honors `getattr`/`hasattr` only with a literal string second
  argument and only when the call is unqualified, and honors `.format(**locals())`
  only for the literal `locals()` form; `visit_BinOp` (`:350-362`) honors only the
  `% locals()` form. Anything outside these provable shapes is not treated as a
  use.
- **Reproduction & observed** (all confirmed via `main(['foo.py', '--no-color'])`):
  - literal `getattr(o, "secret")` → `None` (method suppressed)
  - variable `getattr(o, name)` →
    `'foo.py:2:4: DC04 Method \`secret\` is never used'`
  - `.format(**locals())` → `None` (name suppressed)
  - `.format(**vars())` →
    `'foo.py:2:4: DC01 Variable \`name\` is never used'`
  - `builtins.getattr(o, "secret")` →
    `'foo.py:5:4: DC04 Method \`secret\` is never used'`
- **Verdict**: by-design — the heuristic intentionally limits suppression to
  provable literal, unqualified forms. The non-suppressing boundaries are
  acceptable: extending suppression to non-provable dynamic forms (variable
  attribute names, `**vars()`, qualified `builtins.getattr`) would trade a few
  false negatives for broad false negatives. Pinned green as characterization;
  **no `@expectedFailure`** (no boundary is confirmed as a bug).
- **Guarding test**:
  `tests/test_dynamic_usage_boundaries.py::DynamicUsageBoundaryTests`

## F7 — Six parsed-but-unused CLI flags

- **Category**: false negative (gap — users expecting suppression get false
  positives)
- **Severity**: medium (six documented CLI flags are silently no-ops)
- **Root cause**: `deadcode/actions/parse_arguments.py:61` onward registers the
  six flags in the parser (and they populate the `Args` dataclass), but the
  visitor (`deadcode/visitor/find_unused_code_visitor.py` / `ignore.py`) never
  references them, so they have no effect on analysis.
- **Reproduction & observed** (each flag produced output identical to baseline,
  confirming the flag is a no-op; all confirmed via `main([...])`):
  - `--ignore-if-decorated-with=@mark` →
    `'/tmp/g_decorated.py:6:0: DC02 Function \`decorated_handler\` is never used'`
  - `--ignore-if-inherits-from=Base` →
    `'/tmp/g_inherits.py:5:0: DC03 Class \`Derived\` is never used'`
  - `--ignore-names-if-inherits-from=Base` →
    `'/tmp/g_member.py:6:4: DC04 Method \`helper\` is never used'`
  - `--ignore-names-if-decorated-with=@mark` →
    `'/tmp/g_decorated.py:6:0: DC02 Function \`decorated_handler\` is never used'`
  - `--ignore-bodies-of=Derived` →
    `'/tmp/g_member.py:6:4: DC04 Method \`helper\` is never used'`
  - `--ignore-bodies-if-decorated-with=@mark` →
    `'/tmp/g_decorated_class.py:7:4: DC04 Method \`helper\` is never used'`
- **Assumed intended semantics** (drive the fixtures; recorded since the flags
  are unimplemented): `*-if-decorated-with` = suppress definitions whose
  decorator matches; `*-if-inherits-from` = suppress class definitions whose base
  matches; `ignore-names-if-*` = suppress member names within matching classes;
  `ignore-bodies-of` / `ignore-bodies-if-decorated-with` = suppress definitions
  inside the matching definition's body.
- **Note on test shape**: structure F7 was ambiguous (it asked to "assert the
  definition is still reported" yet also marked the test `@expectedFailure` — a
  green characterization cannot also be an expected failure). Resolved per design
  decision 2: each test asserts the definition **is suppressed** (the intended
  behavior) and is marked `@expectedFailure`. The flag is currently a no-op, so
  the definition is still reported → the assertion fails → the test passes as an
  expected failure. When a flag is wired up, the test flips to an unexpected pass,
  signalling the guard converted. Tests are named `..._should_suppress_definition`.
- **Verdict**: confirmed bug — six flags are silently no-ops.
- **Guarding test**:
  `tests/cli_args/test_dead_cli_flags.py::DeadCliFlagTests`

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
