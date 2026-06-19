# Implementation Plan

## Overview

Three independent, test-first correctness fixes to `deadcode`: repair the
`does_include` self-comparison so multi-part edits aren't dropped, align `# noqa`
detection with flake8 (any whitespace + lowercase codes), and recognize
`__all__ += [...]` / `__all__: ... = [...]` exports so those names aren't false
positives. No architectural change; the flat `used_names` scope limitation stays
out of scope.

**Path note (applies to all phases):** the structure outline wrote test paths as
`deadcode/tests/...`, but the tests actually live in the top-level `tests/`
directory (verified: `tests/actions/test_merge_overlaping_file_parts.py`,
`tests/noqa/test_noqa_comments.py`, `tests/visitor/test_find_unused_code_visitor.py`).
The implementation files are under `deadcode/`. Paths below are corrected
accordingly.

**Pre-confirmation of Phase 3 (Decision 5 resolution):** Phase 3 was provisional.
It is now **confirmed in scope** — live probes reproduce both false positives, and
the fix is local to `_assigns_special_variable__all__` plus three thin
`visit_*` dispatch methods (no scope handling). See Phase 3 for the probe evidence.

**Tooling (Justfile, CLAUDE.md §5):**
- `just test` → `uv run pytest -n <cpus>`
- `just test <path>` → run a subset (e.g. `just test tests/noqa/test_noqa_comments.py`)
- `just check` → format-check, lint, complexity (C901, ≤10), mypy, then full test suite

---

## Phase 1: Fix `does_include` self-comparison in part merge

### Changes

#### 1. The defective expression
**File**: `deadcode/actions/merge_overlaping_file_parts.py`
**Action**: modify (one token, line 10)

Current:
```python
ends_faster = (line_end_b < line_end_s) or ((line_end_b == line_end_b) and (col_end_b <= col_end_s))
```
Change the always-`True` self-comparison `line_end_b == line_end_b` to compare
against the smaller part's end line:
```python
ends_faster = (line_end_b < line_end_s) or ((line_end_b == line_end_s) and (col_end_b <= col_end_s))
```
Signature of `does_include(bigger_part: Part, smaller_part: Part) -> bool` is
unchanged. Do not touch the Lithuanian comments or neighboring functions
(CLAUDE.md §3).

#### 2. Regression test
**File**: `tests/actions/test_merge_overlaping_file_parts.py`
**Action**: modify (add tests to the existing `TestMergeBranches` class, after
line 213)

Add a direct `does_include` assertion that pins the defect — the bigger part ends
on a *later* line than the smaller part (so it cannot contain it) yet has a
smaller end column, the exact shape the buggy clause mishandled:
```python
    def test_does_include_false_when_bigger_ends_on_a_later_line(self):
        # bigger ends on line 10, smaller on line 5: bigger cannot contain smaller,
        # even though bigger's end column (2) <= smaller's end column (6).
        # The buggy `line_end_b == line_end_b` made this wrongly return True.
        bigger = (1, 10, 0, 2, None, None)
        smaller = (1, 5, 0, 6, None, None)
        assert does_include(bigger, smaller) is False

    def test_does_include_true_for_genuine_same_line_containment(self):
        # Same end line, bigger's end column >= smaller's: genuine containment.
        assert does_include((1, 1, 0, 6, None, None), (1, 1, 0, 2, None, None)) is True
```
`does_include` is already imported at the top of the file (line 5).

> **Implementation deviation**: The plan's second test had the arguments swapped.
> `does_include(bigger_part, smaller_part)` returns True when `bigger_part` is INSIDE
> `smaller_part` (confusingly, the "bigger" param is the contained/smaller span).
> With the fix, `does_include((1,1,0,6,...), (1,1,0,2,...))` returns False — col_end
> 6 > col_end 2 means the first arg does NOT end before the second. The corrected test
> swaps the arguments: `does_include((1,1,0,2,...), (1,1,0,6,...)) is True`, where
> the smaller column span (0-2) is correctly inside the larger (0-6).

### Verification
#### Automated
- [x] `just test tests/actions/test_merge_overlaping_file_parts.py` fails on
      `test_does_include_false_when_bigger_ends_on_a_later_line` **before** the
      line-10 edit (run it first to observe the failure).
- [x] `just test tests/actions/test_merge_overlaping_file_parts.py` passes
      **after** the edit.
- [x] `just test` passes (whole suite; confirms the fix does not regress existing
      merge tests — see manual note below).
- [x] `just check` passes (format, lint, complexity ≤10, mypy).

