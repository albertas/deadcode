# Structure Outline

## Approach

`ruff check deadcode/ tests/` currently reports **249 errors + non-error
warnings**. Drive it to a clean, *warning-free* exit by fixing violations
rule-family-by-rule-family (autofix-first, then manual one-offs), gating every
slice on `just test` + `just check-typecheck`, then trimming the now-dead
`ignore` entries so most rules are actively enforced. No behavior changes; no
`--unsafe-fixes`; no refactors beyond the lines ruff flags (CLAUDE.md §3).

A "vertical slice" here crosses: **source edit → config (`ignore` /
`per-file-ignores`) → behavioral verification (tests + mypy) → ruff error-count
drop**. Each phase leaves the tree green and independently shippable: if a later
phase fails, earlier phases still reduce the error count and keep `just check`
passing.

Shared verification primitives (used per phase):
- `uv run ruff check deadcode/ tests/ --statistics` — per-rule remaining counts.
- `just test` — full pytest gate (`--cov-fail-under=95.0`), catches wrongly-removed symbols.
- `just check-typecheck` — mypy `strict`, confirms PEP 604/585 import-time safety.

---

## Phase 1: Modernize type annotations (autofix UP006/UP007/UP035/UP045)

Converge the package's `typing.List/Dict/Optional/Union` forms onto builtin
generics + PEP 604 unions (already native in 5 spots, research Q1). ~155 of the
249 errors. This is the largest, lowest-risk batch and establishes the style the
rest build on.

**Files**: `deadcode/**/*.py` (esp. `cli.py`, `constants.py`, `data_types.py`,
`visitor/noqa.py`, `visitor/find_unused_code_visitor.py`,
`visitor/fix_unused_code_visitor.py`, `actions/*.py`, `utils/*.py`).
**Key changes**:
- `typing.List[X]` → `list[X]`, `Dict[K,V]` → `dict[K,V]`, `Optional[X]` → `X | None`, `Union[A,B]` → `A | B`.
- `from typing import List, Optional, …` → trimmed/removed import lines (UP035).
- No `from __future__ import annotations` added (design §2).

**Verify**: `uv run ruff check deadcode/ tests/ --fix` (safe only) then
`--statistics` shows UP006/UP007/UP035/UP045 = 0; `just test` and
`just check-typecheck` pass (confirms `Literal` aliases in `constants.py:4-33`
and `NamedTuple`/`dataclass` bodies in `data_types.py` evaluate at import).

---

## Phase 2: Remaining safe autofixes (SIM905, F401, D403, PLR5501, RUF023)

Apply the rest of the safe-autofix codes. F401 (35, mostly the copied header in
`fix_unused_code_visitor.py`, Q4) carries getattr/string-dispatch risk — verify
behaviorally, not by static reading (design §7).

**Files**: `visitor/fix_unused_code_visitor.py`, `visitor/find_unused_code_visitor.py`,
`utils/nested_scopes.py`, plus SIM905 `.split('.')` sites.
**Key changes**:
- Remove unused imports (F401) — but **keep** `import print_ast as show  # noqa: F401` and `except:  # noqa: E722`.
- `'a.b'.split('.')` → `['a', 'b']` (SIM905); D403/PLR5501/RUF023 single-site fixes.

**Verify**: `--statistics` shows SIM905/F401/D403/PLR5501/RUF023 = 0; `just test`
+ `just check-typecheck` pass (catches any import removed that was reachable via
`getattr`/`visit_*`). `grep -c 'noqa: F401' deadcode/visitor/*.py` still returns 2.

---

## Phase 3: Manual unused-binding renames (RUF059, F841)

Prefix deliberately-unused unpack targets / locals with `_` per the established
convention (`merge_overlaping_file_parts.py:6-7`, CLAUDE.md §6 throwaway caveat)
rather than adding `# noqa`. RUF059 (16) + F841 (4), none autofixable.

**Files**: `actions/merge_overlaping_file_parts.py`,
`actions/remove_file_parts_from_content.py`,
`visitor/fix_unused_code_visitor.py` (`node_name` at `:439`).
**Key changes**:
- `insert_code_b, …` → `_insert_code_b, …`; `node_name` → `_node_name` (or drop the bind).

**Verify**: `--statistics` shows RUF059/F841 = 0; `just test` passes (these are
read-only renames of unused binds — behavior identical).

---

## Phase 4: Manual real-issue one-offs (EM101/TRY003, UP036, F811, PLR1704, SIM103, D301, E501)

