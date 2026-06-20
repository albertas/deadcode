# Design Discussion

## Current State

`deadcode` is a static unused-code analyzer. A single AST pass
(`FindUnusedCodeVisitor`) collects typed definition lists and one flat
`used_names` set; "unused" is a plain string-membership test —
`[item for item in defined_items if item.name not in used_names]`
(`deadcode/visitor/ignore.py:39-42`). Scope is recorded but plays **no role**
in matching (research Q2; `find_unused_code_visitor.py:597-618`).

For FastAPI this is the core problem (research cross-cutting notes):

- **Route handlers** (`@app.get("/")`, `@router.post(...)`) are functions whose
  names never appear at any in-project call site, so they land in `used_names`
  nowhere and are reported as DC02 false positives. `notes:696-700` lists
  "fastapi route decorator functions" as a known hard false-positive case.
- **Decorator names are computed but discarded.** `get_decorator_name`
  correctly yields `'@app.get'` for `@app.get("/path")`
  (`deadcode/visitor/utils.py:53-61`; `tests/visitor/test_utils.py:36-43`), but
  its only consumer is `self.ignore_decorators`, which is initialised to `[]`
  and **never populated from `self.args`** (research Q3;
  `find_unused_code_visitor.py:50,440,458`).
- **The natural suppression option is declared but inert.**
  `--ignore-definitions-if-decorated-with` is fully parsed into `Args`
  (`parse_arguments.py:105-115`) but never read by the visitor (research Q4/Q7).
  `docs/unused-detection-and-ignoring.md:51-62` flags it as "silently
  ineffective".
- The intended FastAPI mechanism per `notes:690-692` is **example
  configuration via ignore options**, not built-in framework recognition.

What already works in our favour:

- **Dependency-injection callables** referenced as `Depends(get_db)` mark
  `get_db` used via `visit_Name` Load (`find_unused_code_visitor.py:497-501`),
  so they are **not** false positives.
- **Inheritance-gated suppression works today.**
  `--ignore-definitions-if-inherits-from` is wired through
  `_apply_ignore_definitions` (`find_unused_code_visitor.py:533-534`,
  `get_inherits_from:422-436`) — this covers Pydantic models
  (`class X(BaseModel)`) and their fields.

## Desired End State

1. A new test module that exercises FastAPI-shaped source and asserts
   `deadcode`'s exact output, demonstrating: (a) framework entrypoints are
   **not** reported when the recommended configuration is applied, and (b)
   genuinely unused code in the same file **is still** reported.
2. `--ignore-definitions-if-decorated-with` actually suppresses decorated
   definitions (the minimal tool change that makes the documented FastAPI
   configuration real).
3. A documented `[tool.deadcode]` example configuration for FastAPI.

**Verification:** `just test` passes; the new tests fail before the visitor
wiring and pass after; `just check` (lint/format/typecheck) is clean.

## Patterns to Follow

- **Inline `files` dict + `assertEqual` on `main()` output** — the dominant
  scenario-test idiom. Model the new tests on
  `tests/cli_args/test_ignore_definitions_if_inherits_from.py:7-59`: set
  `self.files = {...}`, call `main([...flags...])`, assert the joined
  `file:line:col: DCxx ... is never used` string (research Q1;
  `tests/test_deadcode.py:22-29`).
- **`BaseTestCase`** virtual filesystem (`deadcode/utils/base_test_case.py`) —
  no real files, no FastAPI install needed; `fix_indent` strips leading indent
  so fixtures can be written as indented triple-quoted strings.
- **Decorator-option wiring should mirror the inheritance path**, not invent a
  new one: extend `_apply_ignore_definitions`
  (`find_unused_code_visitor.py:527-539`) with a `_match_many` check against
  `self.args.ignore_definitions_if_decorated_with`, exactly as
  `ignore_definitions_if_inherits_from` is handled at `:533-534`.
- **`_match`/`_match_many` glob primitives** (`ignore.py:49-55`,
  `fnmatchcase`) — decorator patterns like `@app.*`, `@router.*` work via
  existing glob support; no new matcher needed.

**Patterns to NOT follow:**

