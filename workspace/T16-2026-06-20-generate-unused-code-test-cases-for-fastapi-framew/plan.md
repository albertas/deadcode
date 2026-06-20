# Implementation Plan

## Overview

Make the already-parsed-but-inert `--ignore-definitions-if-decorated-with` option
actually suppress decorated definitions by wiring it into the existing
`_apply_ignore_definitions` gate, then add configuration-driven FastAPI/Pydantic
scenario tests (each with a negative control) and document the recommended
`[tool.deadcode]` config. Phase 1 is the only production-code change; Phases 2–3
are pure test slices; Phase 4 is docs + stale-comment cleanup.

**Repo root:** `/home/niekas/tools/deadcode`. All paths below are relative to it.

**Verification commands (from `Justfile`):** `just test [path]`, `just check`
(runs format-check, lint, complexity C901, mypy, test). Complexity gate is McCabe
≤ 10 (`pyproject.toml`); the `visit()` change adds one branchless statement and
must not push it over.

---

## Phase 1: Wire `--ignore-definitions-if-decorated-with` end-to-end

### Changes

#### 1. Extend the ignore-definitions gate with a decorator disjunct
**File**: `deadcode/visitor/find_unused_code_visitor.py`
**Action**: modify `_apply_ignore_definitions` (currently `:527-539`)

Add a third parameter `decorators` and a third disjunct that mirrors the existing
`ignore_definitions_if_inherits_from` path exactly:

```python
def _apply_ignore_definitions(
    self,
    node_name: str | None,
    inherits_from: list[str] | None,
    decorators: list[str] | None,
) -> bool:
    """Activate should_ignore_new_definitions for name/inheritance/decorator matches.

    Returns True iff this call turned the flag on (i.e. the caller owns turning
    it back off in teardown).
    """
    if (
        (node_name and _match(node_name, self.args.ignore_definitions))
        or (inherits_from and _match_many(inherits_from, self.args.ignore_definitions_if_inherits_from))
        or (decorators and _match_many(decorators, self.args.ignore_definitions_if_decorated_with))
    ):
        if not self.should_ignore_new_definitions:
            self.should_ignore_new_definitions = True
            return True
    return False
```

`_match` and `_match_many` are already imported (`:29-30`); `_match_many` accepts
`(names, patterns)` (`ignore.py:54`), so decorator glob patterns like `@app.*`
work with no new matcher.

#### 2. Compute decorator names and pass them into the gate
**File**: `deadcode/visitor/find_unused_code_visitor.py`
**Action**: modify `visit()` (currently `:588-618`), only the
`_apply_ignore_definitions` call site at `:601`

```python
        inherits_from = self.get_inherits_from(node)
        if inherits_from:
            node.inherits_from = inherits_from  # type: ignore

        decorators = [
            utils.get_decorator_name(decorator) for decorator in getattr(node, 'decorator_list', [])
        ] or None

        should_turn_off_ignore_new_definitions = self._apply_ignore_definitions(
            node_name, inherits_from, decorators
        )
```

Notes:
- Use `utils.get_decorator_name` — the module already does
  `from deadcode.visitor import utils` (`:18`) and calls `utils.get_decorator_name`
  elsewhere (`:440,447`). **Do not** add a bare `from ... import get_decorator_name`
  (deviation from structure — see summary).
