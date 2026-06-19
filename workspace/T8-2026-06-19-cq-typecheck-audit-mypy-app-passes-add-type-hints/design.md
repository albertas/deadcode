# Design Discussion

## Current State

`just check-typecheck` runs `uv run mypy deadcode/` under `strict = true`
(`pyproject.toml:162-170`) and reports **42 errors in 10 files** (confirmed by a
live run, which the research did not perform). The codebase is already almost
fully annotated with modern syntax (`list[...]`, `| None`, `collections.abc`);
the failures are concentrated and concrete. Breakdown by error code:

- `[attr-defined]` ×19 — accessing `lineno`/`col_offset`/`end_lineno`/`items`/
  `id`/`module`/`name` on a value typed `ast.AST` (or the wrong concrete node).
- `[arg-type]` ×7 / `[return-value]` ×2 — the `Part`-vs-`tuple[int,int,int,int]`
  contract mismatch threaded through the fix pipeline + the `ast.Str.s` value
  type.
- `[no-untyped-def]` ×3, `[var-annotated]` ×2, `[type-arg]` ×2, `[override]` ×2,
  `[no-any-return]` ×2, `[unused-ignore]` ×1, `[return]` ×1, `[call-arg]` ×1.

The errors cluster into the two groups named in `task.md`: AST-visitor method
signatures under `deadcode/visitor/`, and the return/argument contract spanning
`find_unused_names` → `fix_or_show_unused_code` → `cli`.

## Desired End State

`just check-typecheck` exits 0 ("Success: no issues found"). No runtime behavior
changes: `just test` passes identically before and after. Verify with:

1. `just check-typecheck` → 0 errors.
2. `just test` → green (the full suite, unchanged).
3. `git diff` touches only annotations / type-narrowing / type-equivalent node
   constructs — no logic edits.

## Patterns to Follow

- **Modern generics + `| None` only**; `Iterable`/`Callable` from
  `collections.abc`, `Any`/`TypeVar`/`Literal` from `typing`
  (research Q5; `data_types.py:5`, `flatten_lists.py:3`).
- **Correct `visit_X` param to the concrete node type.** The good methods
  already do this: `visit_Attribute(node: ast.Attribute)`
  (`find_unused_code_visitor.py:343`), `visit_Call(node: ast.Call)` (`:358`),
  `visit_FunctionDef(node: ast.FunctionDef | ast.AsyncFunctionDef)` (`:432`).
- **Module-local `T = TypeVar('T')` for generic helpers** —
  `flatten_lists.py:3`, `remove_file_parts_from_content.py:6`.
- **Inline annotations for uninferable locals** — `nested_scopes.py:18`,
  `remove_file_parts_from_content.py:141`, `lines.py:28`.
- **`Part` (NamedTuple) is the canonical position record** — `data_types.py:38`;
  `remove_file_parts_from_content(... unused_file_parts: list[Part])` (`:128`)
  already types it correctly.

**Patterns NOT to follow / to correct:**

- The wrong `visit_X` annotations: `visit_With(node: ast.ClassDef)`
  (`fix_unused_code_visitor.py:261`) and `visit_ImportFrom(node: ast.Import)`
  (`:319`) — these are the source of the `[override]` + downstream
  `[attr-defined]` errors. Fix the annotation, do not suppress.
- The `tuple[int,int,int,int]` declarations that lie about a runtime `Part` /
  `dict[Filename, list[Part]]` (`find_unused_names.py:12`,
  `fix_or_show_unused_code.py:17`, `fix_unused_code_visitor.py:170,143`).
- `ast.Str` / `node.s` (deprecated, removed in 3.12) at
  `find_unused_code_visitor.py:355-376,494` — replace with the
  `ast.Constant` + `isinstance(value, str)` equivalent.
- Do NOT add `# type: ignore`; `strict` enables `warn_unused_ignores`, and the
  existing stray ignore at `print_ast.py:5` is itself one of the 42 errors.

## Design Decisions

1. **Fix annotations, never suppress.** Every error is resolved by a correct
   type, a narrowing `isinstance`, or a type-equivalent node construct — no
   `# type: ignore`, no loosening of mypy config. Rationale: the project's
   intent is genuine `strict` coverage; suppression would re-break later.

2. **Correct `visit_X` params to concrete node types.** `visit_With` →
   `ast.With`, `visit_ImportFrom` → `ast.ImportFrom`. This single fix clears the
   2 `[override]` errors plus the `[attr-defined]` on `.items`/`.id`/`.module`
   and the `Part(node.lineno, ...)` reads at `fix_unused_code_visitor.py:258`.

