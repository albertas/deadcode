# Structure Outline

## Approach

Drive `just check-typecheck` from **42 errors → 0** by fixing types only (correct
annotations, narrowing `isinstance`, type-equivalent node constructs, generics,
`typing.cast`) — never `# type: ignore`, never config loosening, never logic
edits. Each phase clears one independent error *cluster*, lowers the live error
count by a known delta, and keeps `just test` green. The risky end-to-end `Part`
pipeline re-typing (fan-out into the removal helpers) is the last phase, so every
earlier phase stands on its own if the capstone needs more work.

**Shared verification primitives** (used by every phase):
- Count: `just check-typecheck 2>&1 | grep -c ': error:'` → expected remaining count.
- Per-file gone: `just check-typecheck 2>&1 | grep -c '<path>\.py:'` → `0`.
- No regression: `just test` exits `0`.
- No suppression added: `git diff -- deadcode/ | grep -c 'type: ignore'` does not increase.

Baseline today: **42 errors in 10 files** (live run confirmed).

---

## Phase 1: Isolated standalone fixes (42 → 38)

Three unrelated single-spot fixes in separate files; zero fan-out.

**Files**: `deadcode/utils/print_ast.py`, `deadcode/actions/parse_abstract_syntax_tree.py`, `deadcode/utils/remove_from_list.py`
**Key changes**:
- `print_ast.py:5` — delete the stray `# type: ignore` (`[unused-ignore]`).
- `parse_abstract_syntax_tree.py:13` — `ast.Module()` → `ast.Module(body=[], type_ignores=[])` (`[call-arg]`).
- `remove_from_list.py` — add module-local `T = TypeVar('T')`; `remove_from_list(elements: list[T], should_remove: Callable[[T], bool]) -> None` (clears 2× `[type-arg]`). `Callable` already imported from `collections.abc`.

**Verify**: `just check-typecheck 2>&1 | grep -c ': error:'` → `38`; the three files no longer appear (`grep -c 'print_ast.py:\|parse_abstract_syntax_tree.py:\|remove_from_list.py:'` → `0`); `just test` exits `0`.

---

## Phase 2: Correct `visit_X` node types + attribute narrowing in the fix-visitor (38 → 32)

Fix the two lying `visit_X` parameter annotations and narrow the attribute reads
they expose, all within `fix_unused_code_visitor.py`.

**Files**: `deadcode/visitor/fix_unused_code_visitor.py`
**Key changes**:
- `:261` `visit_With(node: ast.ClassDef)` → `visit_With(node: ast.With)` — clears `[override]` and `[attr-defined] .items` (`:263`).
- `:266` `item.optional_vars.id` — narrow `optional_vars` to `ast.Name` (the existing `isinstance(item.optional_vars, ast.AST)` guard becomes `isinstance(item.optional_vars, ast.Name)`) so `.id` resolves; type-equivalent (a non-`Name` target never had `.id`).
- `:286` `body_node.name` — read via `getattr(body_node, 'name', None)` (already the guard idiom on the same line) so `ast.stmt` has no missing `.name`.
- `:319` `visit_ImportFrom(node: ast.Import)` → `visit_ImportFrom(node: ast.ImportFrom)` — clears `[override]` and `[attr-defined] .module` (`:320`).

**Verify**: `grep -c ': error:'` → `32`; `just check-typecheck 2>&1 | grep -E 'fix_unused_code_visitor.py:(261|263|266|286|319|320)'` → empty; `just test` exits `0` (covers the import/with-removal fix paths).

---

## Phase 3: Position-bearing node reads via narrowing / `cast` (32 → 20)

Single technique applied to every spot that reads `lineno`/`col_offset`/
`end_lineno`/`end_col_offset` off a statically-`ast.AST` value (typeshed defines
these on `ast.stmt`/`ast.expr`, not `ast.AST`). Annotate/narrow the local where it
is statically a stmt/expr; use `typing.cast(ast.stmt, node)` only where recursion
makes the static type genuinely `ast.AST` (per Decision 4). New primitive
`typing.cast` — note in the diff.

**Files**: `deadcode/visitor/lines.py`, `deadcode/visitor/find_unused_code_visitor.py`, `deadcode/visitor/fix_unused_code_visitor.py`
**Key changes**:
- `lines.py:55,62,81` — cast/narrow the loop node before `.lineno`; resolves the two `[no-any-return]` at `:59,81` once the read is typed `int`.
- `find_unused_code_visitor.py:311,313,314` — annotate `first_node`/`last_node` locals as `ast.stmt` (or narrow) before reading position attrs.
- `fix_unused_code_visitor.py:131-134` — `get_original_code_lines(node: ast.AST)`: cast `node` to `ast.stmt` for the `lineno`/`end_lineno`/`col_offset`/`end_col_offset` reads.
- `fix_unused_code_visitor.py:256-258` — `remove_node(node: ast.AST)`: cast to `ast.stmt` for the `Part(node.lineno, …)` construction (4× `[attr-defined]`).

**Verify**: `grep -c ': error:'` → `20`; `grep -cE 'lines.py:(55|59|62|81)'` → `0`; `just test` exits `0` (line-number computation and node removal are exercised by the fix/diff tests).

---

