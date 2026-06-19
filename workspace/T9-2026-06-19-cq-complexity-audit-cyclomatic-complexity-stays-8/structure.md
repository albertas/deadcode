# Structure Outline

## Approach

Encode the McCabe ceiling of **8** in `pyproject.toml` first (the durable config
fact), confirm the four offenders surface at `> 8`, then refactor each offender
below 9 by extracting helpers in the existing flat/private-method style. Pure
structural refactor: behavior unchanged, verified by the pre-existing test suite
and the 95% coverage gate. One offender per phase, lowest-risk first, so a later
failure leaves earlier phases independently valuable.

The "phases" here are vertical in the sense that each crosses the layers this
task actually has — **config (ruff) → implementation function → test/coverage
verification** — and each ends green on `just check-complexity` for its target
plus `just test`. There is no DB/API/UI; the analogous full-stack slice is
"config threshold + one function refactored + its tests still pass".

---

## Phase 1: Encode `max-complexity = 8` in config

Add the mccabe threshold so the "8" is config, not a CLI magic number. After
this, `just check-complexity` enforces 8 and reports exactly the four known
offenders at `> 8` — establishing the baseline every later phase shrinks.

**Files**: `pyproject.toml`
**Key changes**:
- New section under `[tool.ruff.lint]`:
  ```toml
  [tool.ruff.lint.mccabe]
  max-complexity = 8
  ```
- `C901` stays in the global `ignore`; `select` unchanged (Decision 2). No
  Justfile edit — existing `--select C901` now enforces 8.

**Verify**: `just check-complexity` exits non-zero and lists exactly four
functions, each annotated `> 8`: `remove_file_parts_from_content`,
`visit`, `fix_indent`, `fix_or_show_unused_code`. `just test` still green
(config-only change touches no runtime code). Capture this offender list as the
baseline.

---

## Phase 2: Refactor `fix_or_show_unused_code` (9 → ≤ 8)

Split the per-file loop body into two same-module helpers so the IO seams stay
patchable by `BaseTestCase`.

**Files**: `deadcode/actions/fix_or_show_unused_code.py`
**Key changes**:
- `_compute_updated_content(filename: Filename, file_unused_items: list[CodeItem], additional_code_parts_to_remove: dict[Filename, list[Part]]) -> str` — parts merge + `f.readlines()` + `remove_file_parts_from_content` + join. `open` call site stays in this module.
- `_emit_for_file(filename: Filename, updated_file_content: str, args: Args) -> str | None` — the dry / fix / remove branch. `open` (write), `os.remove`, and `unified_diff` call sites stay in this module (Decision 5).
- `fix_or_show_unused_code` becomes: group-by-filename loop → call the two helpers → accumulate `result`.

**Verify**: `just check-complexity` no longer flags `fix_or_show_unused_code`
(three offenders remain). `just test` green; coverage ≥ 95%. Spot-check that
`tests/cli_args/test_fix.py`, `test_dry.py`, and `tests/fix/test_empty_files.py`
(asserts `os_remove`) still pass — these exercise all three output branches.

---

## Phase 3: Refactor `fix_indent` (10 → ≤ 8)

Extract the two scan/strip loops into same-file private helpers; keep the
try/except and blank-line trimming in `fix_indent`.

**Files**: `deadcode/utils/fix_indent.py`
**Key changes**:
- `_find_common_margin(lines: list[str]) -> int` — the min-indent scan (`:18-22`); returns `sys.maxsize` when no content line found.
- `_strip_margin(lines: list[str], margin: int) -> None` — in-place de-indent loop (`:27-33`), preserving the walrus `prefix_without_spaces` / else logic.
- `fix_indent` keeps `try/except UnicodeError -> None`, the first-line strip, the `if margin < sys.maxsize` guard, and the `while lines and not lines[0]` blank-trim.
- Helpers are module-private; `fix_indent` is already in `[tool.deadcode] ignore_names`, so the new `_`-prefixed helpers won't be flagged as unused.

**Verify**: `just check-complexity` no longer flags `fix_indent`, and its score
is confirmed **≤ 8** (not merely < 10 — Open Risk). `just test` green; coverage
≥ 95%. `tests/utils/test_fix_indent.py` (3 tests) passes unchanged; downstream
users (`base_test_case.py`, `tests/cli_args/test_dry.py`) still green.

---

## Phase 4: Refactor `visit` (19 → ≤ 8)

The method is a linear pipeline of phases (not deeply nested); extract each phase
into a private method and make `visit` an orchestrator. Flag/scope semantics stay
identical.

