# Design Discussion

## Current State

McCabe cyclomatic complexity (`C901`) is currently **not enforced by default**:
`C901` sits in the global ruff `ignore` list (`pyproject.toml:87`), and there is
no `[tool.ruff.lint.mccabe]` section anywhere, so no `max-complexity` override
exists. The only place the rule runs is the dedicated recipe
`check-complexity` (`Justfile:28-29`):

```
uv run ruff check --select C901 deadcode/ tests/
```

`--select C901` re-enables the rule, but with ruff's **default threshold of 10**.
Running it at the target threshold of **8** today reports exactly four offenders
(authoritative `ruff` output, not estimates):

| Function | File:line | Score |
|---|---|---|
| `remove_file_parts_from_content` | `deadcode/actions/remove_file_parts_from_content.py:128` | **24 > 8** |
| `visit` | `deadcode/visitor/find_unused_code_visitor.py:518` | **19 > 8** |
| `fix_indent` | `deadcode/utils/fix_indent.py:4` | **10 > 8** |
| `fix_or_show_unused_code` | `deadcode/actions/fix_or_show_unused_code.py:15` | **9 > 8** |

Test coverage gate is strict: `pytest --cov=deadcode --cov-fail-under=95.0`
(`pyproject.toml [tool.pytest.ini_options]`). Each target has tests (research
Q6): `tests/actions/test_remove_file_parts_from_content.py`,
`tests/visitor/test_find_unused_code_visitor.py`,
`tests/utils/test_fix_indent.py`, and `fix_or_show_unused_code` is exercised
indirectly via `tests/cli_args/test_fix.py`, `test_dry.py`, and `tests/fix/*`
through `BaseTestCase` (`deadcode/utils/base_test_case.py:10`).

## Desired End State

`just check-complexity` (and the aggregate `just check`) passes cleanly with a
McCabe ceiling of **8** across `deadcode/` and `tests/`. Concretely:

1. `pyproject.toml` encodes `max-complexity = 8` so the "8" is a durable config
   fact, not a magic number passed on the command line.
2. The four offending functions are refactored below 9 (≤ 8).
3. `just test` still passes and coverage stays ≥ 95% — behavior is unchanged;
   this is a pure structural refactor.

**Verification:** `just check-complexity` exits 0; `just test` green;
`just check` green end-to-end.

## Patterns to Follow

- **Helper extraction in the same module.** `remove_file_parts_from_content.py`
  already keeps small private helpers alongside the main function: `list_get`
  (`:9`), `get_indentation` (`:23`), `ends_with_semicolon` (`:15`),
  `indentation_is_not_childs` (`:19`), `remove_unused_fragments_from_a_line`
  (`:61`). Extract new helpers in this same flat style — module-level functions,
  full-word names (CLAUDE.md §6, Code Best Practices).
- **`visit_<NodeType>` dispatch.** `FindUnusedCodeVisitor` already delegates
  per-node behavior to `visit_*` methods via `getattr` (`find_unused_code_visitor.py:543`).
  The branchy phases inside `visit` (activation flags, scope push/pop, type
  comments, child traversal) are natural private-method extractions
  (`_dispatch_pre_visit`, `_push_scope`, `_visit_children`, etc.) — matching the
  existing method-per-concern shape of the class.
- **Test seam patching.** Tests patch the SDK/IO seam on the defining module
  object (`BaseTestCase.setUp` patches
  `deadcode.actions.fix_or_show_unused_code.open`/`os.remove`,
  `base_test_case.py:49-52`). Any extracted helper that does IO must stay in the
  same module so these patches keep working — do **not** move `open`/`os.remove`
  call sites to a new module.
- **`@dataclass` for grouped state** (Code Best Practices "Data structures"): if
  `remove_file_parts_from_content`'s ~10 loop-state locals get threaded into a
  helper, group them into a small `@dataclass` rather than passing 10 params.

### Patterns NOT to follow / clean up cautiously

- `remove_file_parts_from_content` is littered with `print(...)` debug statements
  (e.g. `:154`, `:161`, `:168`, ... ~25 calls). These do **not** affect
  cyclomatic complexity and are **out of scope** — do not remove them as part of
  this task (CLAUDE.md §3 surgical changes). Mention them; leave them.
- Large commented-out code blocks (`:190-215`, `:263-281`) are pre-existing dead
  code. Do not delete (CLAUDE.md §3) — but when extracting a helper, the live
  code can move while the comments stay where they are.

## Design Decisions