#### Manual
- [x] Confirm no existing merge test changed result, not just that the suite is
      green: `just test tests/actions/test_merge_overlaping_file_parts.py -v`
      shows `test_contained_part_is_dropped_during_merge`,
      `test_overlaping_parts_in_the_same_line`, and
      `test_merge_overlaping_file_parts_with_multiple_parts_on_the_same_line` all
      PASSED. (Analysis: in every existing case the buggy clause never fired
      because `starts_later` was already `False`, or the part is still removed via
      the merge path instead of the include path — so outputs are unchanged. If
      any of these fails, apply the Open-Risks rule: decide whether the test
      pinned the bug or is a real regression.)

---

## Phase 2: Align noqa matching with flake8 (whitespace + lowercase codes)

### Changes

#### 1. Widen the regex to flake8's `#\s*noqa`
**File**: `deadcode/visitor/noqa.py`
**Action**: modify (line 12)

Current:
```python
    r'# noqa(?::[\s]?(?P<codes>([A-Z]+[0-9]+(?:[,\s]+)?)+))?',
```
Replace the literal `# noqa` (exactly one space) with `#\s*noqa` so `#noqa`,
`#  noqa`, etc. all match. Keep `re.IGNORECASE` (line 13) and the code subpattern
`[A-Z]+[0-9]+` (it already matches lowercase under IGNORECASE):
```python
    r'#\s*noqa(?::[\s]?(?P<codes>([A-Z]+[0-9]+(?:[,\s]+)?)+))?',
```

#### 2. Normalize captured codes to uppercase before the map lookup
**File**: `deadcode/visitor/noqa.py`
**Action**: modify (`parse_noqa`, line 60)

`NOQA_CODE_MAP` (lines 16–46) has only uppercase keys, so an IGNORECASE-captured
`dc07`/`f401` currently misses. Upper-case the captured code before lookup.