**Files**: `deadcode/visitor/find_unused_code_visitor.py`
**Key changes**:
- `_apply_ignore_definitions(self, node: ast.AST, node_name: str | None, inherits_from: list[str] | None) -> bool` — the `should_ignore_new_definitions` activation block (`:530-540`); returns/sets the activation flag.
- `_maybe_push_scope(self, node: ast.AST) -> bool` — scope push for `ClassDef`/`FunctionDef`/`AsyncFunctionDef` (`:550-556`); returns whether a scope was pushed (drives teardown pop).
- `_visit_type_comment(self, node: ast.AST) -> None` — type-comment reparse + recurse (`:566-569`).
- `_visit_children(self, node: ast.AST) -> None` — the `ast.iter_fields` traversal replacing `generic_visit` (`:573-583`).
- Pre/post dynamic dispatch (`visit_<Cls>` / `visit_<Cls>_after_visiting_child_nodes`) may fold into small `_dispatch_pre_visit` / `_dispatch_post_visit` helpers.
- `visit` becomes: name → inherits_from → ignore-defs → pre-dispatch → maybe-push-scope → type-comment → children → post-dispatch → teardown (reset flag, pop scope).

**Verify**: `just check-complexity` no longer flags `visit` (one offender left).
`just test` green; coverage ≥ 95%. Both
`tests/visitor/test_find_unused_code_visitor.py` strategies pass —
`TestVisitorPathsViaMain` and `TestVisitorDirectUnits` (async def, type comment,
`__all__`, unreachable code, `visit_MatchClass`).

---

## Phase 5: Refactor `remove_file_parts_from_content` (24 → ≤ 8)

Highest-risk refactor — done last. Extract the four-way line dispatch into
per-branch handlers; thread the ~10 mutable loop locals through one `@dataclass`
state object (pass-by-reference keeps mutation semantics identical).

**Files**: `deadcode/actions/remove_file_parts_from_content.py`
**Key changes**:
- `@dataclass` (mutable) `_RemovalState` grouping the loop locals: `updated_content_lines`, `unused_part_index`, `previous_non_removed_line`, `has_block_started`, `was_block_removed`, `next_line_after_removed_block`, `indentation_of_first_removed_line`, `empty_lines_in_a_row_list`, `empty_lines_before_removed_block_list` (fields documented with inline `#`).
- `_handle_first_line(line: str, current_lineno: int, code_part: Part, state: _RemovalState) -> None` — Branch B (`:172`), single-line vs multi-line sub-branches.
- `_handle_last_line(line: str, code_part: Part, state: _RemovalState) -> None` — Branch C (`:247`), buffer append/swap + block-end flags.
- `_handle_normal_line(line: str, state: _RemovalState) -> None` — Branch D (`:331`), blank / no-prior-block / after-block (`pass` insertion).
- `remove_file_parts_from_content` keeps the loop, Branch A interior-skip `continue`, the four-way dispatch, and the post-loop `pass` fixup; `print(...)` debug lines and commented-out blocks stay put (out of scope).
- IO-free helpers `list_get`, `get_indentation`, `ends_with_semicolon`, `indentation_is_not_childs`, `remove_unused_fragments_from_a_line` stay in the module.

**Verify**: `just check-complexity` exits **0** (no offenders). `just test`
green; coverage ≥ 95%. `tests/actions/test_remove_file_parts_from_content.py`
plus all `tests/fix/*` pass unchanged. Extract one branch at a time, running
`just test` after each, to localize any ordering regression. Finally:
**`just check` green end-to-end** (format + lint + complexity + typecheck + test).

---

## Testing Checkpoints

Resumable state after each phase (re-derive current phase by running
`just check-complexity` and counting remaining offenders):

- **After Phase 1**: `just check-complexity` reports exactly 4 offenders, all
  `> 8`. `just test` green. Threshold is config, not CLI.
- **After Phase 2**: 3 offenders remain (`fix_or_show_unused_code` cleared).
  `just test` green, coverage ≥ 95%.
- **After Phase 3**: 2 offenders remain (`fix_indent` cleared, score confirmed
  ≤ 8). `just test` green.
- **After Phase 4**: 1 offender remains (`visit` cleared). `just test` green.
- **After Phase 5**: 0 offenders; `just check-complexity` exits 0;
  `just check` green end-to-end.

**Invariants every phase**: no behavior change (no test edits unless an
extraction exposes an untested branch dropping coverage < 95% — then add the
minimal test only); `C901` stays in global `ignore`; `print`/commented-out dead
code untouched; only the four named functions are modified.