1. **Encode threshold in config, not CLI**: add a `[tool.ruff.lint.mccabe]`
   section with `max-complexity = 8` to `pyproject.toml` (the lint config lives
   under `[tool.ruff.lint]`, `pyproject.toml:72`). The Justfile's existing
   `--select C901` then enforces 8. Rationale: the task says "configure the
   complexity threshold to 8"; CLI-only would leave the repo's effective default
   at 10 and the "8" undiscoverable.

2. **Keep `C901` in the global `ignore`** (`pyproject.toml:87`); do not add it to
   `select`. Rationale: the project's deliberate design is that plain
   `just lint` ignores complexity and the dedicated `just check-complexity`
   recipe surfaces it via `--select C901`. Removing it from `ignore` would change
   `lint`/`check-lint` behavior beyond the task's scope (CLAUDE.md §3).

3. **`remove_file_parts_from_content` (24→≤8): extract per-branch handlers.** The
   four-way line dispatch (interior-skip / first-line / last-line / normal-line,
   `:167/:172/:247/:331`) becomes the seam. Extract `_handle_first_line`,
   `_handle_last_line`, `_handle_normal_line` (and fold the post-loop `pass`
   fixup). Group the ~10 mutable loop locals into a `@dataclass` state object
   passed to each handler. This is the highest-risk refactor; rely on
   `tests/actions/test_remove_file_parts_from_content.py` + all `tests/fix/*`.

4. **`visit` (19→≤8): extract sequential phases into private methods.** The
   method is a linear pipeline of phases, not deeply nested — extract
   `_apply_ignore_definitions(node, node_name, inherits_from) -> bool`,
   `_maybe_push_scope(node) -> bool`, `_visit_type_comment(node)`,
   `_visit_children(node)`, and the post-visit dispatch. `visit` becomes an
   orchestrator. Each helper keeps the existing flag/scope semantics exactly.

5. **`fix_or_show_unused_code` (9→≤8): extract the per-file body.** Split the
   `for filename, ...` loop body into `_compute_updated_content(...)` (parts
   merge + read + remove) and `_emit_for_file(...)` (the dry/fix/remove
   branch). Keep `open`/`os.remove`/`unified_diff` call sites in this module so
   `BaseTestCase` patches still bind (Decision relies on the test-seam pattern).

6. **`fix_indent` (10→≤8): extract margin computation.** Pull the
   minimum-indent scan loop (`fix_indent.py:18-22`) into
   `_find_common_margin(lines) -> int` and the de-indent loop (`:27-33`) into
   `_strip_margin(lines, margin)`. `fix_indent` keeps the try/except and
   blank-line trimming. It is a single-function module today; the helpers stay
   in the same file (`fix_indent` is in `[tool.deadcode] ignore_names`, so the
   new private helpers won't be flagged as unused).

7. **No behavior change, ever.** Every refactor is verified by the pre-existing
   tests passing unchanged. We do not add new tests unless an extraction reveals
   an untested branch that drops coverage below 95% — only then add the minimal
   test (CLAUDE.md §4 goal-driven).

## What We're NOT Doing

- Not removing the `print(...)` debug noise in
  `remove_file_parts_from_content.py` (out of scope; doesn't affect complexity).
- Not deleting pre-existing commented-out code blocks.
- Not changing `C901`'s membership in the global `ignore`, nor altering `lint` /
  `check-lint` behavior.
- Not lowering complexity of functions already at ≤ 8 (only the four offenders).
- Not rewriting `remove_file_parts_from_content` as the "generator/stream"
  redesign its TODOs muse about — that is a separate, larger effort.
- Not touching `tests/` for complexity refactors (no test function in `tests/`
  exceeds 8 at threshold 8 — the four offenders are all in `deadcode/`).

## Open Risks

- **`remove_file_parts_from_content` is fragile.** ~24 decision points with
  heavily interdependent mutable state (two swapping blank-line buffers,
  `has_block_started`/`was_block_removed` flags). Extracting handlers risks
  subtle ordering bugs. Mitigation: extract one branch at a time, run
  `just test` after each step; the dataclass-state approach keeps mutation
  semantics identical (pass-by-reference object).
- **Coverage gate (95%)**: splitting a function can leave a newly-extracted
  branch unexercised if the original had dead-ish paths. Watch
  `--cov-fail-under=95.0`; add targeted tests only if it dips.
- **Threshold config interaction**: confirm ruff applies
  `[tool.ruff.lint.mccabe] max-complexity` when `--select C901` is passed (it
  does in current ruff). Verify by re-running `just check-complexity` after the
  config edit and before refactoring — it should report the same four offenders
  at "> 8".
- **`fix_indent` at exactly 10**: a light extraction may overshoot or undershoot;
  confirm the final score is ≤ 8, not just < 10.
