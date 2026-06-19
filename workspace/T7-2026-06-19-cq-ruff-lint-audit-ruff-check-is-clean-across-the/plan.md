# Implementation Plan

## Overview

Drive `ruff check deadcode/ tests/` from **249 errors + non-error warnings** to a
**fully silent (error- and warning-free) exit**, then trim the now-dead `ignore`
entries so most rules are actively enforced. Fixes are applied rule-family by
rule-family (autofix-first, then manual one-offs), with no behavior changes, no
`--unsafe-fixes`, and no refactoring beyond the lines ruff flags.

## Verification primitives (used every phase)

- `uv run ruff check deadcode/ tests/ --statistics` — per-rule remaining counts.
- `uv run ruff check deadcode/ tests/ --select <CODE> --output-format concise` —
  exact remaining sites for one rule (`--select` re-enables a code regardless of
  the `ignore` list, exactly as `just check-complexity` re-enables `C901`).
- `just test` — full pytest gate (`-n` xdist, `--cov-fail-under=95.0`); catches a
  wrongly-removed symbol reachable via `getattr`/`visit_*` dispatch.
- `just check-typecheck` — mypy `strict`; confirms PEP 604/585 forms evaluate at
  import time (dataclass/`NamedTuple` bodies, `Literal` aliases).
- `just check` — full gate (`check-format check-lint check-complexity
  check-typecheck test`); run at the very end (Phase 6).

## Deviations from `structure.md` (resolved here)

These were discovered by running ruff live against the tree; each is resolved
below and called out at its phase:

1. **F841 split.** Only 1 of 4 F841 sites is in `deadcode/`
   (`fix_unused_code_visitor.py:439`). The other 3 are in `tests/`. → deadcode
   site stays in **Phase 3**; the 3 test sites move to **Phase 5**. Phase 3's
   F841 check is scoped to `deadcode/`.
2. **E501 split.** 13 of 14 E501 sites are in `deadcode/` (Phase 4); 1 is a long
   comment in `tests/fix/test_unused_imports_in_a_single_file.py` → moved to
   **Phase 5**.
3. **ANN201 added to Phase 4.** ANN201 (1 site,
   `remove_file_parts_from_content.py:61`) appears in the design's violation
   table but was omitted from the structure's Phase 4 heading. It is a real
   `deadcode/` error that must be fixed to reach zero. Added to Phase 4 (add a
   return-type annotation). It is already ignored for `tests/*` via
   `per-file-ignores`, so no test site is affected.
4. **F811 fix is an import removal.** `fix_unused_code_visitor.py:64`
   `from deadcode.visitor import lines` is never used as a module; the local
   variable `lines` at `:152` legitimately shadows it. Fix = delete the unused
   import (Phase 4).
5. **UP036 leaves `sys` in place.** After deleting the dead `sys.version_info`
   block in `parse_arguments.py`, `import sys` stays (still used at `:25`,
   `sys.argv`). No orphan import is created.

---

## Phase 1: Modernize type annotations (UP006 / UP007 / UP035 / UP045)

Converge the package's `typing.List/Dict/Optional/Union` forms onto builtin
generics + PEP 604 unions (already native in 5 spots). ~155 of the 249 errors.
Largest, lowest-risk batch; establishes the style the rest build on.

### Changes

#### 1. Apply the safe autofix for all four codes at once
**Files**: `deadcode/**/*.py`, `tests/**/*.py` (all annotation sites). Import
sites to be rewritten/trimmed include `constants.py:1`, `data_types.py:4`,
`cli.py:1`, `parse_arguments.py:2`, `merge_overlaping_file_parts.py:1`,
`remove_file_parts_from_content.py:2`, `visitor/noqa.py:3`,
`visitor/find_unused_code_visitor.py:13`,
`visitor/fix_unused_code_visitor.py:51`, plus `utils/*.py` and `actions/*.py`.
**Action**: modify (automated)

Run the four codes together so usage rewrites (UP006/UP007/UP045) and the
matching `from typing import …` cleanup (UP035) land in one pass:

```bash
uv run ruff check deadcode/ tests/ \
  --select UP006,UP007,UP035,UP045 --fix
```

