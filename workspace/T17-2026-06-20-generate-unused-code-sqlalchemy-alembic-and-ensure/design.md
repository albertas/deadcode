# Design Discussion

## Current State

Deadcode has one framework scenario test file, `tests/frameworks/test_fastapi.py`,
covering FastAPI route handlers (decorator suppression) and Pydantic models
(inherits-from suppression). It is the template for all framework work (T16).

Scenario tests subclass `BaseTestCase` (`deadcode/utils/base_test_case.py:11`),
define an in-memory `dict[str, str]` of fixture sources as `self.files`, call the
real `main()` (`deadcode/cli.py:10`) with a `list[str]` of CLI args, and assert on
the exact `path:line:col: DCxx Description` string (`test_fastapi.py:44-53`). No
real filesystem I/O occurs — `setUp` patches `open`, `find_python_filenames`,
`os.remove`, and `parse_pyproject_toml→{}` (`base_test_case.py:37-57`).

Six of the twelve `ignore-*` options are actually consumed by the visitor
(research Q2 table); the relevant wired ones are:
- `ignore_names` / `ignore_names_in_files` — `find_unused_code_visitor.py:287-288`
- `ignore_definitions` — `:532`
- `ignore_definitions_if_inherits_from` — `:533`
- `ignore_definitions_if_decorated_with` — `:534`
- `ignore_bodies_if_inherits_from` — `:543`

`_apply_ignore_definitions` runs before pre-visit, so it suppresses the
container's **own name**; `_apply_ignore_bodies` runs after the container is
defined but before body children, so it suppresses only **body members**
(`find_unused_code_visitor.py:520-547`, research Q2).

Inheritance tracking (`get_inherits_from`, `find_unused_code_visitor.py:415-429`)
extracts base names at line 421 with `base.id` — **only `ast.Name` bases**.
Dotted bases such as `db.Model` / `models.Model` (`ast.Attribute`) are silently
dropped (research Q3). Transitive resolution works one hop, same-file only.

No SQLAlchemy, Alembic, or Flask configuration, docs, or tests exist anywhere in
the repo (research Q6, Open Areas).

## Desired End State

Two new scenario test files demonstrate Deadcode correctly suppresses
SQLAlchemy/Alembic false positives via documented options while still reporting
genuinely unused code:

- `tests/frameworks/test_sqlalchemy.py` — ORM models and mapped columns.
- `tests/frameworks/test_alembic.py` — migration functions and revision identifiers.

One minimal implementation extension enables the one mainstream pattern existing
options cannot handle: **dotted base classes** (`db.Model`). A
SQLAlchemy + Alembic configuration section is added to `README.md` and
`docs/unused-detection-and-ignoring.md`, mirroring the existing FastAPI block.

**Verify:** `just test` passes (new tests assert exact finding strings); `just
check` passes; each test shows the real-dead-code finding(s) still emitted
alongside the framework code being silenced.

## Patterns to Follow

- **Scenario-test shape** — `tests/frameworks/test_fastapi.py:5-53`: subclass
  `BaseTestCase`, set `self.files`, call `main([...,'--no-color', '--ignore-...'])`,
  `assertEqual` on the exact `path:line:col: DCxx ...` string.
- **inherits-from suppression** — `test_fastapi.py:55-77` (Pydantic): pass
  `--ignore-definitions-if-inherits-from=Base` AND, for column suppression,
  `--ignore-bodies-if-inherits-from=Base` (definitions suppress the class name,
  bodies suppress members — both are required for a model that owns columns).
- **decorator suppression** — `test_fastapi.py:44-53`: `--ignore-definitions-if-decorated-with=@event.*`
  matches via `get_decorator_name` (`deadcode/visitor/utils.py:53-61`), which
  already builds dotted names for `@event.listens_for(...)`.
- **Dotted-name extraction to reuse for the extension** — `get_decorator_name`
  (`utils.py:53-61`) walks `ast.Attribute` chains into a dotted string; mirror
  this in a base-name helper used by `get_inherits_from`.
- **README framework block** — `README.md:54-60` (FastAPI/Pydantic toml block):
  copy its structure for the SQLAlchemy/Alembic section.
