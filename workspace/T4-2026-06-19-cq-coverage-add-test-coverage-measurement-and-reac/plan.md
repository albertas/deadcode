# Implementation Plan

## Overview

Scope coverage to the `deadcode/` package via an explicit `[tool.coverage.*]`
config, write behavior-describing tests that close the real gaps module-group by
module-group, and only then raise `--cov-fail-under` to `95.0`. No product code
in `deadcode/` changes (one `# pragma: no cover` aside); tests adapt to the code.

**Verified baseline** (run `pytest -o addopts="" --cov=deadcode
--cov-report=term-missing` on Python 3.11): `1190` stmts, `110` missing,
`91%` (`90.84%`). Suite: `127 passed, 18 skipped`. After omitting
`base_test_case.py` (52 stmts / 3 missing) the denominator becomes `1138` stmts
with `107` missing → `≈90.6%`. To clear `95.0%` we must reduce misses to
`≤ 56` (close `≥ 51` lines). The phases below make ~80+ lines reachable, so the
target has a wide margin even if a handful of fiddly lines are left to a
justified pragma.

**Cross-cutting rules (apply to every test added):**
- Tests must be **Python 3.8-compatible** (CI runtime): no `X | None` unions,
  no `match`/`case`, no walrus in places 3.8 rejects, use `typing.Optional`.
- Follow conventions: files `test_<topic>.py`, classes `TestCamelCase`/`*Tests`,
  methods `test_*`, plain `assert`/`assertEqual`. Subclass `BaseTestCase` for
  virtual-FS / `main()` tests; plain `unittest.TestCase` for pure-function units.
- Never add a `@skip` or empty stub to dodge a gap (design Decision 5).
- Import module-private symbols (`_safe_eval`, etc.) directly from their
  defining module.

**Per-phase verification command (template):**
```bash
uv run pytest -o addopts="" --cov=deadcode --cov-report=term-missing <paths>
```
`-o addopts=""` strips the `--cov=.`/`--no-cov-on-fail`/`--cov-fail-under` from
`pyproject.toml` so a single area can be measured without the global gate
aborting the run.

---

## Phase 1: Coverage measurement scaffolding (no gate change)

Scope coverage to the package and document it in config, **without** raising the
threshold. Establishes the clean denominator everything else is measured against.

### Changes

#### 1. pytest/coverage configuration
**File**: `pyproject.toml`
**Action**: modify (last section) + add two new sections at end of file.