Fix each ≤1-site real issue rather than suppress, keeping every rule enforced
(design §4). E501 (14) wrapped manually.

**Files**: `visitor/fix_unused_code_visitor.py:182` (the sole `raise`, Q3),
`actions/merge_overlaping_file_parts.py` (SIM103), and the F811/PLR1704/UP036/D301/E501 sites.
**Key changes**:
- `raise ValueError('…')` → extract message to a local (`message = …; raise ValueError(message)`) — satisfies EM101 + TRY003 together.
- UP036: delete the dead `sys.version_info` branch. SIM103: collapse `if …: return True / return False`.
- E501: manual line wraps (no logic change).

**Verify**: `--statistics` shows EM101/TRY003/UP036/F811/PLR1704/SIM103/D301/E501
= 0; `just test` passes; `git diff` on these lines is logic-preserving (visual /
`just check-typecheck`).

---

## Phase 5: Test-suite fixes (PTH109, PT011, SLF001)

Bring `tests/` to zero ruff errors. Prefer real fixes; add a `per-file-ignores`
entry only where a fix is awkward (design §5). Never touch fixture source strings
or assertions (design "What We're NOT Doing").

**Files**: `tests/**` (PTH109 + PT011 sites), `pyproject.toml`
(`[tool.ruff.lint.per-file-ignores]` `"tests/*"`).
**Key changes**:
- `os.getcwd()` → `Path.cwd()` at the 2 PTH109 sites (keeps PTH109 active).
- `pytest.raises(ValueError)` → `pytest.raises(ValueError, match='…')` at `test_fix_unused_code_visitor.py:15` (PT011).
- Add `SLF001` to `per-file-ignores["tests/*"]` (tests legitimately read `visitor._log`).

**Verify**: `uv run ruff check tests/ --statistics` is empty; `just test` passes;
the intentionally-malformed `# noqa: DC02` fixture (`tests/noqa/test_noqa_comments.py:71`)
is byte-unchanged (`git diff --stat tests/noqa/`).

---

## Phase 6: Warning-free finish — reword `noqa.py`, trim `ignore`, full gate

Eliminate the remaining **non-error warnings** and trim dead `ignore` entries so
the run is fully silent and most rules enforced.

**Files**: `deadcode/visitor/noqa.py:8-12` (example-comment text only),
`pyproject.toml` (`[tool.ruff.lint] ignore`).
**Key changes**:
- Reword the inline example comments above `noqa.py:13` so ruff stops parsing literal `` `# noqa` `` as a directive — **`NOQA_REGEXP` string (`:5-15`) and `tests/noqa/` fixtures stay byte-identical** (design Open Risks).
- Remove `ANN101` (removed rule) and every `ignore` entry now yielding zero hits; **keep** policy ignores: `D1xx/D2xx/D4xx`, `T201`, `S101`, `FBT00x`, `C901`/`PLR09xx`, `G004`, `COM812`/`ISC001`, `RUF100`/`RUF012`.

**Verify**: `uv run ruff check deadcode/ tests/ 2>&1` produces **zero output** (no
errors, no "Invalid `# noqa` directive", no removed-rule warning); `just check`
passes end-to-end (`check-format` + `check-lint` + `check-complexity` +
`check-typecheck` + `test`); `git diff` touches only lint-driven lines.

---

## Testing Checkpoints

After each phase the tree must satisfy: `just test` green, `just check-typecheck`
green, and the phase's target rule codes at **0** in `--statistics`.

| After | True state |
|-------|-----------|
| P1 | UP006/UP007/UP035/UP045 = 0; ~155 fewer errors; imports still evaluate (tests pass). |
| P2 | SIM905/F401/D403/PLR5501/RUF023 = 0; 2 deliberate `# noqa: F401` survive. |
| P3 | RUF059/F841 = 0; unused binds `_`-prefixed, behavior identical. |
| P4 | EM101/TRY003/UP036/F811/PLR1704/SIM103/D301/E501 = 0; logic preserved. |
| P5 | `tests/` ruff-clean; fixture strings byte-unchanged. |
| P6 | `ruff check deadcode/ tests/` fully silent; `ignore` trimmed; `just check` passes. |

**Resume note**: if context resets, run `uv run ruff check deadcode/ tests/
--statistics` to see which rule families remain and pick up at the lowest-numbered
phase with non-zero counts. The phases are independent — order is for low-risk-first,
not hard dependency, except P6 (ignore-trim) must run last so removed entries are
validated against an otherwise-clean tree.