3. **Canonical pipeline type is `Part` / `dict[Filename, list[Part]]`.** The
   runtime value already is this (research Q3). Re-type the second tuple element
   end-to-end: `find_unused_names` return (`:12`), `fix_or_show_unused_code`
   param (`:17`), the `cli.py:22` call site (auto-resolves once both ends
   agree), `convert_1d_part_to_2d` return (`:143` already builds a `Part`),
   `get_chars_to_remove` return (`:170`), and the two `.extend(...)` sites
   (`fix_unused_code_visitor.py:224`, `fix_or_show_unused_code.py:37`). Chosen
   over "convert Parts to 4-tuples" because `Part` carries the extra
   `insert_code*` fields that the removal algorithm relies on.

4. **For genuinely-generic position reads, narrow the local/param to the
   position-bearing node type rather than `cast` or assert.** `lines.py`
   (`:55,62,81`), `get_original_code_lines` (`fix_unused_code_visitor.py:131`),
   and the `first_node`/`last_node` locals in `find_unused_code_visitor`
   (`:311-314`) read `lineno`/`col_offset`, which typeshed defines on
   `ast.stmt`/`ast.expr` but not on `ast.AST`. Prefer annotating the local /
   narrowing with `isinstance` where the node is statically a stmt/expr;
   fall back to `typing.cast(ast.stmt, node)` only where recursion makes the
   static type genuinely `ast.AST` (e.g. `lines.py`'s loop). `cast` is chosen
   over `assert isinstance` because assert changes runtime (can raise) and the
   helpers already guard with `try/except AttributeError`. This introduces
   `cast` as a new-but-standard primitive; note it in the diff.

5. **`ast.Str`/`.s` → `ast.Constant` + `isinstance(value, str)`.** Behavior-
   equivalent on 3.11 and removes the deprecated API. Use
   `isinstance(node, ast.Constant) and isinstance(node.value, str)` so only
   string constants match (matching `ast.Str`'s old semantics), then read
   `node.value`. Fixes the 4 `arg-type` errors at `:356,366,376,494`.

6. **Make `remove_from_list` generic.** `def remove_from_list(elements:
   list[T], should_remove: Callable[[T], bool]) -> None` with a module-local
   `T = TypeVar('T')` (matches `flatten_lists.py:3`). Clears both `[type-arg]`.

7. **`ast.Module()` → `ast.Module(body=[], type_ignores=[])`** at
   `parse_abstract_syntax_tree.py:13`. Equivalent empty module; clears
   `[call-arg]`.

8. **Annotate the remaining gaps directly.** `code_parts_for_the_same_line:
   list[tuple[int, int, int, int]] = []` (`remove_file_parts_from_content.py:48,
   86`, matching the 4-tuple usage there); add param types to
   `get_chars_to_remove` (`:168`) and `remove_unused_fragments_from_a_line`'s
   `code_parts` (`:61`); annotate `add_code_adjustments_for_cleaned_up_code_items`
   params and resolve its `-> str`/missing-return conflict (Decision 9). Remove
   the stray `# type: ignore` at `print_ast.py:5`.

9. **`add_code_adjustments_for_cleaned_up_code_items` return type follows its
   callers.** It declares `-> str` with no `return` (`:213`). Planning must read
   the call sites first: if the return value is unused, change to `-> None`; if
   used, add the correct `return`. Default assumption: unused → `-> None`.

## What We're NOT Doing

- Not changing any runtime logic, control flow, or algorithm.
- Not converting `CodeItem` to a dataclass (its `# TODO` is out of scope) or
  touching the commented-out `VariableInfo` block (`code_item.py:1-29`).
- Not relaxing mypy config, adding per-module overrides, or excluding files.
- Not adding `from __future__ import annotations` (codebase avoids it, Q5).
- Not type-checking or annotating `tests/` (mypy targets only `deadcode/`, Q6).
- Not auditing/annotating files that currently pass mypy beyond what the 42
  errors require.

## Open Risks

- **Pipeline re-typing fan-out (Decision 3).** Re-typing the second element to
  `Part` may surface *new* mypy errors in `remove_file_parts_from_content.py`
  and `merge_overlaping_file_parts.py`, which unpack values as 4- or 6-tuples
  (research Q4 flags 6-tuple unpacking at `:101,108,118`). The `Part`/tuple
  distinction must be reconciled there; expect a second mypy pass to reveal
  follow-on errors. Re-run `just check-typecheck` after each cluster.
- **Decision 9** depends on call-site inspection; the `-> None` default is an
  assumption to confirm during structure/planning.
- **`cast` introduction (Decision 4)** is a new pattern; if reviewers prefer
  zero new primitives, narrowing param types is the fallback but may ripple to
  callers that pass `ast.Module`.
- The live count is exactly 42; if a fix changes the count unexpectedly
  (e.g. a narrowing reveals a hidden error), treat it as signal, not noise.