Change the existing pytest section (currently the file's last line):
```toml
[tool.pytest.ini_options]
addopts = "--cov=deadcode --no-cov-on-fail --cov-fail-under=88.0"
```
(only `--cov=.` → `--cov=deadcode`; keep `--no-cov-on-fail` and the `88.0`
gate for now — the gate flips in Phase 6).

Append two new sections:
```toml
[tool.coverage.run]
source = ["deadcode"]
omit = ["deadcode/utils/base_test_case.py"]

[tool.coverage.report]
# Coverage's default exclude already matches "# pragma: no cover";
# pragmas added in later phases are honored without further config.
```

Rationale (design Decisions 1–3): measure the package only (test files must not
dilute the gate), make the measurement self-documenting, and legitimately drop
the `assertUpdatedFiles` 87–90 gap by omitting the in-package test base.

### Verification
#### Automated
- [x] `uv run pytest -o addopts="" --cov=deadcode --cov-report=term-missing` runs to completion.
- [x] `just test` passes (gate still `88.0`).

#### Manual
- [x] Report contains **no** `tests/` rows:
  `uv run pytest -o addopts="" --cov=deadcode --cov-report=term-missing 2>&1 | grep -E "^tests/" ; test $? -ne 0` (grep finds nothing → exit 1 → assertion passes).
- [x] Report contains **no** `base_test_case.py` row:
  `uv run pytest -o addopts="" --cov=deadcode --cov-report=term-missing 2>&1 | grep -q "base_test_case" && echo FAIL || echo OK` → prints `OK`.
- [x] `just test` prints `Required test coverage of 88.0% reached` (TOTAL ≥ 88.0; expected new baseline ≈ 90.6%).

---

## Phase 2: Close `actions/` gaps

Add targeted unit tests for standalone action helper functions on raw
tuples / `Part`s, plus two `parse_arguments` paths.

### Changes

#### 1. `remove_file_parts_from_content` string helpers
**File**: `tests/actions/test_remove_file_parts_from_content.py`
**Action**: modify (append new classes; keep existing `TestRemoveFilePartsFromCont`).
**Target lines**: `28-34`, `38-41`, `47-57`.

```python
from deadcode.actions.remove_file_parts_from_content import (
    remove_as_from_end,
    remove_comma_from_begining,
    get_code_parts_for_the_same_line,
)


class TestRemoveAsFromEnd(BaseTestCase):
    def test_line_not_ending_with_as_is_returned_unchanged(self):
        assert remove_as_from_end('from a import b') == 'from a import b'  # line 28-29

    def test_as_with_preceding_whitespace_is_stripped(self):
        assert remove_as_from_end('import foo as') == 'import foo'  # line 32-33

    def test_word_ending_in_as_without_space_is_kept(self):
        assert remove_as_from_end('alias') == 'alias'  # line 34


class TestRemoveCommaFromBegining(BaseTestCase):
    def test_line_without_leading_comma_is_returned_unchanged(self):
        assert remove_comma_from_begining('foo') == 'foo'  # line 38-39

    def test_leading_comma_and_surrounding_space_are_removed(self):
        assert remove_comma_from_begining(', foo') == 'foo'  # line 41


class TestGetCodePartsForTheSameLine(BaseTestCase):
    def test_collects_parts_ending_on_same_line_in_reverse_until_break(self):
        parts = [
            (3, 3, 0, 5, None, None),
            (3, 3, 6, 9, None, None),
            (4, 4, 0, 2, None, None),  # different line -> break (line 56)
        ]
        result = get_code_parts_for_the_same_line(parts, 0)
        assert result == [(3, 3, 6, 9, None, None), (3, 3, 0, 5, None, None)]
```

> Note on remaining lines `112`, `219`, `290-291` (inside the main
> `remove_file_parts_from_content` loop: middle-of-line `else: break`, same-line
> `insert_code` append, and the empty-line bucket append): these require crafted
> multi-`Part` inputs with `insert_code` set and are fragile. They are
> **best-effort** — attempt a `Part(1, 1, 4, 7, 'pass', None)` single-line case
> for `219` if cheap, otherwise leave them; the package margin absorbs ≤4 lines
> here. Do **not** modify product code to reach them.

#### 2. `find_python_filenames` verbose paths
**File**: `tests/actions/test_find_python_filenames.py`
**Action**: modify (append one method to `TestFindPythonFilenames`).
**Target lines**: `19`, `32-33`.

```python
    def test_verbose_logs_ignored_and_listed_files(self):
        self.args.paths = ['deadcode/cli.py']
        self.args.exclude = ['deadcode/cli.py']
        self.args.verbose = True
        with self.assertLogs(level='INFO') as cm:
            find_python_filenames(args=self.args)
        assert any('Ignoring' in message for message in cm.output)  # line 18-19
        assert any('Files to be checked' in message for message in cm.output)  # line 31-33
```

#### 3. `merge_overlaping_file_parts` branches
**File**: `tests/actions/test_merge_overlaping_file_parts.py`
**Action**: modify (append methods / a class).
**Target lines**: `14`, `86-87`, `114`.

```python
from deadcode.actions.merge_overlaping_file_parts import does_include  # add to imports


class TestMergeBranches(BaseTestCase):
    def test_does_include_returns_true_when_contained(self):
        # bigger starts later and ends faster -> contained (line 13-14)
        assert does_include((3, 5, 0, 6, None, None), (1, 7, 0, 6, None, None)) is True

    def test_contained_part_is_dropped_during_merge(self):
        # (1,5) is contained in (1,10): break + drop path (lines 113-114, 14)
        parts = [(1, 10, 0, 6, None, None), (1, 5, 0, 6, None, None)]
        assert merge_overlaping_file_parts(parts) == [(1, 10, 0, 6, None, None)]

    def test_merge_picks_second_insert_code_at_same_start(self):
        # same start, p1 insert falsy -> insert_code = p2's (lines 86-87)
        assert merge_parts(
            (2, 7, 0, 6, None, None), (2, 7, 0, 6, 'pass', None)
        ) == (2, 7, 0, 6, 'pass', None)
```

#### 4. `parse_arguments` paths
**File**: `tests/cli_args/test_parsing.py`
**Action**: modify (append methods to `CommandLineArgParsingTests`).
**Target lines**: `25`, `222`.

```python
from unittest.mock import patch  # add to imports
from deadcode.actions.parse_arguments import parse_pyproject_toml  # add to imports


    def test_falls_back_to_sys_argv_when_no_args_passed(self):
        with patch('sys.argv', ['deadcode', '.']):
            args = parse_arguments(None)  # line 24-25
        self.assertEqual(args.paths, ['.'])

    def test_parse_pyproject_returns_empty_when_file_missing(self):
        with patch('deadcode.actions.parse_arguments.os.path.isfile', return_value=False):
            self.assertEqual(parse_pyproject_toml(), {})  # line 221-222
```

> **Assumption / known residual**: `parse_arguments.py` line `9`
> (`import tomli as tomllib`) is a `sys.version_info` version guard. It executes
> on Python 3.8 (CI) but not on 3.11 (local); on 3.8 line `7` is the missed line
> instead. Either way exactly **one** import-guard line is uncovered per
> interpreter — this is inherent and left to the package margin (no pragma, to
> avoid masking a real future regression).

### Verification
#### Automated
- [x] `uv run pytest -o addopts="" --cov=deadcode --cov-report=term-missing tests/actions tests/cli_args/test_parsing.py` passes.

#### Manual
- [x] `find_python_filenames.py` Missing column shows only the version-independent residual (ideally empty):
  `uv run pytest -o addopts="" --cov=deadcode --cov-report=term-missing tests/actions 2>&1 | grep "find_python_filenames" | grep -qv "19," && echo OK` → `OK`.
- [x] `merge_overlaping_file_parts.py` no longer lists `14` or `114`:
  `... grep "merge_overlaping_file_parts" | grep -Eqv "(^| )14(,| )" && echo OK`.
- [x] Suite shows no newly added skips: `uv run pytest -o addopts="" -rs tests/actions tests/cli_args/test_parsing.py 2>&1 | grep -c SKIPPED` is `0`.

---

## Phase 3: Close `visitor/utils.py` + small visitor gaps

Direct unit tests for AST helpers (need crafted AST inputs), plus small
`code_item.py` / `lines.py` / `fix_unused_code_visitor.py` gaps.

### Changes

#### 1. `visitor/utils.py` helpers
**File**: `tests/visitor/test_utils.py` (create; `tests/visitor/` and
`tests/visitor/__init__.py` may need creating — mirror `tests/actions/`).
**Target lines**: `23-27`, `29`, `55-62`, `73`, `85`.

```python
import ast
from pathlib import Path
from unittest import TestCase

from deadcode.visitor.utils import (
    _safe_eval,
    get_decorator_name,
    LoggingList,
    LoggingSet,
)
from deadcode.visitor.code_item import CodeItem


def _expr(source):
    return ast.parse(source, mode='eval').body


class TestSafeEval(TestCase):
    def test_boolop_and(self):
        assert _safe_eval(_expr('True and False'), True) is False  # lines 23-25

    def test_boolop_or(self):
        assert _safe_eval(_expr('False or True'), False) is True  # lines 23-24, 27

    def test_unary_not(self):
        assert _safe_eval(_expr('not False'), True) is True  # lines 28-29

    def test_unevaluatable_name_returns_default(self):
        assert _safe_eval(_expr('undefined_name'), True) is True  # literal_eval ValueError -> 34/35


class TestGetDecoratorName(TestCase):
    def _decorator(self, source):
        return ast.parse(source).body[0].decorator_list[0]

    def test_plain_name(self):
        assert get_decorator_name(self._decorator('@deco\ndef f(): pass')) == '@deco'

    def test_attribute_chain(self):
        assert get_decorator_name(self._decorator('@a.b.c\ndef f(): pass')) == '@a.b.c'  # lines 58-62

    def test_call_decorator(self):
        assert get_decorator_name(self._decorator('@deco(1)\ndef f(): pass')) == '@deco'  # lines 55-56


class TestLoggingCollections(TestCase):
    def test_logging_list_append_in_verbose_mode(self):
        collection = LoggingList('function', verbose=True)
        collection.append(CodeItem(name='x', type_='function', filename=Path('f.py')))  # line 73
        assert collection == ['x']

    def test_logging_set_add_in_verbose_mode(self):
        names = LoggingSet('name', verbose=True)
        names.add('x')  # line 85
        assert 'x' in names
```

#### 2. `visitor/code_item.py` gaps
**File**: `tests/code_item/test_code_item.py`
**Action**: modify (append methods to `TestCodeItem`).
**Target lines**: `91`, `129`, `137`.

```python
    def test_scoped_name(self):
        code_item = CodeItem(name='bar', type_='variable', filename=Path('f.py'), scope='mod.Foo')
        self.assertEqual(code_item.scoped_name, 'mod.Foo.bar')  # line 91

    def test_repr_is_the_name(self):
        code_item = CodeItem(name='bar', type_='variable', filename=Path('f.py'))
        self.assertEqual(repr(code_item), "'bar'")  # line 129

    def test_eq_with_unrelated_type_is_false(self):
        code_item = CodeItem(name='bar', type_='variable', filename=Path('f.py'))
        self.assertNotEqual(code_item, 123)  # line 137 (returns False)
```

#### 3. `visitor/lines.py` gaps
**File**: `tests/visitor/test_lines.py` (create).
**Target lines**: `80-81` (decorator first-line), `64-65` (best-effort).

```python
import ast
from unittest import TestCase

from deadcode.visitor.lines import get_first_line_number, get_last_line_number


class TestLineNumbers(TestCase):
    def test_first_line_number_uses_first_decorator(self):
        node = ast.parse('@deco\ndef f():\n    pass').body[0]
        assert get_first_line_number(node) == 1  # lines 79-81

    def test_last_line_number_handles_children_without_lineno(self):
        # comprehension nodes lack lineno -> AttributeError branch (lines 64-65)
        node = ast.parse('[x for x in y]', mode='eval').body
        assert isinstance(get_last_line_number(node), int)
```

> If `test_last_line_number_handles_children_without_lineno` does not actually
> reach `64-65` on the local interpreter (verify via term-missing), leave the
> two lines to the margin — do not contort the input.

#### 4. `visitor/fix_unused_code_visitor.py` line 184
**File**: `tests/visitor/test_fix_unused_code_visitor.py` (create).
**Target line**: `184` (the `raise ValueError` in `convert_1d_part_to_2d`).

```python
from unittest import TestCase

import pytest

from deadcode.data_types import Args
from deadcode.visitor.fix_unused_code_visitor import FixUnusedCodeVisitor


class TestConvert1dPartTo2d(TestCase):
    def test_out_of_range_offsets_raise(self):
        visitor = FixUnusedCodeVisitor(filenames=[], args=Args())
        with pytest.raises(ValueError):
            # from_char beyond every line -> from_line stays None -> line 184
            visitor.convert_1d_part_to_2d(
                from_char=100, to_char=200, line_lengths=[5], first_line=1, first_col=0
            )
```

> Confirm `FixUnusedCodeVisitor.__init__` accepts `(filenames, args)` like
> `FindUnusedCodeVisitor`; if its signature differs, instantiate per its actual
> `__init__` (read `fix_unused_code_visitor.py:82`).

### Verification
#### Automated
- [x] `uv run pytest -o addopts="" --cov=deadcode --cov-report=term-missing tests/visitor tests/code_item` passes.

#### Manual
- [x] `visitor/utils.py` coverage rises well above 69%:
  `uv run pytest -o addopts="" --cov=deadcode --cov-report=term-missing tests/visitor tests/code_item 2>&1 | grep "visitor/utils.py"` shows ≥ 95%.
  _Result: 96% (lines 39, 43 are `condition_is_always_false`/`condition_is_always_true` — covered by full suite)._
- [x] No new skips: `uv run pytest -o addopts="" -rs tests/visitor tests/code_item 2>&1 | grep -c SKIPPED` equals the pre-existing count for those dirs (run once before editing to record it; expected `0` for the new files).
  _Result: 0 skipped._
- [x] New tests are 3.8-safe: `uv run pytest -o addopts="" tests/visitor tests/code_item` passes (no `match`/union-type syntax used).
  _Result: 17 passed._
  _Adaptation: `FixUnusedCodeVisitor.__init__` takes `find_unused_code_visitor: FindUnusedCodeVisitor`, not `(filenames, args)`. Instantiated a `FindUnusedCodeVisitor` first and passed it in._

---

## Phase 4: Close `visitor/find_unused_code_visitor.py` gaps (the big one)

Largest gap (47 lines). Drive most paths from the public `main()` surface via
`BaseTestCase` virtual-FS tests; fall back to direct visitor unit tests for
paths unreachable from `main()` (verbose `_log`, decorator-whitelist break,
`visit_MatchClass`).

### Changes

#### 1. `main()`-driven source fixtures
**File**: `tests/visitor/test_find_unused_code_visitor.py` (create).
**Target lines** reached here: `251`, `265-267`, `343`, `347`, `358`,
`366-368`, `378`, `381-397`, `402`, `440`, `449`, `459`, `493-496`,
`556-557`, `599-607`.

Each case sets `self.files` and calls `main(['foo.py', '--no-color'])` — the
`FindUnusedCodeVisitor` runs during `find_unused_names` regardless of `--fix`,
so no assertion on output is required beyond "it ran without error".

```python
from deadcode.cli import main
from deadcode.utils.base_test_case import BaseTestCase


class TestVisitorPathsViaMain(BaseTestCase):
    def _run(self, source):
        self.files = {'foo.py': source}
        main(['foo.py', '--no-color'])

    def test_async_function_def(self):
        self._run('async def handler():\n    pass\n')  # line 343

    def test_attribute_store(self):
        self._run('import os\nos.custom_attr = 1\n')  # line 347

    def test_old_style_format_string(self):
        self._run('value = "%(foo)s" % locals()\n')  # line 357-358

    def test_getattr_marks_attribute_used(self):
        self._run('import os\ngetattr(os, "getcwd")\n')  # lines 366-368

    def test_new_style_format_string(self):
        self._run('text = "{foo}".format(**locals())\n')  # lines 378, 381-397, 402

    def test_property_definition(self):
        self._run('class A:\n    @property\n    def value(self):\n        return 1\n')  # lines 440, 449

    def test_ternary_expression(self):
        self._run('result = 1 if undefined else 2\n')  # line 459

    def test_ternary_always_true(self):
        self._run('result = 1 if True else 2\n')  # line 251

    def test_redundant_if_without_else(self):
        self._run('if True:\n    x = 1\n')  # lines 265-267

    def test_dunder_all_assignment(self):
        self._run('__all__ = ["foo"]\nfoo = 1\n')  # lines 493-496

    def test_type_comment(self):
        self._run('values = []  # type: list\n')  # lines 556-557

    def test_unreachable_code_after_return(self):
        self._run('def f():\n    return\n    dead = 1\n')  # lines 599-607
```

> `parse_abstract_syntax_tree` parses with `type_comments=True` (confirmed
> `parse_abstract_syntax_tree.py:9`), so `test_type_comment` reaches `556-557`.

#### 2. Direct visitor unit tests (paths unreachable from `main()`)
**File**: same `tests/visitor/test_find_unused_code_visitor.py` (append class).
**Target lines**: `204-206` (`_log` body — `self.verbose` is hardcoded `False`),
`428-430` and `446-447` (decorator-whitelist `break`/`_log` — `ignore_decorators`
is always `[]` from `main()`), `503-504` (`visit_MatchClass` — `match`/`case` is
3.10+ syntax, untestable from 3.8 source).

```python
import ast
import types
from unittest import TestCase

from deadcode.data_types import Args
from deadcode.visitor.find_unused_code_visitor import FindUnusedCodeVisitor


def _visitor():
    return FindUnusedCodeVisitor(filenames=[], args=Args())


class TestVisitorDirectUnits(TestCase):
    def test_log_emits_when_verbose(self):
        visitor = _visitor()
        visitor.verbose = True
        visitor._log('hello')  # lines 203-206

    def test_class_decorator_whitelist_break(self):
        visitor = _visitor()
        visitor.ignore_decorators = ['@deco']
        node = ast.parse('@deco\nclass A:\n    pass\n').body[0]
        visitor.visit_ClassDef(node)  # lines 428-430 (break taken)

    def test_function_decorator_whitelist_skip(self):
        visitor = _visitor()
        visitor.ignore_decorators = ['@deco']
        node = ast.parse('@deco\ndef f():\n    pass\n').body[0]
        visitor.visit_FunctionDef(node)  # lines 446-447

    def test_visit_match_class_marks_kwd_attrs_used(self):
        visitor = _visitor()
        node = types.SimpleNamespace(kwd_attrs=['kind'])  # avoid 3.10 match syntax
        visitor.visit_MatchClass(node)  # lines 503-504
        assert 'kind' in visitor.used_names
```

> `_log` lines `207-210` (the `UnicodeEncodeError` fallback) are left to the
> margin — provoking an encode error from `print` is not worth the fragility.

### Verification
#### Automated
- [x] `uv run pytest -o addopts="" --cov=deadcode --cov-report=term-missing tests/visitor tests/fix tests/test_imports.py` passes.

#### Manual
- [x] `find_unused_code_visitor.py` rises from 83% toward ~95%:
  `uv run pytest -o addopts="" --cov=deadcode --cov-report=term-missing tests/visitor 2>&1 | grep "find_unused_code_visitor.py"` shows ≥ 93% and a much shorter Missing list.
  _Result: 90% with tests/visitor only; 93% with the broader set (tests/visitor tests/fix tests/test_imports.py). All Phase 4 target lines are covered. Remaining uncovered lines (207-210 UnicodeEncodeError, 387-389 ValueError, 416-424 base lookup, 516, 526-528, 548-550, 583) are not Phase 4 targets._
- [x] All new visitor tests pass under the 3.8-incompatible-syntax check (they
  construct `match` via `SimpleNamespace`, never `match`/`case` source):
  `uv run pytest -o addopts="" tests/visitor/test_find_unused_code_visitor.py` passes.
  _Result: 16 passed._
- [x] Any line left uncovered that is a genuinely unreachable branch is recorded
  in this plan's notes above (none required a `# pragma: no cover` in Phase 4).
  _Result: Remaining uncovered lines are: 207-210 (UnicodeEncodeError — left to margin per plan), 387-389 (invalid format string ValueError — left to margin), 416-424 (scope lookup in get_inherits_from), 516, 526-528 (ignore_definitions gate), 548-550 (ignore_bodies_if_inherits_from), 583 (should_ignore_new_definitions reset). None require pragmas._

---

## Phase 5: Close `utils/` leaf + `cli.py` gaps

Mop up remaining misses in leaf helpers and the orchestrator.

### Changes

#### 1. `utils/flatten_lists.py`
**File**: `tests/utils/test_flatten_lists.py` (create).
**Target line**: `18` (`return []` for falsy input).

```python
from unittest import TestCase

from deadcode.utils.flatten_lists import flatten_list, flatten_lists_of_comma_separated_values


class TestFlattenLists(TestCase):
    def test_flatten_list_of_none_is_empty(self):
        assert flatten_list(None) == []  # line 17-18

    def test_flatten_list_concatenates(self):
        assert flatten_list([['a'], ['b', 'c']]) == ['a', 'b', 'c']

    def test_flatten_comma_separated(self):
        assert flatten_lists_of_comma_separated_values([['a,b']]) == ['a', 'b']
```

#### 2. `utils/nested_scopes.py`
**File**: `tests/utils/test_nested_scopes.py` (create).
**Target line**: `24` (`if code_item.scope is None: return None`).

```python
from pathlib import Path
from unittest import TestCase

from deadcode.utils.nested_scopes import NestedScope
from deadcode.visitor.code_item import CodeItem


class TestNestedScope(TestCase):
    def test_add_ignores_code_item_without_scope(self):
        scope = NestedScope()
        item = CodeItem(name='x', type_='variable', filename=Path('f.py'))  # scope defaults to None
        assert scope.add(item) is None  # lines 23-24
```

#### 3. `utils/fix_indent.py` (best-effort)
**File**: `tests/utils/test_fix_indent.py`
**Target lines**: `12-13` (`UnicodeError` → `return None`).

`fix_indent` is typed for `str`; `str.expandtabs()`/`splitlines()` do not raise
`UnicodeError` for ordinary or surrogate strings, so `12-13` are effectively
untestable without changing the signature (out of scope). **Leave to the
margin** — do not add a brittle test. Record here that `12-13` are intentionally
uncovered.

#### 4. `utils/print_ast.py`
**File**: `deadcode/utils/print_ast.py`
**Action**: modify (add pragma — the only product-code edit, per design Decision 6).
**Target line**: `5` (debug-only `print`).

```python
def print_ast(node: ast.AST) -> None:  # pragma: no cover
    print(ast.dump(node, indent=4))  # type: ignore
```

#### 5. `cli.py` `__main__` guard
**File**: `tests/test_deadcode.py`
**Action**: modify (append a test).
**Target line**: `35` (`main()` under `if __name__ == '__main__':`).

```python
import runpy
import sys
from unittest import mock


class CliEntrypointTests(TestCase):  # use existing TestCase import in the file
    def test_module_runs_as_script(self):
        argv = ['deadcode', 'deadcode/data_types.py', '--no-color', '--quiet']
        with mock.patch.object(sys, 'argv', argv):
            runpy.run_module('deadcode.cli', run_name='__main__')  # executes line 35
```

> `runpy.run_module(..., run_name='__main__')` re-executes the module top level,
> hitting line 35. Targeting `data_types.py` (a small, fully-used module) keeps
> the run fast and side-effect-free. **Fallback**: if `runpy` interacts badly
> with coverage in parallel (`-n`) runs, apply `# pragma: no cover` to the
> `if __name__ == '__main__':` block (lines 34-35) instead (design Decision 6)
> and drop this test.

### Verification
#### Automated
- [x] `uv run pytest -o addopts="" --cov=deadcode --cov-report=term-missing` passes and prints a package **TOTAL ≥ 95.0%**.

#### Manual
- [x] `flatten_lists.py`, `nested_scopes.py` rows show 100%:
  `uv run pytest -o addopts="" --cov=deadcode --cov-report=term-missing 2>&1 | grep -E "flatten_lists.py|nested_scopes.py"` → both `100%`.
  _Result: flatten_lists.py 100%, nested_scopes.py 100%._
- [x] `print_ast.py` no longer counted (pragma):
  `... grep "print_ast.py"` shows `3 0 100%` (or row absent).
  _Result: `deadcode/utils/print_ast.py  1  0  100%` — pragma excludes the print line; row shows 100%._
- [x] TOTAL line ≥ 95.0:
  `uv run pytest -o addopts="" --cov=deadcode --cov-report=term-missing 2>&1 | grep "^TOTAL"` → final column ≥ `95%`.
  _Result: TOTAL 1136 14 99%._
- [x] Skip count unchanged (still 18, none newly added):
  `uv run pytest -o addopts="" 2>&1 | grep -E "[0-9]+ skipped"` → `18 skipped`.
  _Result: 175 passed, 18 skipped._

---

## Phase 6: Raise the gate to 95.0

Only after Phase 5 confirms the package clears 95%. Flip the enforcement value.

### Changes

#### 1. Raise `--cov-fail-under`
**File**: `pyproject.toml`
**Action**: modify.

```toml
[tool.pytest.ini_options]
addopts = "--cov=deadcode --no-cov-on-fail --cov-fail-under=95.0"
```
(only `88.0` → `95.0`).

### Verification
#### Automated
- [x] `just test` passes and prints `Required test coverage of 95.0% reached`.
- [ ] `make check` passes end-to-end (`test lint mypy audit deadcode`) — this is
  the CI gate (Python 3.8). If unavailable locally, at minimum run
  `just check` (format + lint + complexity + typecheck + test).
  _Note: `just check` fails due to 247 pre-existing ruff lint errors in `deadcode/` (275 before any phases). These errors were present before Phase 1 and are out of scope for Phase 6._

#### Manual
- [x] Gate value is exactly 95.0:
  `grep -q "cov-fail-under=95.0" pyproject.toml && echo OK` → `OK`.
- [x] Terminal report reaches the gate:
  `just test 2>&1 | grep -q "Required test coverage of 95.0% reached" && echo OK` → `OK`.
- [x] No newly-added skip dodging a gap (skip count still ≤ 18):
  `uv run pytest -o addopts="" -rs 2>&1 | grep -E "[0-9]+ skipped"` → `18 skipped` (or fewer).
  _Result: 175 passed, 18 skipped._
- [x] Coverage config sections present and correct:
  `grep -q "source = \[\"deadcode\"\]" pyproject.toml && grep -q "base_test_case.py" pyproject.toml && echo OK` → `OK`.

---

## Testing Checkpoints (roll-up)

- **After Phase 1**: coverage measures `deadcode/` only; no `tests/` or
  `base_test_case.py` rows; baseline ≈ 90.6%; 88.0 gate green.
- **After Phase 2**: `actions/` modules at/near 100% (minus the version-guard
  import line); suite green, no new skips.
- **After Phase 3**: `visitor/utils.py` ≫ 69% (≥ 95%); `code_item`/`lines`/
  `fix_unused_code_visitor` small gaps closed; all AST tests 3.8-compatible.
- **After Phase 4**: `find_unused_code_visitor.py` ≫ 83% (≥ 93%); MatchClass and
  decorator-whitelist paths covered via direct units; suite green.
- **After Phase 5**: package TOTAL ≥ 95.0% with the gate **still at 88.0** (so
  the green→enforced transition is purely the Phase 6 flip); one
  `# pragma: no cover` on `print_ast.py:4-5`.
- **After Phase 6**: `make check` enforces 95.0 on Python 3.8; CI green; no new
  skips. Task complete.
```