- `getattr(node, 'decorator_list', [])` no-ops on nodes without `decorator_list`
  (Open Risk #1): only `FunctionDef`/`AsyncFunctionDef`/`ClassDef` carry it; for all
  other nodes the comprehension is empty and `or None` yields `None`, so the new
  disjunct short-circuits to falsey.
- Teardown is unchanged: the existing `should_turn_off_ignore_new_definitions`
  bookkeeping (`:607-616`) resets `should_ignore_new_definitions` after the decorated
  subtree, so suppression does not leak to sibling definitions (Open Risk #2 —
  proven by the negative controls below).
- **Do not** touch `self.ignore_decorators`, `visit_ClassDef`, or
  `visit_FunctionDef` (design "Patterns to NOT follow").

#### 3. New option-level test
**File**: `tests/cli_args/test_ignore_definitions_if_decorated_with.py`
**Action**: create

Modeled on `tests/cli_args/test_ignore_definitions_if_inherits_from.py:7-59`
(inline `files` dict + `assertEqual` on `main()` output). `register` is defined and
used (referenced in the `@register` decorator → `visit_Name` Load → marked used), so
it is never reported; `registered_handler` is decorated; `unused_helper` is the
plain negative control.

```python
from deadcode.cli import main
from deadcode.utils.base_test_case import BaseTestCase


class TestIgnoreDefinitionIfDecoratedWith(BaseTestCase):
    def test_decorated_function_suppressed_plain_helper_still_reported(self):
        self.files = {
            'foo.py': """
                def register(func):
                    return func


                @register
                def registered_handler():
                    return 1


                def unused_helper():
                    return 2
                """
        }

        # With the flag: the decorated function is suppressed, the plain helper is not.
        output = main(['foo.py', '--no-color', '--ignore-definitions-if-decorated-with=@register'])
        self.assertEqual(output, 'foo.py:10:0: DC02 Function `unused_helper` is never used')

        # Without the flag: the decorated function IS reported (the gate is what suppresses it).
        output_without_flag = main(['foo.py', '--no-color'])
        self.assertEqual(
            output_without_flag,
            'foo.py:6:0: DC02 Function `registered_handler` is never used\n'
            'foo.py:10:0: DC02 Function `unused_helper` is never used',
        )
```

Line numbers were computed from `fix_indent` behavior (`fix_indent.py`: strips the
common margin and the leading blank line, so line 1 is `def register(func):`).
DC02 message format is `{filename}:{name_line}:{col}: DC02 Function \`{name}\` is never used`
(`get_unused_names_error_message.py`; name_line = the `def` line, not the decorator).

### Verification
#### Automated
- [x] `just test tests/cli_args/test_ignore_definitions_if_decorated_with.py` passes.
- [x] `just check` clean (format, lint, C901 complexity ≤ 10 on `visit()`, mypy).

#### Manual
- [x] Confirm the gate flips behavior on the same source. Run the test once; if the
  exact line/col differ from the computed `:10:0`/`:6:0` (e.g. `fix_indent` edge
  case), read the `AssertionError` diff, paste the actual `main()` output into the
  two `assertEqual` calls, and re-run to green. The semantic gate is fixed: the
  with-flag output must omit `registered_handler` and include `unused_helper`; the
  without-flag output must include both. (Test passed first try; computed line/col `:10:0`/`:6:0` were exact.)
- [x] `git grep -n 'ignore_definitions_if_decorated_with' deadcode/visitor/find_unused_code_visitor.py`
  → returns the new disjunct line (proves the option is now consumed by the visitor).

---

## Phase 2: FastAPI route-handler scenario test

### Changes

#### 1. New test package marker
**File**: `tests/frameworks/__init__.py`
**Action**: create (empty file)

#### 2. FastAPI scenario test
**File**: `tests/frameworks/test_fastapi.py`
**Action**: create

`class TestFastapiRoutes(BaseTestCase)` with inline source fixtures (FastAPI is
**not** imported or installed — `deadcode` parses text only, design decision 4).
Covers `@app.get`, `@router.post`, `@app.websocket`, `@app.on_event`, a
`Depends(get_db)` DI callable (already not a false positive — `get_db` is marked
used via `Depends(get_db)` Load), and a trailing undecorated `_unused_helper`
negative control. The fixture filename is `main.py` (not a test-file glob, so the
helper is reported).

```python
from deadcode.cli import main
from deadcode.utils.base_test_case import BaseTestCase


class TestFastapiRoutes(BaseTestCase):
    def test_route_handlers_suppressed_unused_helper_still_reported(self):
        self.files = {
            'main.py': """
                from fastapi import FastAPI, APIRouter, Depends

                app = FastAPI()
                router = APIRouter()


                def get_db():
                    return "db"


                @app.get("/items")
                def list_items(db=Depends(get_db)):
                    return []


                @router.post("/items")
                def create_item():
                    return {}


                @app.websocket("/ws")
                async def websocket_endpoint():
                    return None


                @app.on_event("startup")
                async def on_startup():
                    return None


                def _unused_helper():
                    return 42
                """
        }

        output = main(
            [
                'main.py',
                '--no-color',
                '--ignore-definitions-if-decorated-with=@app.*',
                '--ignore-definitions-if-decorated-with=@router.*',
            ]
        )

        self.assertEqual(output, 'main.py:31:0: DC02 Function `_unused_helper` is never used')
```

Why the rest is silent: `FastAPI`/`APIRouter`/`Depends` imports are used
(`FastAPI()`, `APIRouter()`, `Depends(...)`); `app`/`router` are used in decorators;
`get_db` is used via `Depends(get_db)`; the four handlers are suppressed by the
`@app.*`/`@router.*` globs. `_unused_helper` is a function (single-underscore
exemption applies only to *variables*, `ignore.py` `_ignore_variable`; functions get
no underscore exemption), so it is the sole reported line.

### Verification
#### Automated
- [x] `just test tests/frameworks/test_fastapi.py` passes.
- [x] `just check` clean.

#### Manual
- [x] Output is exactly the negative control — no handler lines. If the computed
  `:31:0` differs, run the test, read the diff, freeze the actual `main()` output in
  the `assertEqual`. The invariant: `_unused_helper` present; `list_items`,
  `create_item`, `websocket_endpoint`, `on_startup`, `get_db` all absent. (Test passed first try; computed `:31:0` was exact.)
- [x] Confirm the DI callable is not a false positive even without it being
  decorated: `git grep -n 'get_db' tests/frameworks/test_fastapi.py` shows `get_db`
  is undecorated yet absent from asserted output (used via `Depends`).

---

## Phase 3: Pydantic model scenario (no tool change)

### Changes

#### 1. Add a Pydantic test method
**File**: `tests/frameworks/test_fastapi.py`
**Action**: modify (add a method to `TestFastapiRoutes`)

Proves the existing `--ignore-definitions-if-inherits-from` already covers Pydantic
models and their fields — **no production code changes in this phase**. `Item`
inherits `BaseModel` (suppressed with its `name`/`price` fields); `UnusedPlainClass`
and its attribute are the negative control.

```python
    def test_pydantic_models_suppressed_via_inherits_from(self):
        self.files = {
            'models.py': """
                from pydantic import BaseModel


                class Item(BaseModel):
                    name: str
                    price: float


                class UnusedPlainClass:
                    unused_attribute = None
                """
        }

        output = main(['models.py', '--no-color', '--ignore-definitions-if-inherits-from=BaseModel'])

        self.assertEqual(
            output,
            'models.py:9:0: DC03 Class `UnusedPlainClass` is never used\n'
            'models.py:10:4: DC01 Variable `unused_attribute` is never used',
        )
```

`BaseModel` import is used (referenced as the base of `Item`). `Item`, `name`,
`price` are suppressed by the inheritance gate (`_apply_ignore_definitions`'s
`ignore_definitions_if_inherits_from` disjunct, unchanged). DC03 = class, DC01 =
variable (`constants.py`).

### Verification
#### Automated
- [x] `just test tests/frameworks/test_fastapi.py` passes (both methods). (2 passed; single-file coverage gate fails as expected, full `just check` is green.)
- [x] `just check` clean. (192 passed, 24 skipped, 98.72% coverage.)

#### Manual
- [x] Asserted output reports only `UnusedPlainClass` + `unused_attribute`, never
  `Item`/`name`/`price`. (Test passed first try; computed `:9:0`/`:10:4` were exact.)
- [x] No production file changed in this phase:
  `git status --short deadcode/` shows only the pre-existing Phase 1 decorator-gate
  edit (verified via diff: the `_match_many(..., ignore_definitions_if_decorated_with)`
  disjunct); this slice added only `tests/frameworks/test_fastapi.py`.

---

## Phase 4: Documentation + stale-comment cleanup

### Changes

#### 1. Remove the stale "not implemented yet" TODO/log
**File**: `deadcode/visitor/find_unused_code_visitor.py`
**Action**: modify `_define` (currently `:284-289`) — delete the now-inaccurate TODO
comment and `self._log(...)` block. `ignore_definitions` and
`ignore_definitions_if_inherits_from` are already implemented (and after Phase 1 so
is the decorator option), so the message is wrong (CLAUDE.md §3 — fix only the lines
our change makes wrong).

Delete exactly:

```python
        # TODO: add support for ignore_definitions, ignore_definitions_if_inherits_from options
        self._log(
            f'Options ignore_definitions, ignore_definitions_if_inherits_from not implemented yet. '
            f'Got these values: ignore_definitions={self.args.ignore_definitions}, '
            f'ignore_definitions_if_inherits_from={self.args.ignore_definitions_if_inherits_from}'
        )
```

Leave the rest of `_define` (the `ignored()` closure onward) untouched.

#### 2. README `[tool.deadcode]` FastAPI example
**File**: `README.md`
**Action**: modify — after the existing `[tool.deadcode]` example block (`:46-52`),
add a short FastAPI/Pydantic configuration example.

```markdown
For FastAPI and Pydantic projects, suppress route handlers (matched by their
decorators) and Pydantic models (matched by their base class):
\`\`\`
[tool.deadcode]
ignore-definitions-if-decorated-with = ["@app.*", "@router.*"]
ignore-definitions-if-inherits-from = ["BaseModel"]
\`\`\`
\`app\` and \`router\` are the conventional FastAPI instance names — rename the
globs to match your own variables. TOML values are a list: each pattern is a
separate list entry (they are not comma-split).
```

(Open Risk #3: TOML values are not comma-split — call this out so multi-pattern
config is authored as a list.)

#### 3. Docs: move the decorator option from "inert" to "working"
**File**: `docs/unused-detection-and-ignoring.md`
**Action**: modify

- In the "Known Gaps: Inert Ignore Options" list (`:51-62`), remove the
  `ignore_definitions_if_decorated_with` bullet (`:53`) — it is now consulted.
- In the Filtering Pipeline step 3 (`:70`), change
  "Checks inheritance-based gates" → "Checks inheritance- and decorator-based gates".
- Add a working scenario after Scenario 4 (`:91-93`):

```markdown
**Scenario 5**: Function decorated with `@app.get("/items")`,
`--ignore-definitions-if-decorated-with=@app.*` set.
- Step 3: Decorator gate matches `@app.get` against `@app.*`; the function
  definition (name and body) is marked used.
- Step 6: Name is in `used_names`, item is not unused, not reported.
```

Leave the `self.ignore_decorators` sentence (`:60`) unchanged — that seam is still
unwired and that statement is still accurate (design "Patterns to NOT follow").

### Verification
#### Automated
- [x] `just check` clean (format, lint, complexity, mypy) and `just test` fully green. (192 passed, 24 skipped, 98.71% coverage.)

#### Manual
- [x] `grep -n 'ignore-definitions-if-decorated-with' README.md docs/unused-detection-and-ignoring.md`
  → returns the new README config lines and the docs Scenario 5 flag.
- [x] `grep -rn 'not implemented yet' deadcode/visitor/find_unused_code_visitor.py`
  → returns nothing.
- [x] `grep -n 'ignore_definitions_if_decorated_with' docs/unused-detection-and-ignoring.md`
  → no longer appears in the inert-options bullet list (only the Scenario 5 hit at `:94` remains, which is the new wording).

---

## Testing Checkpoints

- [ ] **After Phase 1**: `--ignore-definitions-if-decorated-with` suppresses a
  decorated definition via the CLI; undecorated unused code still reported.
  `tests/cli_args/test_ignore_definitions_if_decorated_with.py` green. Minimal
  enabling fix — independently valuable even if Phases 2–4 are dropped.
- [ ] **After Phase 2**: FastAPI route handlers suppressed with the recommended glob
  config; the `_unused_helper` negative control still reported. `tests/frameworks/`
  exists.
- [ ] **After Phase 3**: Pydantic models suppressed via inheritance; no new tool code
  (`git status --short deadcode/` empty for this slice).
- [x] **After Phase 4**: README/docs carry the FastAPI config example; stale TODO/log
  removed; `just check` and `just test` fully clean — matches design "Desired End
  State" #1–3.

**Slicing note**: Phase 1 is the only phase touching production code; Phases 2–3 pass
*because of* Phase 1 (and the existing inheritance wiring); Phase 4 is docs + cleanup.
All phases are independently testable; later phases never block earlier ones from
being valuable.