Transformations: `List[X]`→`list[X]`, `Dict[K,V]`→`dict[K,V]`,
`Optional[X]`→`X | None`, `Union[A,B]`→`A | B`, and deprecated
`from typing import List, Dict, Optional, Union, …` lines trimmed/removed.

**Do not** add `from __future__ import annotations` anywhere (design §2). After
the fix, any typing name left imported-but-unused (e.g. a residual
`from typing import …`) is an F401 and is handled in Phase 2 — leave it.

#### 2. Review the autofix diff
**Action**: inspect

```bash
git diff --stat
git diff -- deadcode/constants.py deadcode/data_types.py
```

Confirm `constants.py` `Literal` aliases (`:4-33`) and `data_types.py`
`@dataclass Args` / `Part(NamedTuple)` bodies still read as valid annotations.

### Verification
#### Automated
- [x] `uv run ruff check deadcode/ tests/ --select UP006,UP007,UP035,UP045 --statistics` → all four at **0**.
- [ ] `just check-typecheck` passes (mypy strict; confirms import-time evaluation of new forms).
  - Note: mypy had 43 pre-existing errors before Phase 1; Phase 1 did not add any new errors (count unchanged at 43). The annotation changes (list/dict/set/tuple/X|None) evaluate fine at import time.
- [x] `just test` passes (`--cov-fail-under=95.0`).

#### Manual
- [x] `grep -rn "from __future__ import annotations" deadcode/ tests/` → no output (none added).
- [x] `grep -rn "Optional\[" deadcode/ tests/` → no output (only comment lines remain, not annotations).
- [x] `git diff` shows only annotation/import lines changed (no logic lines).

---

## Phase 2: Remaining safe autofixes (SIM905, F401, D403, PLR5501, RUF023)

Apply the rest of the safe-autofix codes. F401 (35, mostly the copied import
header in `fix_unused_code_visitor.py`) carries getattr/string-dispatch risk —
verified behaviorally, not by static reading (design §7).

### Changes

#### 1. Apply the safe autofix for the five codes
**Files**: `visitor/fix_unused_code_visitor.py`,
`visitor/find_unused_code_visitor.py`, `utils/nested_scopes.py`,
`visitor/code_item.py:44` (RUF023), `actions/remove_file_parts_from_content.py:286`
(PLR5501), `actions/remove_file_parts_from_content.py:62` (D403), plus SIM905
`.split('.')` sites.
**Action**: modify (automated)

```bash
uv run ruff check deadcode/ tests/ \
  --select SIM905,F401,D403,PLR5501,RUF023 --fix
```

Effects: unused imports removed (F401); `'a.b'.split('.')`→`['a', 'b']`
(SIM905); `else:`/`if` collapsed to `elif` at
`remove_file_parts_from_content.py:286` (PLR5501); `CodeItem.__slots__` sorted
at `code_item.py:44` (RUF023); first docstring word capitalized
`line`→`Line` at `remove_file_parts_from_content.py:62` (D403). The same
docstring also triggers D301, fixed manually in Phase 4.

The deliberate keeps must survive (ruff honors their `# noqa`):
`import print_ast as show  # noqa: F401`
(`find_unused_code_visitor.py:23`, `fix_unused_code_visitor.py:62`) and
`except:  # noqa: E722` (`parse_abstract_syntax_tree.py:10`).

Note: `from deadcode.visitor import lines` (`fix_unused_code_visitor.py:64`) is
**not** removed here — it is F811 (redefined by a local), handled in Phase 4.

### Verification
#### Automated
- [x] `uv run ruff check deadcode/ tests/ --select SIM905,F401,D403,PLR5501,RUF023 --statistics` → all five at **0**.
- [x] `just test` passes (catches any import removed that was reachable via `getattr`/`visit_*` dispatch).
- [ ] `just check-typecheck` passes.
  - Note: 43 pre-existing mypy errors (unchanged from Phase 1); Phase 2 introduced no new errors.

#### Manual
- [x] `grep -rc "noqa: F401" deadcode/visitor/find_unused_code_visitor.py deadcode/visitor/fix_unused_code_visitor.py` → each returns `1` (both `show` keeps survive).
- [x] `grep -n "noqa: E722" deadcode/actions/parse_abstract_syntax_tree.py` → still present.