Current (lines 59–61):
```python
            for error_code in _parse_error_codes(match.groupdict()):
                error_code = NOQA_CODE_MAP.get(error_code, error_code)
                noqa_lines[error_code].add(lineno)
```
Change line 60 to:
```python
                error_code = NOQA_CODE_MAP.get(error_code.upper(), error_code.upper())
```
This makes both the mapped result and the fallback uppercase (so the bare-code
fallback stores `DC07`, matching how reporting looks codes up). `parse_noqa`'s
signature `parse_noqa(code: str) -> dict[str, set[int]]` is unchanged. Leave the
`'all'` key path (`_parse_error_codes`, line 51) untouched — `'all'.upper()` is
`'ALL'` which would break `ignore_line`'s `noqa_lines['all']` check, so do **not**
upper-case inside `_parse_error_codes`; only upper-case the per-code value in
`parse_noqa` as shown (the `'all'` token never reaches that map lookup because it
is produced only when `codes` is empty, and `'ALL'` is not a map key — so guard:
the `.upper()` is applied to the matched DC/flake8 code, and `'all'` from the
no-code branch is `_parse_error_codes`'s literal which must stay lowercase).

> Implementation detail: `_parse_error_codes` returns `['all']` when no code is
> given. That value flows into the same loop. `'all'.upper()` → `'ALL'`, and
> `NOQA_CODE_MAP.get('ALL', 'ALL')` → `'ALL'`, which would **not** match
> `ignore_line`'s hardcoded `noqa_lines['all']`. To keep bare `# noqa` working,
> skip normalization for the `'all'` sentinel:
> ```python
>             for error_code in _parse_error_codes(match.groupdict()):
>                 if error_code != 'all':
>                     error_code = NOQA_CODE_MAP.get(error_code.upper(), error_code.upper())
>                 noqa_lines[error_code].add(lineno)
> ```
> Use this guarded form.

#### 3. Behavior tests
**File**: `tests/noqa/test_noqa_comments.py`
**Action**: modify (add tests to the existing `TestNoqaComments` class)

Add cases modeled on the existing `test_noqa_all` / `test_unused_variable` style
(subclass already in place, `main([...], '--no-color', '--fix')`, assert the name
is suppressed). Do **not** un-skip the DC05/06/08/09/13 `@skip`ped tests
(Decision 7).

```python
    def test_noqa_without_space_is_honored(self):
        self.files = {
            'foo.py': """
                unused_variable = "Hello"  #noqa
                """
        }
        unused_names = main(['foo.py', '--no-color', '--fix'])
        self.assertEqual(unused_names, None)

    def test_noqa_with_extra_space_is_honored(self):
        self.files = {
            'foo.py': """
                unused_variable = "Hello"  #  noqa
                """
        }
        unused_names = main(['foo.py', '--no-color', '--fix'])
        self.assertEqual(unused_names, None)

    def test_noqa_lowercase_code_is_honored(self):
        self.files = {
            'foo.py': """
                import os  # noqa: dc07
                """
        }
        unused_names = main(['foo.py', '--no-color', '--fix'])
        self.assertEqual(unused_names, None)

    def test_type_ignore_comment_does_not_suppress(self):
        self.files = {
            'foo.py': """
                unused_variable = "Hello"  # type: ignore
                """
        }
        unused_names = main(['foo.py', '--no-color', '--fix'])
        self.assertEqual(
            unused_names,
            'foo.py:1:0: DC01 Variable `unused_variable` is never used\n\nRemoved 1 unused code item!',
        )
```

> The `# type: ignore` guard test pins the over-match risk (design Open Risks): a
> benign non-noqa comment must still be reported. The expected string mirrors the
> existing `test_unused_variable_but_wrong_noqa_specified` report format
> (`test_noqa_comments.py:88-91`). If the exact report string differs, capture it
> from a one-off `just test ... -v` run and use the observed value — the assertion
> intent is "the name is still reported (not None)".

### Verification
#### Automated
- [x] Before the regex/`.upper()` edits, `just test tests/noqa/test_noqa_comments.py`
      fails the three new positive cases (`#noqa`, `#  noqa`, `# noqa: dc07`) and
      passes the `# type: ignore` guard.
- [x] After the edits, `just test tests/noqa/test_noqa_comments.py` passes all
      four new cases and every previously-passing per-code/`all` case.
- [x] `just test` passes (whole suite).
- [x] `just check` passes.

#### Manual
- [x] `python -c "from deadcode.visitor.noqa import parse_noqa; d=parse_noqa('x=1  #noqa\n'); print(dict(d))"`
      → output contains `'all': {1}`.
- [x] `python -c "from deadcode.visitor.noqa import parse_noqa; d=parse_noqa('import os  # noqa: dc07\n'); print(dict(d))"`
      → output contains `'DC07': {1}` (lowercase code resolved to the DC code).
- [x] `python -c "from deadcode.visitor.noqa import parse_noqa; d=parse_noqa('x=1  # type: ignore\n'); print(dict(d))"`
      → output is `{}` (no suppression for `# type: ignore`).

---

## Phase 3: Recognize `__all__` AugAssign/AnnAssign

> **Scope confirmation (resolves Decision 5 / provisional status).** Live probes
> on the current code reproduce both false positives, and the fix is local:
> ```
> $ deadcode probe_aug.py   # def used_via_aug + __all__ += ['used_via_aug']
> probe_aug.py:1:0: DC02 Function `used_via_aug` is never used      # FALSE POSITIVE
> $ deadcode probe_ann.py   # def used_via_ann + __all__: list = ['used_via_ann']
> probe_ann.py:1:0: DC02 Function `used_via_ann` is never used      # FALSE POSITIVE
> ```
> No existing `visit_AugAssign` / `visit_AnnAssign` handlers exist (grep
> confirmed). The fix touches only `_assigns_special_variable__all__` and the
> `visit_Assign` dispatch group — no scope handling — so the phase stays in scope.

### Changes

#### 1. Broaden the `__all__` predicate to all three assignment node types
**File**: `deadcode/visitor/ignore.py`
**Action**: modify (`_assigns_special_variable__all__`, lines 66–70)

`ast.Assign` exposes `node.targets` (a list); `ast.AugAssign` and `ast.AnnAssign`
expose a single `node.target`. `ast.AnnAssign.value` is optional (`None` for a
bare `x: int`). Rewrite to handle all three and the `value is None` case:

Current:
```python
def _assigns_special_variable__all__(node: ast.Assign) -> bool:
    assert isinstance(node, ast.Assign)
    return isinstance(node.value, (ast.List, ast.Tuple)) and any(
        target.id == '__all__' for target in node.targets if isinstance(target, ast.Name)
    )
```
New:
```python
def _assigns_special_variable__all__(node: ast.Assign | ast.AugAssign | ast.AnnAssign) -> bool:
    assert isinstance(node, (ast.Assign, ast.AugAssign, ast.AnnAssign))
    if not isinstance(node.value, (ast.List, ast.Tuple)):
        return False
    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
    return any(target.id == '__all__' for target in targets if isinstance(target, ast.Name))
```
The `isinstance(node.value, ...)` guard returns `False` for `AnnAssign` with
`value is None` (its `.value` is `None`), covering the optional-value case.

#### 2. Dispatch AugAssign/AnnAssign through the same `__all__` handling
**File**: `deadcode/visitor/find_unused_code_visitor.py`
**Action**: modify (`visit_Assign`, lines 503–508)

Extract the element-marking into a small private helper and add the two new
`visit_*` methods that the custom dispatcher (`_dispatch_pre_visit`, line 540,
resolves `visit_<ClassName>` by `getattr`) will route to.

Current:
```python
    def visit_Assign(self, node: ast.Assign) -> None:
        if _assigns_special_variable__all__(node):
            assert isinstance(node.value, (ast.List, ast.Tuple))
            for elt in node.value.elts:
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                    self.add_used_name(elt.value)
```
New:
```python
    def _mark_all_exports_used(self, node: ast.Assign | ast.AugAssign | ast.AnnAssign) -> None:
        if _assigns_special_variable__all__(node):
            assert isinstance(node.value, (ast.List, ast.Tuple))
            for elt in node.value.elts:
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                    self.add_used_name(elt.value)

    def visit_Assign(self, node: ast.Assign) -> None:
        self._mark_all_exports_used(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        self._mark_all_exports_used(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        self._mark_all_exports_used(node)
```
No change to the import on line 31 (`_assigns_special_variable__all__` is already
imported). Child traversal is unaffected — `_visit_children` still runs for these
nodes independently of the `visit_*` pre-visit, so non-`__all__` AugAssign/AnnAssign
behavior is unchanged.

#### 3. Detection tests
**File**: `tests/visitor/test_find_unused_code_visitor.py`
**Action**: modify (add a new `BaseTestCase` subclass; `main` and `BaseTestCase`
are already imported at lines 5 and 7)

```python
class TestDunderAllAugAndAnnAssign(BaseTestCase):
    def test_name_exported_via_all_augassign_is_used(self):
        self.files = {
            'foo.py': """
                def used_via_all():
                    pass

                __all__ = []
                __all__ += ['used_via_all']
                """
        }
        unused_names = main(['foo.py', '--no-color'])
        self.assertEqual(unused_names, None)

    def test_name_exported_via_all_annassign_is_used(self):
        self.files = {
            'foo.py': """
                def used_via_all():
                    pass

                __all__: list[str] = ['used_via_all']
                """
        }
        unused_names = main(['foo.py', '--no-color'])
        self.assertEqual(unused_names, None)
```
(`__all__` itself is never reported — `_ignore_variable` ignores `__x__` special
names, `ignore.py:96-105`.)

### Verification
#### Automated
- [x] Before the edits,
      `just test tests/visitor/test_find_unused_code_visitor.py` fails both new
      tests (each reports `used_via_all` as `DC02`, so `unused_names` is a string,
      not `None`).
- [x] After the edits, both new tests pass.
- [x] `just test` passes (whole suite).
- [x] `just check` passes (verify mypy accepts the
      `ast.Assign | ast.AugAssign | ast.AnnAssign` union and the
      `[node.target]` branch).

#### Manual
- [x] Reproduce the resolved false positives end-to-end:
      ```
      printf 'def used_via_all():\n    pass\n\n__all__ = []\n__all__ += ["used_via_all"]\n' > /tmp/aug.py
      uv run deadcode /tmp/aug.py --no-color | grep -q 'used_via_all' && echo STILL_BUGGY || echo FIXED
      ```
      → prints `FIXED`.
- [x] ```
      printf 'def used_via_all():\n    pass\n\n__all__: list[str] = ["used_via_all"]\n' > /tmp/ann.py
      uv run deadcode /tmp/ann.py --no-color | grep -q 'used_via_all' && echo STILL_BUGGY || echo FIXED
      ```
      → prints `FIXED`.
- [x] Negative control (a genuinely unused name not in `__all__` is still
      reported): `printf 'def a():\n    pass\n\n__all__ = []\n__all__ += ["b"]\n' > /tmp/neg.py; uv run deadcode /tmp/neg.py --no-color | grep -q "DC02 Function \`a\`" && echo OK`
      → prints `OK`.

---

## Testing Checkpoints

After **Phase 1**: `just test` + `just check` green. `does_include` returns `True`
only for genuine line+column containment; the new direct unit assertions pin the
defect; existing merge tests unchanged.

After **Phase 2**: `just test` + `just check` green. `parse_noqa` recognizes
`#noqa`, `#  noqa`, and lowercase/legacy codes; `# type: ignore` is unaffected.

After **Phase 3**: `just test` + `just check` green. `__all__` augmented/annotated
assignments mark their string elements used; the two reproduced false positives
are gone.

Resume rule: each phase is self-contained and test-first. To resume after a
context reset, run `just test`; the first failing or missing assertion among the
three areas (merge → noqa → `__all__`) identifies the next phase.
</content>
</invoke>
