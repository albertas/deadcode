# Structure Outline

## Approach

Add two framework scenario test files (`test_sqlalchemy.py`, `test_alembic.py`)
that drive the real `main()` over in-memory fixtures and assert exact
`path:line:col: DCxx ...` strings, mirroring `test_fastapi.py`. All canonical
SQLAlchemy/Alembic patterns are covered by already-wired ignore options; the only
production-code change is extending `get_inherits_from` to capture dotted base
classes (`db.Model`) so Flask-SQLAlchemy models can be suppressed. Docs mirror the
existing FastAPI block. Each slice is one framework pattern, testable end-to-end
via `just test`.

Phases are ordered so every slice rests only on already-wired behavior except
Phase 4, which adds the single visitor change. If Phase 4 fails, Phases 1–3 and 5
remain independently valuable (they need no new code). Phase 6 (docs) is pure
documentation and depends on nothing.

---

## Phase 1: SQLAlchemy 2.0 declarative models (`Base` / `DeclarativeBase`)

Demonstrate suppression of `class Base(DeclarativeBase)` + `class User(Base)`
models and their `mapped_column` / `Mapped[...]` columns using wired
inherits-from options, while a genuinely unused helper is still reported.

**Files**: `tests/frameworks/test_sqlalchemy.py` (new)
**Key changes**:
- `class TestSqlalchemyDeclarative(BaseTestCase)` with
  `test_2_0_models_suppressed_unused_helper_still_reported(self)`
- Fixture `self.files = {'models.py': "...class Base(DeclarativeBase)... class User(Base): id: Mapped[int] = mapped_column(...) ... def _unused_helper(): ..."}`
- Invocation: `main(['models.py', '--no-color',
  '--ignore-definitions-if-inherits-from=Base',
  '--ignore-bodies-if-inherits-from=Base'])`
- No production code changes.

**Verify**: `just test` passes. Manually confirm the assertion pins exactly the
`_unused_helper` DC02 finding (and any genuinely-unused module var) and that no
`User` / `id` / `name` column findings appear. Cross-check `mapped_column`
(`AnnAssign`) classification by running
`just test -- tests/frameworks/test_sqlalchemy.py` and reading the asserted
string; the assertion is the source of truth for the exact DC code/line/col.

---

## Phase 2: SQLAlchemy 1.x declarative models (`declarative_base()` + `Column`)

Demonstrate the 1.x style — `Base = declarative_base()`, `class User(Base)` with
`name = Column(String)` body assignments (class-body `Store` Name → DC01) — is
suppressed by the same two wired options.

**Files**: `tests/frameworks/test_sqlalchemy.py` (extend; new test method)
**Key changes**:
- `test_1_x_models_with_column_assignments_suppressed(self)`
- Fixture: `Base = declarative_base()`, `class User(Base): id = Column(Integer, primary_key=True)`, plus an unreferenced module-level `UNUSED_CONSTANT = 1`.
- Same `--ignore-definitions-if-inherits-from=Base --ignore-bodies-if-inherits-from=Base`.

**Verify**: `just test` passes. Assertion contains only the genuinely-unused
item (e.g. `models.py:NN:0: DC01 Variable \`UNUSED_CONSTANT\` is never used`) and
none of the `Column`-bearing members. Confirms `--ignore-bodies-if-inherits-from`
silences body `Column(...)` assignments (DC01), not just the class name.

---

## Phase 3: SQLAlchemy event listeners (`@event.listens_for`)

Demonstrate `@event.listens_for(...)` handler functions are suppressed by the
wired decorator option, matching `get_decorator_name`'s dotted output `@event.*`.

**Files**: `tests/frameworks/test_sqlalchemy.py` (extend; new test method)
**Key changes**:
- `test_event_listeners_suppressed_via_decorator(self)`
- Fixture: `@event.listens_for(User, "before_insert")\ndef set_created(...)`, plus an undecorated unused function.
- Invocation adds `--ignore-definitions-if-decorated-with=@event.*`.

**Verify**: `just test` passes. Assertion reports only the undecorated unused
function; the `@event.listens_for` handler is absent. No production code change —
`get_decorator_name` (`deadcode/visitor/utils.py:53-61`) already builds
`@event.listens_for`.

---

## Phase 4: Dotted base classes (`db.Model`) — the one production change

Extend `get_inherits_from` to capture attribute-style bases (`db.Model`,
`models.Model`) currently dropped at `find_unused_code_visitor.py:421`, storing
both the dotted form and the trailing leaf so `db.Model` and `*Model` both match.

**Files**: `deadcode/visitor/utils.py`, `deadcode/visitor/find_unused_code_visitor.py`, `tests/frameworks/test_sqlalchemy.py`
**Key changes**:
- New helper `get_base_name(base: ast.Name | ast.Attribute) -> str | None` in
  `utils.py`, modeled on `get_decorator_name`: walks `ast.Attribute` chains into a
  dotted string (`'db.Model'`); returns plain `.id` for `ast.Name`; `None`
  otherwise. (No leading `@`.)