## Phase 4: Deprecated `ast.Str`/`.s` → `ast.Constant` (20 → 16)

Replace removed-in-3.12 string-node API with the behavior-equivalent
`ast.Constant` + `str` check.

**Files**: `deadcode/visitor/find_unused_code_visitor.py`
**Key changes**:
- `:356,366,376,494` — `isinstance(node, ast.Str)` / `node.s` → `isinstance(node, ast.Constant) and isinstance(node.value, str)` then read `node.value`. Matches `ast.Str`'s old string-only semantics; clears 4× `[arg-type]`.

**Verify**: `grep -c ': error:'` → `16`; `grep -cE 'find_unused_code_visitor.py:(356|366|376|494)'` → `0`; `git diff deadcode/visitor/find_unused_code_visitor.py | grep -c 'ast.Str\b'` shows only removals; `just test` exits `0`.

---

## Phase 5: Helper annotation gaps (16 → 10)

Fill the remaining untyped params / var-annotation / missing-return gaps. These
are 4-tuple-typed helpers (the local removal algorithm genuinely uses
`tuple[int,int,int,int]` here, distinct from the `Part` pipeline of Phase 6).

**Files**: `deadcode/actions/remove_file_parts_from_content.py`, `deadcode/visitor/fix_unused_code_visitor.py`
**Key changes**:
- `remove_file_parts_from_content.py:48,86` — `code_parts_for_the_same_line: list[tuple[int, int, int, int]] = []` (`[var-annotated]`).
- `remove_file_parts_from_content.py:61` — annotate `remove_unused_fragments_from_a_line(line: str, code_parts: list[tuple[int, int, int, int]], index: int)` (`[no-untyped-def]`).
- `fix_unused_code_visitor.py:168` — `get_chars_to_remove(self, original_code_lines: list[str], fixed_code: str, first_line: int, first_col: int)` (`[no-untyped-def]`).
- `fix_unused_code_visitor.py:213` — `add_code_adjustments_for_cleaned_up_code_items(self, node: ast.AST) -> None` (all 3 call sites at `:269,342,420` discard the result → `-> None`; clears `[no-untyped-def]` + `[return]`).

**Verify**: `grep -c ': error:'` → `10`; `grep -cE 'fix_unused_code_visitor.py:(168|213)'` → `0`; `just test` exits `0`.

---

## Phase 6: `Part` pipeline re-typing — capstone (10 → 0)

Re-type the second pipeline element from the lying `list[tuple[int,int,int,int]]`
to the runtime truth `dict[Filename, list[Part]]`, end-to-end. Highest fan-out:
re-run `just check-typecheck` after the boundary edit to surface any follow-on
errors in `remove_file_parts_from_content.py` / `merge_overlaping_file_parts.py`
(which unpack 4-/6-tuples) and reconcile them within this phase (Open Risk).

**Files**: `deadcode/actions/find_unused_names.py`, `deadcode/cli.py`, `deadcode/actions/fix_or_show_unused_code.py`, `deadcode/visitor/fix_unused_code_visitor.py` (+ possible follow-on in `actions/remove_file_parts_from_content.py`, `actions/merge_overlaping_file_parts.py`)
**Key changes**:
- `find_unused_names.py:9-12` — return `tuple[Iterable[CodeItem], dict[Filename, list[Part]]]` (clears `:24` `[return-value]`).
- `fix_or_show_unused_code.py:15-17` — param `additional_code_parts_to_remove: dict[Filename, list[Part]]`; `.extend(...)` at `:37` now `Part`-typed (clears `[arg-type]`).
- `cli.py:22` — call site auto-resolves once both ends agree (`[arg-type]` gone).
- `fix_unused_code_visitor.py:166` — `convert_1d_part_to_2d(...) -> Part` (it already builds a `Part`; clears `[return-value]`); `get_chars_to_remove(...) -> list[Part]`; `.extend(...)` at `:224` now `Part`-typed.

**Verify**: `just check-typecheck` prints `Success: no issues found` and exits `0` (`grep -c ': error:'` → `0`); `just test` exits `0`; `git diff -- deadcode/ | grep -c 'type: ignore'` did not increase over baseline.

---

## Testing Checkpoints

After each phase, both invariants must hold — use to resume after a context reset:

| After phase | `grep -c ': error:'` | `just test` |
|-------------|----------------------|-------------|
| baseline    | 42                   | green       |
| 1           | 38                   | green       |
| 2           | 32                   | green       |
| 3           | 20                   | green       |
| 4           | 16                   | green       |
| 5           | 10                   | green       |
| 6           | 0 (`Success`)        | green       |

If a phase changes the count by an unexpected amount, treat it as signal (a
narrowing revealed a hidden error or the `Part` fan-out surfaced follow-ons), not
noise — reconcile before moving on. Phases 1–5 are each independently valuable and
mergeable even if Phase 6 stalls.

**Out of scope** (per design "What We're NOT Doing"): `visit_MatchClass`
(`find_unused_code_visitor.py:500`) is *not* among the 42 errors — its existing
`# type: ignore` is currently load-bearing; leave it untouched to stay surgical.
No `from __future__ import annotations`, no `tests/` annotations, no `CodeItem`
dataclass conversion.