- **DC codes** — `deadcode/constants.py:36-49`: DC01 variable, DC02 function,
  DC03 class. Class-body `name = Column(...)` is a `Store` Name → DC01 variable
  (`find_unused_code_visitor.py:490-494`), not DC05.

**Do NOT follow / do not rely on:** the six declared-but-unused options
(`ignore_bodies_of`, `ignore_bodies_if_decorated_with`, `ignore_if_*`,
`ignore_names_if_*`, research Q2 table) — they are inert; tests must use only
wired options. `self.ignore_decorators` is never populated (`:50`, research Q2)
— do not depend on it.

## Design Decisions

1. **Two files, split by framework**: `test_sqlalchemy.py` and `test_alembic.py`
   — they are distinct frameworks with distinct conventions, matching the
   per-framework file convention (`test_fastapi.py`). Honors CLAUDE.md §7.

2. **Lean on wired options for the canonical cases**: pure SQLAlchemy 2.0
   (`class Base(DeclarativeBase)`, `class User(Base)`) and 1.x
   (`Base = declarative_base()`, `class User(Base)`) use `ast.Name` bases, so
   `--ignore-definitions-if-inherits-from=Base` + `--ignore-bodies-if-inherits-from=Base`
   already work. No new code needed for these.

3. **Extend `get_inherits_from` for dotted bases**: extract attribute-style base
   names (`db.Model`, `models.Model`) instead of dropping them
   (`find_unused_code_visitor.py:421`). This is the one mainstream SQLAlchemy
   pattern (Flask-SQLAlchemy `db.Model`) existing options cannot suppress.
   Implement via a small `get_base_name` helper modeled on `get_decorator_name`
   (`utils.py:53-61`); store both the dotted form (`db.Model`) and the trailing
   leaf (`Model`) so patterns `db.Model` and `*Model` both match via fnmatch
   (`ignore.py:48-55`). This is the only production-code change.

4. **Alembic via `ignore_names` + `ignore_names_in_files`**: `upgrade`,
   `downgrade`, `revision`, `down_revision`, `branch_labels`, `depends_on` are
   suppressed with `--ignore-names`; whole migration dirs (`*/versions/*`) with
   `--ignore-names-in-files`. Both wired (`:287-288`). No new code.

5. **Event listeners via existing decorator option**: `@event.listens_for(...)`
   handlers suppressed with `--ignore-definitions-if-decorated-with=@event.*`
   (already wired, `:534`). No new code.

6. **Every test keeps a genuinely-unused item** (an unreferenced helper
   function / plain class / module variable) and asserts it is still reported —
   proves suppression is targeted, not blanket (mirrors `_unused_helper`,
   `test_fastapi.py:39-53`).

7. **Docs mirror the FastAPI block**: add a SQLAlchemy/Alembic toml + CLI example
   to `README.md` (after `:60`) and `docs/unused-detection-and-ignoring.md`
   (after the Django/FastAPI scenarios at `:90-97`).

## What We're NOT Doing

- NOT wiring the six declared-but-unused ignore options — out of scope; the wired
  set plus the dotted-base fix covers SQLAlchemy/Alembic.
- NOT adding cross-file / imported-base transitive inheritance resolution
  (research Q3 limitation) — canonical cases match the direct base name.
- NOT adding new CLI flags or new `Args` fields.
- NOT adding built-in auto-detection of SQLAlchemy/Alembic (no implicit rules);
  suppression stays explicit and user-configured, like Django/FastAPI today.
- NOT touching the FastAPI test or unrelated visitor logic (CLAUDE.md §3).

## Open Risks

- **Dotted-base extension regression**: changing line 421 must not break the
  existing one-hop transitive lookup (`:424-427`), which keys `scopes.get` by a
  simple name. Keep the simple-name path intact; only add the dotted/leaf names.
  Run the full suite to confirm no existing inheritance test regresses.
- **`mapped_column` / `Mapped[...]` classification**: typed columns are
  `AnnAssign` in the class body; confirm they are suppressed by
  `ignore_bodies_if_inherits_from` and pin exact output in the test (the assertion
  is the source of truth if classification differs from expectation).
- **Both options needed for models with columns**: a reviewer may expect
  `--ignore-definitions-if-inherits-from` alone to silence a model; it does not
  silence its columns. Document this explicitly in the README/docs note.
