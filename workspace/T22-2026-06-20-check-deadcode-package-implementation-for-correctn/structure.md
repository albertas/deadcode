# Structure Outline

## Approach

Audit the `deadcode` detection logic for correctness gaps and land regression
tests — **no visitor fixes** (per design decision 1). Each phase is one candidate
finding (F1–F7): reproduce it by actually running `main([...])` (decision 5),
record a verdict (false positive / false negative / by-design) in a single
`audit.md`, and land a `BaseTestCase` test that encodes the **correct** expected
behavior. Tests that expose a real bug are marked `@unittest.expectedFailure` so
they flip to regression guards when a fix lands (decision 2); correct-but-surprising
behavior is pinned green as a characterization test (decision 4). Every "not
reported" assertion is paired with a *defined-and-unused sibling of the same name*
that **is** reported, to defeat vacuous passes (Open Risks).

Slices are ordered by blast radius (decision 3): F1/F2 (flat-string scope-blindness)
first and highest severity; PEP 695 / match captures lower. Phase 1 establishes the
`audit.md` format and the confirm→test→record loop that every later phase reuses; if
any later phase fails, all prior phases remain independently valuable (a confirmed
finding + its test).

Convention used below: audit report at
`workspace/T22-.../audit.md`; tests under the existing `tests/` tree.

---

## Phase 1: Audit scaffold + F1 scope-blind flat matching

Establish `audit.md` (finding template: category, reproduction, root cause
`file:line`, severity, verdict) and confirm the highest-severity gap: a `Load` of
name `x` anywhere marks **every** definition named `x` used (`ignore.py:40`, `:325`).