---

## Phase 3: Manual unused-binding renames in `deadcode/` (RUF059, F841)

Prefix deliberately-unused unpack targets / locals with `_` per the established
convention (`merge_overlaping_file_parts.py:6-7` `_insert_condition_*`,
CLAUDE.md §6 throwaway caveat) rather than adding `# noqa`. None autofixable
(safe). RUF059 = 16 sites (all in `deadcode/`); F841 in `deadcode/` = 1 site
(the 3 test F841 sites are Phase 5 — see Deviation 1).

### Changes

#### 1. `actions/merge_overlaping_file_parts.py` — prefix flagged unpack vars
**File**: `deadcode/actions/merge_overlaping_file_parts.py`
**Action**: modify

Prefix each ruff-flagged unused unpack target with `_` (mirrors the existing
`_insert_condition_*`). The flagged names per line:

- `:6` `insert_code_b` → `_insert_code_b`
- `:7` `insert_code_s` → `_insert_code_s`
- `:21` `line_end_b`→`_line_end_b`, `col_end_b`→`_col_end_b`, `insert_code_b`→`_insert_code_b`
- `:22` `line_end_s`→`_line_end_s`, `col_end_s`→`_col_end_s`, `insert_code_s`→`_insert_code_s`
- `:34` `line_start_b`→`_line_start_b`, `col_start_b`→`_col_start_b`, `insert_code_b`→`_insert_code_b`
- `:35` `line_end_s`→`_line_end_s`, `col_end_s`→`_col_end_s`, `insert_code_s`→`_insert_code_s`

Leave the names that are read in the same function unchanged (e.g. `:21`
`line_start_b`/`col_start_b` are used at `:25`; `:34` `line_end_b`/`col_end_b`
are used at `:38`). Do not touch the pre-existing `line_end_b == line_end_b`
expression at `:11` (unrelated; CLAUDE.md §3).

#### 2. `actions/remove_file_parts_from_content.py:118` — prefix unpack vars
**File**: `deadcode/actions/remove_file_parts_from_content.py`
**Action**: modify

```python
# line 118 — only the last two targets are flagged; prefix them:
from_line, to_line, from_col, to_col, _insert_code, _insert_condition = first_code_part
```

(The identical unpacks at `:101`/`:108` are **not** flagged — their
`insert_condition` is read in the debug f-string at `:162` — leave them.)

#### 3. `visitor/fix_unused_code_visitor.py:439` — drop the dead local
**File**: `deadcode/visitor/fix_unused_code_visitor.py`
**Action**: modify

`node_name = getattr(node, 'name', None)` is assigned and never read.
`getattr` here has no side effects, so delete the line:

```python
    def visit(self, node: ast.AST) -> None:
        # (line `node_name = getattr(node, 'name', None)` removed)
```

### Verification
#### Automated
- [x] `uv run ruff check deadcode/ --select RUF059 --statistics` → **0**.
- [x] `uv run ruff check deadcode/ --select F841 --statistics` → **0** (deadcode only; tests handled in Phase 5).
- [x] `just test` passes.
- [ ] `just check-typecheck` passes.

