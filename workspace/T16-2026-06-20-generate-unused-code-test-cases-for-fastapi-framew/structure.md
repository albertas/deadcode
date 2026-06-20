# Structure Outline

## Approach

Deliver FastAPI false-positive coverage as **configuration-driven** scenario tests
plus the one minimal tool change that makes the documented config real: wire the
already-parsed-but-inert `--ignore-definitions-if-decorated-with` option into the
existing `_apply_ignore_definitions` gate, exactly mirroring the working
`ignore_definitions_if_inherits_from` path. No built-in framework detection, no new
dependency, no rework of the flat-string matching core. Each slice is a thin
vertical: CLI flag → visitor gate → asserted `main()` output, every scenario
carrying a negative control that must still be reported.

---

## Phase 1: Wire `--ignore-definitions-if-decorated-with` end-to-end

Make the declared-but-inert decorator option actually suppress decorated
definitions (name + body), driven by the CLI flag / `[tool.deadcode]` config.
Delivered with a focused option-level test proving a decorated function is
suppressed while an undecorated unused helper is still reported.

**Files**: `deadcode/visitor/find_unused_code_visitor.py`,
`tests/cli_args/test_ignore_definitions_if_decorated_with.py` (new)

**Key changes**:
- `_apply_ignore_definitions(node_name: str | None, inherits_from: list[str] | None, decorators: list[str] | None) -> bool`
  — add a third disjunct: `decorators and _match_many(decorators, self.args.ignore_definitions_if_decorated_with)`.
- In `visit()` (`:588-618`): compute
  `decorators = [get_decorator_name(d) for d in getattr(node, 'decorator_list', [])] or None`
  and pass to `_apply_ignore_definitions`. `getattr` no-ops on nodes lacking
  `decorator_list` (Open Risk #1). Teardown via existing
  `should_turn_off_ignore_new_definitions` bookkeeping (Open Risk #2).
- Import `get_decorator_name` (already in `deadcode/visitor/utils.py:53`).
- Do **not** touch `self.ignore_decorators` (design "Patterns to NOT follow").

**Verify**: `just test tests/cli_args/test_ignore_definitions_if_decorated_with.py`
passes. The new test sets `self.files` with `@app.get("/x")`-decorated function +
a plain unused helper, calls
`main(['f.py', '--no-color', '--ignore-definitions-if-decorated-with=@app.*'])`,
and asserts output contains the helper's `DC02 ... is never used` line but **not**
the decorated function. To confirm it gates correctly, also assert that without the
flag the decorated function IS reported (run-twice assertion in the same test).

---

## Phase 2: FastAPI route-handler scenario test

A framework-shaped test module asserting `deadcode`'s exact output on FastAPI
source: route handlers (`@app.get`, `@router.post`, `@app.websocket`,
`@app.on_event`) are not reported when `--ignore-definitions-if-decorated-with`
is applied, while a genuinely-unused undecorated helper in the same file still is.

**Files**: `tests/frameworks/__init__.py` (new),
`tests/frameworks/test_fastapi.py` (new)

**Key changes**:
- `class TestFastapiRoutes(BaseTestCase)` with inline `self.files` fixtures
  (plain source strings; FastAPI not installed/imported — design decision 4).
- Fixture includes `app = FastAPI()`, `router = APIRouter()`, several decorated
  handlers, a `Depends(get_db)` callable (already not a false positive), and one
  trailing undecorated `def _unused_helper()` negative control (design decision 7).
- `main(['main.py', '--no-color', '--ignore-definitions-if-decorated-with=@app.*', '--ignore-definitions-if-decorated-with=@router.*'])`.

**Verify**: `just test tests/frameworks/test_fastapi.py` passes.
`assertEqual(output, '...DC02 ... `_unused_helper` is never used')` — exactly the
negative control, no handler lines. Confirms both suppression (a) and retained
detection (b) from "Desired End State" #1.

---

## Phase 3: Pydantic model scenario (no tool change)

Prove the inheritance idiom already covers Pydantic models: classes inheriting
`BaseModel` and their fields are suppressed via the existing
`--ignore-definitions-if-inherits-from`, keeping decorator vs. inheritance idioms
cleanly separated (design decision 6).

**Files**: `tests/frameworks/test_fastapi.py` (add a test method)

**Key changes**:
- `def test_pydantic_models_suppressed_via_inherits_from(self)` — fixture with
  `class Item(BaseModel): name: str ...` + an unused plain dataclass/helper control.
- `main(['models.py', '--no-color', '--ignore-definitions-if-inherits-from=BaseModel'])`.

**Verify**: `just test tests/frameworks/test_fastapi.py` passes; asserted output
reports only the undecorated/uninherited control, not the `BaseModel` subclass or
its fields. No production code changes in this phase — if it fails, the inheritance
gate regressed, not this slice.

---

## Phase 4: Documentation + stale-comment cleanup

Document the recommended FastAPI `[tool.deadcode]` configuration and remove the now-
inaccurate TODO/log lines that claim the option is unimplemented (CLAUDE.md §3 —
only the lines our change makes wrong).

**Files**: `README.md`, `docs/unused-detection-and-ignoring.md`,
`deadcode/visitor/find_unused_code_visitor.py` (`:284-289`)

**Key changes**:
- Add a `[tool.deadcode]` example:
  `ignore-definitions-if-decorated-with = ["@app.*", "@router.*"]` and
  `ignore-definitions-if-inherits-from = ["BaseModel"]`, noting TOML values are a
  list (not comma-split — Open Risk #3).
- In `docs/unused-detection-and-ignoring.md:51-62`, move
  `ignore-definitions-if-decorated-with` from "silently ineffective" to working.
- Delete or correct the stale `_log` TODO at `find_unused_code_visitor.py:284-289`.

**Verify**: `just check` (lint/format/typecheck) clean and `just test` fully
green. Inspect docs:
`grep -n "ignore-definitions-if-decorated-with" README.md docs/unused-detection-and-ignoring.md`
returns the new example lines, and
`grep -n "not implemented yet" deadcode/visitor/find_unused_code_visitor.py`
returns nothing.

---

## Testing Checkpoints

- **After Phase 1**: `--ignore-definitions-if-decorated-with` suppresses a
  decorated definition via the CLI; undecorated unused code still reported.
  `tests/cli_args/test_ignore_definitions_if_decorated_with.py` green. This is the
  minimal enabling tool fix — independently valuable even if Phases 2–4 are
  dropped.
- **After Phase 2**: FastAPI route handlers suppressed with the recommended glob
  config; the negative-control helper still reported. `tests/frameworks/` exists.
- **After Phase 3**: Pydantic models suppressed via inheritance; no new tool code.
- **After Phase 4**: README/docs carry the FastAPI config example; stale TODO/log
  removed; `just check` and `just test` fully clean — matches "Desired End State"
  #1–3 and the design's Verification gate.

**Note on slicing**: Phase 1 is the only phase touching production code; Phases 2–3
are pure test slices that pass *because of* Phase 1 (and existing inheritance
wiring); Phase 4 is docs + cleanup. All phases are independently testable; later
phases never block earlier ones from being valuable.