**Files**: `audit.md` (new), `tests/test_scope_blind_matching.py` (new)
**Key changes**:
- `audit.md` finding entry schema (markdown section per F#): `Category`,
  `Reproduction` (source + exact `main()` argv), `Root cause` (`file:line`),
  `Severity`, `Verdict`.
- `test_unused_method_shadowed_by_unrelated_use_is_reported(self)` — two classes
  each with method `run`; one `run` used, the other genuinely unused →
  **correct** behavior asserts the unused one IS reported. Mark
  `@unittest.expectedFailure` (current tool reports `None`).

**Verify**: `just test` passes (expectedFailure counts as pass).
Manual (agent-executable): run
`python -c "from deadcode.cli import main; print(main(['/tmp/f1.py','--no-color']))"`
against a two-class fixture where only one same-named method is used; confirm
output is `None` (proves the false negative), then confirm the new test file is
collected: `python -m pytest tests/test_scope_blind_matching.py -q` exits 0.

---

## Phase 2: F2 attribute receiver ignored

Confirm any `.foo` Load marks all `.foo` attrs **and** same-named funcs/vars used —
cross-contamination across receivers (`visit_Attribute:344-348`).

**Files**: `tests/test_attribute_receiver.py` (new), `audit.md` (append F2)
**Key changes**:
- `test_unused_attribute_with_same_name_used_elsewhere_is_reported(self)` —
  `a.value` used on one object, `self.value` defined-and-unused on an unrelated
  class → asserts the unused attr IS reported. `@unittest.expectedFailure`.
- Sibling positive control: a distinctly-named unused attr in same fixture IS
  reported (proves mechanism ran).

**Verify**: `just test` passes. Manual: run `main(['/tmp/f2.py','--no-color'])` on a
fixture where a function named `value` is shadowed by a used `.value` attribute;
confirm the function is NOT in output (false negative reproduced) and record the
exact returned string in `audit.md`.

---

## Phase 3: F3 parameters never reported (by-design verdict)

`visit_arg` is commented out (`:337-339`) → unused params undetected. Likely
intentional; record a verdict and pin current behavior.

**Files**: `tests/test_unused_parameters.py` (new), `audit.md` (append F3)
**Key changes**:
- `test_unused_parameter_is_not_reported(self)` — characterization test, asserts
  `main()` returns `None` for a function with an unused param (pins current
  behavior **green**, no expectedFailure).
- Control: an unused local variable in the same function IS reported (proves the
  visitor ran and the gap is param-specific).

**Verify**: `just test` passes green. Manual: `main(['/tmp/f3.py','--no-color'])`
on `def f(unused_param): x = 1` returns only the `x` finding; record verdict
"by-design — param tracking deliberately disabled" with evidence in `audit.md`.

---

## Phase 4: F4 match-capture patterns untracked

`MatchAs`/`MatchStar`/`MatchMapping` rest bind via `str` attrs, not `Name` nodes →
genuinely unused captures undetected; existing `test_match_statement.py` "used
capture" tests pass vacuously. Confirm and document the vacuity.

**Files**: `tests/test_match_capture_unused.py` (new), `audit.md` (append F4)
**Key changes**:
- `@skipUnless(sys.version_info >= (3, 10), ...)` on the class (add the gate the
  existing file lacks — Patterns to Follow).
- `test_unused_match_capture_is_reported(self)` — `match x: case [a]:` where `a`
  is never read → asserts capture IS reported. `@unittest.expectedFailure`.
- Note in `audit.md` that the existing "used capture" tests are green for the
  wrong reason.

**Verify**: `just test` passes. Manual: on Python ≥3.10 run
`main(['/tmp/f4.py','--no-color'])` for an unused `case` capture; confirm `None`
(false negative). On <3.10 confirm the class is skipped:
`python -m pytest tests/test_match_capture_unused.py -q` reports skipped, not error.

---

## Phase 5: F5 PEP 695 generic type params untracked

`def f[T]` / `class C[T]`: `T` is a `TypeVar.name` str, not a `Name` → unused type
params undetected (low severity). No `visit_TypeVar`.

**Files**: `tests/test_pep695_unused_typevar.py` (new), `audit.md` (append F5)
**Key changes**:
- `@skipUnless(sys.version_info >= (3, 12), ...)` on the class (matches
  `test_type_alias.py:8`).
- `test_unused_generic_type_param_is_reported(self)` — `def f[T](x: int)` where
  `T` is never referenced → asserts IS reported. `@unittest.expectedFailure`.
- Control: a used `T` (`def g[T](x: T)`) returns `None` (sibling proves mechanism).

**Verify**: `just test` passes. Manual: on Python ≥3.12 run
`main(['/tmp/f5.py','--no-color'])` for the unused-`T` fixture; confirm `None`.
On <3.12 confirm the class is skipped (pytest reports skipped).

---

## Phase 6: F6 dynamic-usage heuristic boundaries

Confirm false-positive-avoidance boundaries of `getattr`/`hasattr`,
`.format(**locals())`, `% locals()` (`visit_Call:364-413`, `visit_BinOp:350-362`).
These are characterization tests — pin exactly where the heuristic stops.

**Files**: `tests/test_dynamic_usage_boundaries.py` (new), `audit.md` (append F6)
**Key changes**:
- `test_getattr_with_nonliteral_attr_does_not_suppress(self)` — `getattr(o, name)`
  (variable arg) → the targeted method, if otherwise unused, IS reported
  (potential false positive). Verdict recorded; `@unittest.expectedFailure` only
  if confirmed as a *bug*, else characterization (green).
- `test_format_with_vars_not_matched(self)` and
  `test_builtins_getattr_not_matched(self)` — same pattern for the documented
  boundaries (`format(**vars())`, qualified `builtins.getattr`).

**Verify**: `just test` passes. Manual: run `main()` on each boundary fixture and
record the exact returned string (reported vs `None`) in `audit.md`; classify each
boundary as false-positive-risk or acceptable with evidence.

---

## Phase 7: F7 six parsed-but-unused CLI flags

`--ignore-if-decorated-with`, `--ignore-if-inherits-from`,
`--ignore-names-if-inherits-from`, `--ignore-names-if-decorated-with`,
`--ignore-bodies-of`, `--ignore-bodies-if-decorated-with` parse but never affect
output (`parse_arguments.py:60-149`) → users get false positives.

**Files**: `tests/cli_args/test_dead_cli_flags.py` (new), `audit.md` (append F7)
**Key changes**:
- One `test_<flag>_has_no_effect_on_output(self)` per flag — pass the flag with a
  value that *should* suppress a definition; assert the definition is still
  reported. `@unittest.expectedFailure` (encodes intended behavior).
- Each documents the flag is silently a no-op.

**Verify**: `just test` passes. Manual: for each flag run
`main(['/tmp/f7.py', '--<flag>=<value>', '--no-color'])`; confirm the supposedly
-suppressed item still appears in output (proves no-op); list all six confirmed in
`audit.md`.

---

## Phase 8: Audit synthesis + gate

Rank all confirmed findings by severity, summarize counts (false positive / false
negative / by-design), and ensure the full suite + checks are green.

**Files**: `audit.md` (summary table + severity ranking)
**Key changes**: severity-ordered findings table (F1/F2 highest); per-finding
links to the test that guards it.

**Verify**: `just test` green AND `just check` green (format, lint, complexity ≤10,
typecheck). Manual: `audit.md` contains exactly one entry per confirmed F# with all
five schema fields; grep each test file path referenced in `audit.md` exists
(`test -f <path>` for each).

---

## Testing Checkpoints

- **After P1**: `audit.md` exists with F1 confirmed; `test_scope_blind_matching.py`
  present and passing (expectedFailure). The confirm→test→record loop is proven.
- **After P2–P3**: F1/F2 false negatives reproduced via `main()`; F3 verdict
  (by-design) recorded with a green characterization test + control.
- **After P4–P5**: version-gated tests for `match` captures and PEP 695 type params;
  on an interpreter below the gate they **skip**, not error.
- **After P6–P7**: dynamic-heuristic boundaries and the six dead CLI flags each have
  a recorded verdict and a test; expectedFailure used only for confirmed bugs.
- **After P8**: `just test` and `just check` both green; `audit.md` has one
  complete, severity-ranked entry per finding, each linked to its guarding test.
- **Vacuous-pass guard (all phases)**: every "not reported" test ships a
  same-named-or-sibling defined-and-unused control that **is** reported.

## Note on slicing

These slices are vertical in the audit sense — each crosses *reproduce →
test-encode → report-record* end-to-end for one finding and is independently
valuable. There is no DB/API/UI stack here (a CLI static-analysis library), so
"layers" map to reproduction, regression test, and audit entry.