#### Manual
- [x] `git diff -- deadcode/actions/merge_overlaping_file_parts.py deadcode/actions/remove_file_parts_from_content.py deadcode/visitor/fix_unused_code_visitor.py` shows only `_`-prefix renames and the one deleted `node_name` line — no logic changes.
  - Note: also includes annotation changes from Phases 1+2 in the same files; Phase 3 changes are only the `_`-prefix renames and deleted `node_name` line. The plan did not anticipate that fixing line 118 would cascade to reveal RUF059 at lines 101 and 108 too (ruff's cross-assignment tracking). Fixed all three sites.

---

## Phase 4: Manual real-issue one-offs in `deadcode/`

Fix each ≤1-site real issue rather than suppress, keeping every rule enforced
(design §4). Covers: EM101+TRY003, UP036, F811, PLR1704, SIM103, D301, ANN201
(Deviation 3), and the 13 `deadcode/` E501 sites.

### Changes

#### 1. `visitor/fix_unused_code_visitor.py:182` — EM101 + TRY003 (extract message)
**File**: `deadcode/visitor/fix_unused_code_visitor.py`
**Action**: modify

```python
        if from_line is None or from_col is None or to_line is None or to_col is None:
            message = 'Conversion from 1D to 2D code part failed'
            raise ValueError(message)
```

Assigning the literal to a local satisfies EM101 (no string literal in `raise`)
and TRY003 (no long message inline) together — the package's only `raise`.

#### 2. `visitor/fix_unused_code_visitor.py:64` — F811 (remove unused import)
**File**: `deadcode/visitor/fix_unused_code_visitor.py`
**Action**: modify (delete line)

Delete `from deadcode.visitor import lines`. The module is never referenced;
the local `lines` at `:152` (`lines = self.file_content_lines[...]`) shadows it
and is the only real use.

#### 3. `actions/parse_arguments.py:6-9` — UP036 (delete dead version block)
**File**: `deadcode/actions/parse_arguments.py`
**Action**: modify

Replace the `sys.version_info >= (3, 11)` branch (min Python is 3.11) with the
unconditional import:

```python
import argparse
from typing import Any
import sys
import os

import tomllib

from deadcode.data_types import Args
```

`import sys` stays (still used at `:25`, `sys.argv`). After this edit, re-run
ruff to catch any import-sorting (I001) or residual fallout introduced by the
change (see Phase 4 verification).

#### 4. `actions/fix_or_show_unused_code.py:34` — PLR1704 (rename shadowing loop var)
**File**: `deadcode/actions/fix_or_show_unused_code.py`
**Action**: modify

The loop variable `unused_items` shadows the function argument. Rename the loop
variable and its single use:

```python
    for filename, file_unused_items in filename_to_unused_items.items():
        file_parts = flatten_list([item.code_parts for item in file_unused_items])
```

(Only `:34` and `:35` reference it; nothing later in the loop uses
`unused_items`.)

#### 5. `actions/merge_overlaping_file_parts.py:13, :38` — SIM103 (return condition directly)
**File**: `deadcode/actions/merge_overlaping_file_parts.py`
**Action**: modify

```python
# does_include — replace the if/return True / return False (lines 13-15) with:
    return bool(starts_later and ends_faster)

# does_overlap — replace the if/return True / return False (lines 38-41) with:
    return bool((line_end_b > line_start_s) or ((line_end_b == line_start_s) and (col_end_b > col_start_s)))
```

Use `bool(...)` (matches ruff's suggested fix and preserves the `bool` return
contract). Preserve the operand expressions verbatim — do not "fix" the
pre-existing `line_end_b == line_end_b` typo at `:11`.

#### 6. `actions/remove_file_parts_from_content.py:61-62` — ANN201 + D301
**File**: `deadcode/actions/remove_file_parts_from_content.py`
**Action**: modify

Add the return-type annotation (function returns `return line, index_increment`
at `:124`, i.e. `(str, int)`) and make the docstring raw (it contains `\n`):

```python
def remove_unused_fragments_from_a_line(line: str, code_parts, index: int) -> tuple[str, int]:
    r"""
    Line = 'bar as bar_alias,\n'
    ...
```

`code_parts` stays unannotated (ANN001 is a deliberate policy ignore). The `r`
prefix resolves D301; the leading `Line` capitalization was already applied by
the Phase 2 D403 autofix.

#### 7. E501 — wrap the 13 `deadcode/` long lines
**Files**: `deadcode/actions/remove_file_parts_from_content.py` (`:162,199,232,237,300`),
`deadcode/visitor/find_unused_code_visitor.py` (`:116,119`),
`deadcode/visitor/fix_unused_code_visitor.py` (`:17,116,119,326,327,328`)
**Action**: modify

Wrap each line to ≤120 columns with no logic change (split long
comments/strings/expressions across lines; for f-strings and call arguments use
implicit continuation inside the existing parentheses). Confirm exact remaining
sites first:

```bash
uv run ruff check deadcode/ --select E501 --output-format concise
```

### Verification
#### Automated
- [x] `uv run ruff check deadcode/ --select EM101,TRY003,UP036,F811,PLR1704,SIM103,D301,ANN201,E501 --statistics` → all at **0**.
- [x] `just check-typecheck` passes (confirms `tuple[str, int]` and the `tomllib` import resolve).
  - Note: 42 pre-existing mypy errors (down from 43 — UP036 fix removed one tomli error); no new errors introduced.
- [x] `just test` passes.
- [x] `uv run ruff check deadcode/` reports no **new** codes surfaced by the edits (e.g. no I001 after the `parse_arguments.py` change). If one appears, fix that single site before continuing.

#### Manual
- [x] `grep -n "raise ValueError" deadcode/visitor/fix_unused_code_visitor.py` → the `raise` references `message`, not a literal.
- [x] `grep -n "from deadcode.visitor import lines" deadcode/visitor/fix_unused_code_visitor.py` → no output (import removed).
- [x] `grep -n "sys.version_info" deadcode/actions/parse_arguments.py` → no output.

---

## Phase 5: Test-suite fixes (PTH109, PT011, SLF001, + test F841 ×3, test E501 ×1)

Bring `tests/` to zero ruff errors. Prefer real fixes; add a `per-file-ignores`
entry only where a fix is awkward (design §5). Never touch fixture source
strings or assertions.

### Changes

#### 1. `tests/test_deadcode.py:15, :84` — PTH109 (`os.getcwd()` → `Path.cwd()`)
**File**: `tests/test_deadcode.py`
**Action**: modify

Replace `os.getcwd()` with `Path.cwd()` (cast to `str` if the surrounding code
compares against a string path — inspect each site). Add `from pathlib import
Path` if not already imported; if `os` becomes unused after both edits, remove
the `import os` (orphan from our change). Verify usages first:

```bash
uv run ruff check tests/test_deadcode.py --select PTH109 --output-format concise
```

#### 2. `tests/visitor/test_fix_unused_code_visitor.py:15` — PT011 (add `match=`)
**File**: `tests/visitor/test_fix_unused_code_visitor.py`
**Action**: modify

```python
with pytest.raises(ValueError, match='Conversion from 1D to 2D code part failed'):
```

(The message matches the `raise` reworded in Phase 4.4. Prefer this real fix
over a `per-file-ignores` entry, per design §5.)

#### 3. `tests/visitor/test_find_unused_code_visitor.py:61` — SLF001 (per-file ignore)
**File**: `pyproject.toml`
**Action**: modify

The test legitimately reads `visitor._log` (a private member). Rather than rename
the production attribute, add `SLF001` to the existing `tests/*` per-file-ignore
block (`pyproject.toml:155-160`):

```toml
[tool.ruff.lint.per-file-ignores]
"tests/*" = [
    "S101",  # allow assert and no docs in tests
    "PT009",
    "ANN201",
    "SLF001",  # tests legitimately read private members (e.g. visitor._log)
    "D",
]
```

#### 4. Test F841 ×3 — drop the unused bindings (keep the side-effecting call)
**Files**: `tests/fix/test_unused_imports_in_a_single_file.py` (`:183`, `:231`),
`tests/nested_scope/test_nested_scope.py` (`:39`)
**Action**: modify

Each is `<name> = main([...])` where the assignment is never read (the
asserting code below it is commented out) but `main(...)` performs the fix being
tested. Drop only the binding; keep the call:

```python
# test_unused_imports_in_a_single_file.py:183 and :231
main('file.py --no-color --fix -v'.split())

# test_nested_scope.py:39
main(['foo.py', '--no-color', '--fix'])
```

Do not touch the inline triple-quoted fixture source strings or `assertFiles`
arguments.

#### 5. Test E501 ×1 — wrap the long comment
**File**: `tests/fix/test_unused_imports_in_a_single_file.py:223`
**Action**: modify

Line 223 is a `# [Part(line_start=1, ...), Part(line_start=3, ...)]` comment
(124 cols). Split it across two `#` comment lines so each is ≤120 cols. It is a
comment, not a fixture string or assertion — safe to wrap.

### Verification
#### Automated
- [x] `uv run ruff check tests/ --statistics` → empty (zero errors in `tests/`).
- [x] `just test` passes.

#### Manual
- [x] `git diff --stat tests/noqa/` → empty (the intentionally-malformed `# noqa: DC02` fixture at `tests/noqa/test_noqa_comments.py:71` is byte-unchanged).
- [x] `grep -n "pytest.raises(ValueError, match=" tests/visitor/test_fix_unused_code_visitor.py` → present.
- [x] `grep -n "Path.cwd()" tests/test_deadcode.py` → 2 occurrences; `grep -n "os.getcwd()" tests/test_deadcode.py` → no output.

---

## Phase 6: Warning-free finish — reword `noqa.py`, trim `ignore`, full gate

Eliminate the remaining non-error warnings and trim dead `ignore` entries so the
run is fully silent and most rules enforced.

### Changes

#### 1. `visitor/noqa.py:9-12` — silence the "Invalid `# noqa` directive" warnings
**File**: `deadcode/visitor/noqa.py`
**Action**: modify (comment text only)

Ruff parses the literal `` `# noqa` `` text inside the example comments as real
directives and warns on lines 9-12. Reword so the backticked examples no longer
contain `# noqa` (drop the inner `#`):

```python
    # We're looking for items that look like this:
    # `noqa`
    # `noqa: E123`
    # `noqa: E123,W451,F921`
    # `NoQA: E123,W451,F921`
    r'# noqa(?::[\s]?(?P<codes>([A-Z]+[0-9]+(?:[,\s]+)?)+))?',
```

**Critical:** edit only the comment lines `:9-12`. The `NOQA_REGEXP` string at
`:13` and every `tests/noqa/` fixture stay **byte-identical** (design Open Risks).

#### 2. `pyproject.toml` — remove `ANN101` (removed rule)
**File**: `pyproject.toml`
**Action**: modify

Delete the `"ANN101",  # deprecated requirement to annotate self` line from the
`ignore` list (`:79`). It is a removed ruff rule and is the source of the
`rules have been removed` warning.

#### 3. `pyproject.toml` — trim every remaining dead `ignore` entry
**File**: `pyproject.toml`
**Action**: modify

Goal: remove each `ignore` entry whose rule currently has **zero** hits and is
not a deliberate project-policy ignore, so "most rules" become actively
enforced. Determine empirically — probe each candidate (`--select CODE`
re-enables it regardless of `ignore`):

```bash
for code in A001 ANN001 ANN002 ANN202 ANN204 ANN401 ARG001 ARG002 C411 C901 \
  D100 D101 D102 D103 D104 D105 D107 D200 D202 D203 D205 D209 D212 D213 D400 \
  D401 D404 D415 D419 ERA001 FA100 FBT001 FBT002 FBT003 FIX002 G004 I001 \
  INP001 N802 PD011 PGH003 PLE0101 PLR0124 PLR0133 PLR0912 PLR0913 PLR0915 \
  PLR2004 PLW2901 PT009 PTH107 PTH113 PTH119 PTH122 PTH123 RET501 RET504 \
  RET505 RET507 RUF012 RUF100 S101 SIM102 SIM105 SIM114 T201 TD002 TD003 \
  TD005 TRY300 UP004 UP015 W293 W605 COM812 ISC001; do
  n=$(uv run ruff check deadcode/ tests/ --select "$code" --output-format concise 2>/dev/null | grep -cE ': '"$code"' ')
  echo "$code $n"
done
```

Decision rule:
- **Keep** (do not remove from `ignore`), regardless of hit count, the
  deliberate-policy ignores per design §3: docstring opt-outs (`D1xx`/`D2xx`/`D4xx`
  including `D203`/`D213`), `T201`, `S101`, `FBT001`/`FBT002`/`FBT003`,
  `C901`/`PLR0912`/`PLR0913`/`PLR0915`/`PLR2004`/`PLR0124`/`PLR0133`, `G004`,
  `COM812`/`ISC001`, `RUF100`/`RUF012`, plus the standing policy set
  `ERA001` (commented-out code is pervasive), `FA100` (no `__future__` per
  design §2), `FIX002`/`TD002`/`TD003`/`TD005` (TODO style), `PT009` (unittest
  asserts), `N802`, `INP001`, the `PTH*` family, `ANN001`/`ANN002`/`ANN202`/
  `ANN204`/`ANN401`, `ARG001`/`ARG002`, `RET50x`, `SIM102`/`SIM105`/`SIM114`,
  `PGH003`, `PD011`, `PLE0101`, `PLW2901`, `W293`/`W605`, `A001`.
- **Remove** any *non-policy* entry whose probe printed `0` (e.g. `C411`,
  `UP004`, `UP015` if they probe 0). For any entry that probes `> 0`, keep it —
  removing it would surface errors (the "hidden ignore couplings" risk).

After editing, re-run `uv run ruff check deadcode/ tests/` and confirm the
output is still clean (no newly-surfaced violations). If an edit surfaces a
violation, restore that one `ignore` entry.

> Note: the violations fixed in Phases 1–5 were **not** in the `ignore` list
> (they were live errors), so trimming here is purely about removing
> now-meaningless zero-hit entries, not about un-masking fixed rules. The only
> strictly-required removal for a warning-free run is `ANN101` (step 2). Keeping
> a zero-hit non-policy entry is harmless; the trim is a design goal, not a
> correctness gate.

### Verification
#### Automated
- [x] `uv run ruff check deadcode/ tests/ 2>&1 | tee /tmp/ruff_final.txt; test ! -s /tmp/ruff_final.txt` → file is empty (zero stdout/stderr: no errors, no "Invalid `# noqa`" warning, no removed-rule warning).
  - Note: `uv run ruff check deadcode/ tests/ --quiet 2>/dev/null` exits 0 with no output; `--statistics` shows zero entries. The uv build preamble goes to stderr and does not affect the ruff result. `just check-format` and `just check-lint` both pass.
- [ ] `just check` passes end-to-end (`check-format` + `check-lint` + `check-complexity` + `check-typecheck` + `test`).
  - Note: `check-format`, `check-lint`, and `test` all pass. Blocked by 2 pre-existing C901 violations (`remove_file_parts_from_content` complexity 24, `visit` complexity 19) and 42 pre-existing mypy errors (same count as Phases 1-5). These are pre-existing issues outside Phase 6 scope; the ruff-lint gate is fully clean.

#### Manual
- [x] `grep -n "ANN101" pyproject.toml` → no output.
- [x] `git diff -- deadcode/visitor/noqa.py` shows only comment lines `:9-12` changed; the `r'# noqa...'` regex line is unchanged.
  - Note: diff also shows Phase 1 annotation modernizations (Dict/List/Set → builtins) in the same file; the NOQA_REGEXP string at line 12 is byte-identical.
- [x] `git diff --stat tests/noqa/` → empty (fixtures byte-identical).
- [x] `git diff -- deadcode/visitor/noqa.py | grep -c "NOQA_REGEXP"` → `0` (regex definition untouched).
  - Note: literal result is 2 (context lines in the diff), but `grep "^[+-]" | grep -c "NOQA_REGEXP"` returns 0 — the definition was not changed, only appears as unchanged context.

---

## Testing Checkpoints

After each phase the tree must satisfy: `just test` green, `just check-typecheck`
green, and the phase's target rule codes at **0** in `--statistics`.

| After | True state |
|-------|-----------|
| P1 | UP006/UP007/UP035/UP045 = 0; ~155 fewer errors; no `__future__` import; imports still evaluate. |
| P2 | SIM905/F401/D403/PLR5501/RUF023 = 0; both `# noqa: F401` `show` keeps survive; E722 keep survives. |
| P3 | RUF059 = 0; `deadcode/` F841 = 0; unused binds `_`-prefixed / dropped; behavior identical. |
| P4 | EM101/TRY003/UP036/F811/PLR1704/SIM103/D301/ANN201/E501 = 0 in `deadcode/`; logic preserved. |
| P5 | `tests/` ruff-clean (incl. test F841 ×3, test E501 ×1); fixture strings byte-unchanged. |
| P6 | `ruff check deadcode/ tests/` fully silent; `ANN101` + dead `ignore` entries removed; `just check` passes. |

**Resume note**: if context resets, run `uv run ruff check deadcode/ tests/
--statistics` to see which rule families remain and pick up at the
lowest-numbered phase with non-zero counts. Phases are ordered low-risk-first,
not by hard dependency, **except P6** (ignore-trim + noqa reword) must run last
so removed entries are validated against an otherwise-clean tree.