- Do **not** revive or wire `self.ignore_decorators`
  (`find_unused_code_visitor.py:440,458`). It is a dead, test-only seam; the
  CLI surface is `ignore_definitions_if_decorated_with`. Adding a second
  decorator mechanism would duplicate logic (CLAUDE.md §2/§3).
- Do **not** rely on the on-disk `tests/files/` fixtures or the
  `DeadCodeIntegrationTests` path — those need `os.chdir` + real files and have
  no per-scenario flexibility (research Q1).
- Do **not** make matching scope-aware or otherwise rework the flat-string core
  (out of scope, high blast radius).

## Design Decisions

1. **Deliverable is tests + a minimal enabling tool fix** — not built-in
   framework detection. `notes:690-692` explicitly wants configuration-driven
   handling. Built-in recognition is a large, speculative feature (CLAUDE.md
   §2). We make the documented config path actually work.

2. **Wire exactly one option: `--ignore-definitions-if-decorated-with`.** It is
   the option whose semantics ("ignore definition incl. name and body if
   decorated with …", `parse_arguments.py:107-110`) precisely match what a
   FastAPI route handler needs, and it slots into the already-working
   `_apply_ignore_definitions` gate. The other inert decorator options
   (`ignore_if_decorated_with`, `ignore_names_if_decorated_with`,
   `ignore_bodies_if_decorated_with`) stay inert — out of scope (research Q4).

3. **Test location: new `tests/frameworks/test_fastapi.py` (+ `__init__.py`).**
   These are framework-scenario tests, not single-CLI-option tests, so they do
   not belong in `tests/cli_args/` (one-file-per-option). A `frameworks/`
   directory also gives the pending SQLAlchemy/Django tasks (`BACKLOG.md:2-4`)
   a home. *Assumption:* grouping by framework is preferred over folding into
   `cli_args/`.

4. **Fixtures are plain source strings; FastAPI is not a test dependency.**
   `deadcode` parses text, never imports the target. Keeps `requirements*.txt`
   untouched (CLAUDE.md §3).

5. **Recommended config uses glob decorator patterns.** Document
   `ignore-definitions-if-decorated-with = ["@app.*", "@router.*"]` (covers
   `get/post/put/delete/patch/websocket/on_event`) in README and
   `docs/`. *Assumption:* `app`/`router` are the conventional instance names;
   users rename via their own config.

6. **Pydantic models reuse the existing inherits-from option.** Tests show
   `--ignore-definitions-if-inherits-from=BaseModel` already suppresses model
   classes/fields — no new code. Keeps the two framework idioms (decorator vs.
   inheritance) cleanly separated.

7. **Every scenario includes a negative control.** Each test file carries a
   genuinely-unused, undecorated helper that MUST still be reported, directly
   satisfying the task's "still detecting truly unused code" requirement.

## What We're NOT Doing

- No built-in/automatic FastAPI recognition (no decorator allow-list baked in).
- No wiring of the other inert ignore options.
- No change to the flat-string matching core or scope handling.
- No new runtime dependency on `fastapi`/`pydantic`/`starlette`.
- No reuse of the dead `self.ignore_decorators` seam.
- No reformatting/refactoring of adjacent visitor code (CLAUDE.md §3).

## Open Risks

- **`_apply_ignore_definitions` reads `node.decorator_list`.** `visit()` calls
  it generically for every node; only `FunctionDef`/`ClassDef` carry
  `decorator_list`, so the new code must `getattr(node, 'decorator_list', None)`
  and no-op otherwise. Verify with the negative-control assertions.
- **`should_ignore_new_definitions` teardown.** The decorator gate must
  participate in the existing on/off bookkeeping (`visit():601,615-616`) so the
  flag resets after the decorated subtree — risk of leaking suppression to
  siblings if mishandled. Covered by asserting the trailing unused helper is
  reported.
- **TOML values are not comma-split** (research Q4); multi-pattern config must
  be authored as a list. Reflect this in the documented example.
- **Stale TODO/log lines** at `find_unused_code_visitor.py:284-289` claim these
  options are unimplemented; update or remove the now-inaccurate note as part
  of the change (CLAUDE.md §3 — only the lines our change makes wrong).