- `get_inherits_from` (`find_unused_code_visitor.py:415-429`): replace line 421
  base extraction so that for each base it appends the dotted name AND its trailing
  leaf when dotted; **keep the simple-name list used for the one-hop
  `self.scopes.get(name=base, ...)` transitive lookup unchanged** (use leaf/simple
  name as the scope key) to avoid regressing existing inheritance tests.
- New test `test_flask_sqlalchemy_db_model_suppressed(self)`: fixture
  `class User(db.Model): id = db.Column(...)`, suppressed with
  `--ignore-definitions-if-inherits-from=db.Model
  --ignore-bodies-if-inherits-from=db.Model` (or `*Model`).

**Verify**: `just test` passes (full suite — confirms no existing inheritance
test regresses, per Open Risks). New test asserts only the genuinely-unused item;
`db.Model` class and its `db.Column` body are absent. `just check` passes
(typecheck on the new `get_base_name` signature).

---

## Phase 5: Alembic migrations (`upgrade`/`downgrade` + revision identifiers)

Demonstrate Alembic migration boilerplate — `upgrade`, `downgrade` functions and
module-level `revision`, `down_revision`, `branch_labels`, `depends_on` — is
suppressed via `ignore_names` and whole versions dirs via `ignore_names_in_files`.

**Files**: `tests/frameworks/test_alembic.py` (new)
**Key changes**:
- `class TestAlembicMigrations(BaseTestCase)` with two methods:
  - `test_migration_callbacks_and_revision_ids_suppressed_via_ignore_names(self)`
    — fixture `versions/abc123_init.py` with `revision = "abc123"`, `down_revision = None`, `def upgrade(): ...`, `def downgrade(): ...`, plus an unreferenced `def _unused_migration_helper(): ...`. Invocation:
    `main(['versions/abc123_init.py', '--no-color',
    '--ignore-names=upgrade', '--ignore-names=downgrade',
    '--ignore-names=revision', '--ignore-names=down_revision',
    '--ignore-names=branch_labels', '--ignore-names=depends_on'])`.
  - `test_versions_directory_suppressed_via_ignore_names_in_files(self)` — same
    fixture, suppressed wholesale with `--ignore-names-in-files=*/versions/*`,
    asserting a real-dead-code item in a non-migration file is still reported.

**Verify**: `just test` passes. First assertion pins only
`_unused_migration_helper` (DC02); `upgrade`/`downgrade`/revision identifiers
absent. Second confirms `*/versions/*` silences the whole migration file while a
genuinely unused symbol elsewhere is still reported. No production code change
(`ignore_names`/`ignore_names_in_files` wired at `find_unused_code_visitor.py:287-288`).

---

## Phase 6: Documentation (README + docs scenario)

Add a SQLAlchemy/Alembic configuration section mirroring the FastAPI block,
including the explicit note that `--ignore-definitions-if-inherits-from` alone does
not silence model columns (both definition+body options required).

**Files**: `README.md`, `docs/unused-detection-and-ignoring.md`
**Key changes**:
- `README.md` after `:60`: toml + CLI block with
  `ignore-definitions-if-inherits-from = ["Base","db.Model"]`,
  `ignore-bodies-if-inherits-from = ["Base","db.Model"]`,
  `ignore-definitions-if-decorated-with = ["@event.*"]`,
  `ignore-names = ["upgrade","downgrade","revision","down_revision","branch_labels","depends_on"]`,
  `ignore-names-in-files = ["*/versions/*"]`, plus the columns note.
- `docs/unused-detection-and-ignoring.md` after the FastAPI scenario (`:90-97`):
  add SQLAlchemy and Alembic scenarios as CLI-flag examples.

**Verify**: `just check` passes (no markdown lint breakage if configured).
Inspect that the new README block contains the literal strings `db.Model`,
`ignore-bodies-if-inherits-from`, and `*/versions/*`
(`grep -n 'ignore-bodies-if-inherits-from' README.md` returns a hit;
`grep -n 'versions' docs/unused-detection-and-ignoring.md` returns a hit).

---

## Testing Checkpoints

- **After Phase 1**: `test_sqlalchemy.py` exists; 2.0 declarative models suppressed,
  unused helper still reported. `just test` green.
- **After Phase 2**: 1.x `Column` body assignments (DC01) suppressed by
  `--ignore-bodies-if-inherits-from`.
- **After Phase 3**: `@event.listens_for` handlers suppressed; no code change.
- **After Phase 4**: ONLY production change landed; `get_base_name` added,
  `get_inherits_from` captures `db.Model`; full suite green (no inheritance
  regression); `just check` green.
- **After Phase 5**: `test_alembic.py` exists; migration callbacks + revision ids
  suppressed via `ignore_names` and `*/versions/*`.
- **After Phase 6**: README + docs carry the SQLAlchemy/Alembic block with the
  "both options needed for columns" note.

End state: `just test` and `just check` both pass; each test emits its
genuinely-unused finding(s) alongside silenced framework code, proving
suppression is targeted, not blanket.
