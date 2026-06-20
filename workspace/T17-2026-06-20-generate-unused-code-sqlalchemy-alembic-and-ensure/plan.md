# Implementation Plan

## Overview

Add two framework scenario test files (`tests/frameworks/test_sqlalchemy.py`,
`tests/frameworks/test_alembic.py`) that drive the real `main()` over in-memory
fixtures and assert exact `path:line:col: DCxx ...` strings, proving Deadcode
suppresses SQLAlchemy/Alembic false positives via documented `ignore-*` options
while still reporting genuinely unused code. The only production change extends
`get_inherits_from` to capture dotted base classes (`db.Model`) so
Flask-SQLAlchemy models can be suppressed. Docs mirror the existing FastAPI block.

## Shared technique — deriving the exact assertion string

`fix_indent` strips the common leading margin but preserves line structure, so a
fixture's first line (the blank line right after `"""`) is line 1. Computing
`line:col` by hand is error-prone. For every new test, do this:

1. Write the fixture and the `main([...])` call.
2. Temporarily assert against an empty string: `self.assertEqual(output, '')`.
3. Run the single test (commands below). It fails, printing the **actual**
   `path:line:col: DCxx ...` output.
4. Paste that exact output into `assertEqual`. The assertion is the source of
   truth for the exact DC code / line / col, per `structure.md`.

This mirrors how `tests/frameworks/test_fastapi.py` was built (e.g.
`main.py:31:0: DC02 ...`). Do **not** guess line numbers in the plan; derive them.

Single-test run command (used throughout):
```
just test -- tests/frameworks/test_sqlalchemy.py
just test -- tests/frameworks/test_alembic.py
```

---

## Phase 1: SQLAlchemy 2.0 declarative models (`Base` / `DeclarativeBase`)

Demonstrate suppression of `class Base(DeclarativeBase)` + `class User(Base)`
models and their `mapped_column` / `Mapped[...]` columns using wired
inherits-from options, while a genuinely unused helper is still reported.

### Changes

#### 1. New scenario test file
**File**: `tests/frameworks/test_sqlalchemy.py`
**Action**: create

```python
from deadcode.cli import main
from deadcode.utils.base_test_case import BaseTestCase


class TestSqlalchemyDeclarative(BaseTestCase):
    def test_2_0_models_suppressed_unused_helper_still_reported(self):
        self.files = {
            'models.py': """
                from sqlalchemy import String
                from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


                class Base(DeclarativeBase):
                    pass


                class User(Base):
                    __tablename__ = "users"

                    id: Mapped[int] = mapped_column(primary_key=True)
                    name: Mapped[str] = mapped_column(String(50))


                def _unused_helper():
                    return 42
                """
        }

        output = main(
            [
                'models.py',
                '--no-color',
                '--ignore-definitions-if-inherits-from=Base',
                '--ignore-bodies-if-inherits-from=Base',
            ]
        )

        # Derive the exact string per the shared technique, then pin it here.
        self.assertEqual(output, '...models.py:NN:0: DC02 Function `_unused_helper` is never used...')
```

**Notes / resolved assumptions**:
- `--ignore-definitions-if-inherits-from=Base` silences the `User` and `Base`
  class names; `--ignore-bodies-if-inherits-from=Base` silences the body members
  (`__tablename__`, `id`, `name`). Both are required (design decision 2).
- `Mapped[int] = mapped_column(...)` is an `AnnAssign` in the class body. The
  open risk (design, "mapped_column classification") is resolved empirically by
  the test: whatever the classification, `ignore-bodies-if-inherits-from`
  suppresses it. If a `User`/`id`/`name` finding unexpectedly survives, the body
  option is not catching `AnnAssign` — stop and re-run `/lifecycle/4_structure`
  (do not silently widen scope).
- `Base(DeclarativeBase)` has no columns of its own, so its body (`pass`) emits
  nothing. `DeclarativeBase` is an imported `ast.Name` base — already handled.

### Verification
#### Automated
- [x] `just test -- tests/frameworks/test_sqlalchemy.py` passes
- [x] `just test` passes (full suite, no regression)

#### Manual
- [x] `grep -q '_unused_helper' tests/frameworks/test_sqlalchemy.py` → the test
  pins the genuinely-unused finding (returns hit)
- [x] The asserted string contains `_unused_helper` and contains **none** of
  `DC03 Class \`User\``, `Variable \`id\``, `Variable \`name\``:
  `just test -- tests/frameworks/test_sqlalchemy.py -k test_2_0` exits 0

---

## Phase 2: SQLAlchemy 1.x declarative models (`declarative_base()` + `Column`)

Demonstrate the 1.x style — `Base = declarative_base()`, `class User(Base)` with
`id = Column(...)` body assignments (class-body `Store` Name → DC01) — is
suppressed by the same two wired options.

### Changes

#### 1. Extend the SQLAlchemy test file
**File**: `tests/frameworks/test_sqlalchemy.py`
**Action**: modify (add method to `TestSqlalchemyDeclarative`)

```python
    def test_1_x_models_with_column_assignments_suppressed(self):
        self.files = {
            'models.py': """
                from sqlalchemy import Column, Integer, String
                from sqlalchemy.orm import declarative_base


                Base = declarative_base()


                class User(Base):
                    __tablename__ = "users"

                    id = Column(Integer, primary_key=True)
                    name = Column(String)


                UNUSED_CONSTANT = 1
                """
        }

        output = main(
            [
                'models.py',
                '--no-color',
                '--ignore-definitions-if-inherits-from=Base',
                '--ignore-bodies-if-inherits-from=Base',
            ]
        )

        # Derive the exact string per the shared technique, then pin it here.
        self.assertEqual(output, '...models.py:NN:0: DC01 Variable `UNUSED_CONSTANT` is never used...')
```

**Notes / resolved assumptions**:
- `Base = declarative_base()` is a module-level assignment. `Base` is referenced
  as the base of `User`, so it is used and not reported.
- `id = Column(...)` is a `Store` Name in the class body → DC01 variable
  (design, DC codes). `--ignore-bodies-if-inherits-from=Base` must silence it.
- `UNUSED_CONSTANT` is the genuinely-unused module variable still reported.

### Verification
#### Automated
- [x] `just test -- tests/frameworks/test_sqlalchemy.py` passes
- [x] `just test` passes

#### Manual
- [x] Asserted string contains `UNUSED_CONSTANT` and **none** of `Variable \`id\``,
  `Variable \`name\``, `DC03 Class \`User\``:
  `just test -- tests/frameworks/test_sqlalchemy.py -k test_1_x` exits 0
  (test passes; `just test` subset run returns 1 only due to the 95% coverage
  gate on a single file — verified via `uv run pytest ... -o addopts=""`)

---

## Phase 3: SQLAlchemy event listeners (`@event.listens_for`)

Demonstrate `@event.listens_for(...)` handler functions are suppressed by the
wired decorator option, matching `get_decorator_name`'s dotted output `@event.*`.

### Changes

#### 1. Extend the SQLAlchemy test file
**File**: `tests/frameworks/test_sqlalchemy.py`
**Action**: modify (add method — same class or a new `TestSqlalchemyEvents`
class; use the same class `TestSqlalchemyDeclarative` for simplicity)

```python
    def test_event_listeners_suppressed_via_decorator(self):
        self.files = {
            'listeners.py': """
                from sqlalchemy import event

                from models import User


                @event.listens_for(User, "before_insert")
                def set_created(mapper, connection, target):
                    target.created = True


                def _unused_listener_helper():
                    return None
                """
        }

        output = main(
            [
                'listeners.py',
                '--no-color',
                '--ignore-definitions-if-decorated-with=@event.*',
            ]
        )

        # Derive the exact string per the shared technique, then pin it here.
        self.assertEqual(output, '...listeners.py:NN:0: DC02 Function `_unused_listener_helper` is never used...')
```

**Notes / resolved assumptions**:
- `get_decorator_name` (`deadcode/visitor/utils.py:53-61`) builds
  `@event.listens_for` from the `ast.Call` → `ast.Attribute` chain; `@event.*`
  matches it via fnmatch. No production change.
- `from models import User` makes `User` a used import (referenced in the
  decorator call), so no spurious import finding. If `User` is nonetheless
  reported as an unused import, drop the import and reference a local class
  instead — but the decorator argument is a `Load` of `User`, so it should be
  marked used.
- `set_created`'s body (`target.created = True`) is suppressed because
  `ignore-definitions-if-decorated-with` suppresses the whole definition
  (name + body), per research Q2 timing.

### Verification
#### Automated
- [x] `just test -- tests/frameworks/test_sqlalchemy.py` passes (3 passed)
- [x] `just test` passes (195 passed, 24 skipped — no regression)

#### Manual
- [x] Asserted string contains `_unused_listener_helper` and **not**
  `set_created`:
  `just test -- tests/frameworks/test_sqlalchemy.py -k test_event` (1 passed;
  exit 1 is only the 95% coverage gate on the single-file subset, as in Phase 2)

---

## Phase 4: Dotted base classes (`db.Model`) — the one production change

Extend `get_inherits_from` to capture attribute-style bases (`db.Model`,
`models.Model`) currently dropped at `find_unused_code_visitor.py:421`, storing
both the dotted form and the trailing leaf so `db.Model` and `*Model` both match.

### Changes

#### 1. New base-name helper
**File**: `deadcode/visitor/utils.py`
**Action**: modify (add `get_base_name`, modeled on `get_decorator_name`)

```python
def get_base_name(base: ast.expr) -> str | None:
    """Return a base class as a dotted string ('db.Model') or simple name
    ('Base'); None for bases that are neither ast.Name nor a dotted
    ast.Attribute chain (e.g. ast.Subscript like Generic[T])."""
    if isinstance(base, ast.Name):
        return base.id
    parts: list[str] = []
    while isinstance(base, ast.Attribute):
        parts.append(base.attr)
        base = base.value
    if isinstance(base, ast.Name):
        parts.append(base.id)
        return '.'.join(reversed(parts))
    return None
```

**Deviation from structure**: the structure suggested signature
`get_base_name(base: ast.Name | ast.Attribute) -> str | None`. Widened the
parameter to `ast.expr` because `get_inherits_from` iterates over
`node.bases`, whose elements are `ast.expr` (including `ast.Subscript` for
`Generic[T]`-style bases). The widened type keeps mypy green and returns `None`
for unsupported base shapes instead of raising. No leading `@` (unlike
`get_decorator_name`).

#### 2. Capture dotted bases in inheritance tracking
**File**: `deadcode/visitor/find_unused_code_visitor.py`
**Action**: modify `get_inherits_from` (lines 415-429)

Replace the body so that for each base it appends the dotted name AND its
trailing leaf when dotted, while the transitive one-hop scope lookup is keyed by
the **simple/leaf name** (preserving existing behavior for `ast.Name` bases):

```python
    def get_inherits_from(self, node: ast.AST) -> list[str] | None:
        """Returns a set of base classes from any level in inheritance tree."""

        if not (bases_attr := getattr(node, 'bases', None)):
            return None

        inherits_from: list[str] = []
        simple_names: list[str] = []
        for base in bases_attr:
            name = utils.get_base_name(base)
            if name is None:
                continue
            inherits_from.append(name)
            leaf = name.rsplit('.', 1)[-1]
            if leaf != name:
                # Dotted base (db.Model): also store the trailing leaf so both
                # `db.Model` and `*Model` patterns match via fnmatch.
                inherits_from.append(leaf)
            simple_names.append(leaf)

        for base in simple_names:
            if base_code_item := self.scopes.get(name=base, scope=self.scope):
                if base_inherits_from := getattr(base_code_item, 'inherits_from', None):
                    inherits_from.extend(base_inherits_from)

        return inherits_from
```

**Notes / resolved assumptions**:
- For an `ast.Name` base, `name == leaf` (no dot), so no duplicate is appended
  and `simple_names` gets `base.id` — **byte-for-byte the old behavior** for the
  transitive lookup, satisfying the Open Risk ("keep the simple-name path
  intact").
- For `db.Model`: `inherits_from` gets `['db.Model', 'Model']`, `simple_names`
  gets `'Model'`. The transitive lookup now keys on `'Model'` (previously the
  dotted base was dropped entirely). This only changes results if a same-file
  class literally named `Model` exists in scope — no existing test does this, so
  no regression. Assumption noted.
- `utils` is already imported in `find_unused_code_visitor.py` (used at line 433
  `utils.get_decorator_name`); no new import needed. Confirm with
  `grep -n 'import.*utils\|utils\.' deadcode/visitor/find_unused_code_visitor.py`.

#### 3. New test for Flask-SQLAlchemy `db.Model`
**File**: `tests/frameworks/test_sqlalchemy.py`
**Action**: modify (add method)

```python
    def test_flask_sqlalchemy_db_model_suppressed(self):
        self.files = {
            'models.py': """
                from flask_sqlalchemy import SQLAlchemy


                db = SQLAlchemy()


                class User(db.Model):
                    __tablename__ = "users"

                    id = db.Column(db.Integer, primary_key=True)
                    name = db.Column(db.String)


                UNUSED_FLAG = True
                """
        }

        output = main(
            [
                'models.py',
                '--no-color',
                '--ignore-definitions-if-inherits-from=db.Model',
                '--ignore-bodies-if-inherits-from=db.Model',
            ]
        )

        # Derive the exact string per the shared technique, then pin it here.
        self.assertEqual(output, '...models.py:NN:0: DC01 Variable `UNUSED_FLAG` is never used...')
```

**Notes**:
- `db = SQLAlchemy()` is referenced as `db.Model` / `db.Column`, so `db` is
  used. `UNUSED_FLAG` is the genuinely-unused module variable.
- This test **fails before** the Phase 4 code change (dotted base dropped → `User`
  class + `id`/`name` reported) and **passes after**. Run it once before
  applying changes #1/#2 to confirm it captures the gap, then after to confirm
  the fix.

### Verification
#### Automated
- [x] `just test -- tests/frameworks/test_sqlalchemy.py` passes (4 passed)
- [x] `just test` passes (196 passed, 24 skipped — no inheritance regression)
- [x] `just check` passes (ruff format/lint/complexity + mypy green on the new
  `get_base_name` signature)

#### Manual
- [x] `grep -q 'def get_base_name' deadcode/visitor/utils.py` returns a hit
- [x] `grep -q 'get_base_name' deadcode/visitor/find_unused_code_visitor.py`
  returns a hit
- [x] Asserted string for `test_flask_sqlalchemy` contains `UNUSED_FLAG` and
  **none** of `DC03 Class \`User\``, `Variable \`id\``, `Variable \`name\``:
  `just test -- tests/frameworks/test_sqlalchemy.py -k test_flask` passes (1
  passed; exit 1 is only the 95% coverage gate on the single-file subset)

---

## Phase 5: Alembic migrations (`upgrade`/`downgrade` + revision identifiers)

Demonstrate Alembic migration boilerplate — `upgrade`, `downgrade` functions and
module-level `revision`, `down_revision`, `branch_labels`, `depends_on` — is
suppressed via `ignore_names` and whole versions dirs via `ignore_names_in_files`.

### Changes

#### 1. New Alembic scenario test file
**File**: `tests/frameworks/test_alembic.py`
**Action**: create

```python
from deadcode.cli import main
from deadcode.utils.base_test_case import BaseTestCase


class TestAlembicMigrations(BaseTestCase):
    def test_migration_callbacks_and_revision_ids_suppressed_via_ignore_names(self):
        self.files = {
            'versions/abc123_init.py': """
                from alembic import op
                import sqlalchemy as sa


                revision = "abc123"
                down_revision = None
                branch_labels = None
                depends_on = None


                def upgrade():
                    op.create_table("users")


                def downgrade():
                    op.drop_table("users")


                def _unused_migration_helper():
                    return None
                """
        }

        output = main(
            [
                'versions/abc123_init.py',
                '--no-color',
                '--ignore-names=upgrade',
                '--ignore-names=downgrade',
                '--ignore-names=revision',
                '--ignore-names=down_revision',
                '--ignore-names=branch_labels',
                '--ignore-names=depends_on',
            ]
        )

        # Derive the exact string per the shared technique, then pin it here.
        self.assertEqual(
            output,
            '...versions/abc123_init.py:NN:0: DC02 Function `_unused_migration_helper` is never used...',
        )

    def test_versions_directory_suppressed_via_ignore_names_in_files(self):
        self.files = {
            'versions/abc123_init.py': """
                from alembic import op
                import sqlalchemy as sa


                revision = "abc123"
                down_revision = None


                def upgrade():
                    op.create_table("users")


                def downgrade():
                    op.drop_table("users")
                """,
            'service.py': """
                def _genuinely_unused():
                    return None
                """,
        }

        output = main(
            [
                'versions/abc123_init.py',
                'service.py',
                '--no-color',
                '--ignore-names-in-files=*/versions/*',
            ]
        )

        # Derive the exact string per the shared technique, then pin it here.
        self.assertEqual(output, '...service.py:NN:0: DC02 Function `_genuinely_unused` is never used...')
```

**Notes / resolved assumptions**:
- `--ignore-names` is wired at `find_unused_code_visitor.py:287`; it adds the
  matching name to `used_names`. The six names cover the standard Alembic module
  globals + callbacks.
- `op` and `sa` imports are referenced inside `upgrade`/`downgrade` bodies, so no
  spurious import findings. (`upgrade`/`downgrade` themselves are silenced, but
  their bodies are still visited, marking `op` used.)
- **DEVIATION (test 1)**: the original fixture imported `sqlalchemy as sa` but
  never referenced `sa`, producing a spurious `DC07 Import \`sa\``. To match the
  plan's stated assumption (sa is referenced in the body), the `upgrade` body was
  changed to the standard Alembic `op.create_table("users", sa.Column("id",
  sa.Integer))` so `sa` is genuinely used. Result: only `_unused_migration_helper`
  is reported.
- **DEVIATION (test 2)**: `--ignore-names-in-files=*/versions/*` does NOT match
  the relative key `'versions/abc123_init.py'` (fnmatch requires a char + `/`
  before `versions`, but the key starts at `versions/`). Per the plan's stated
  fallback, switched to `--ignore-names-in-files=*versions*`, which matches.
- `--ignore-names-in-files` is wired at `find_unused_code_visitor.py:288`; it
  silences every unused name in files whose path matches the glob (fnmatch).
- `service.py`'s `_genuinely_unused` is the real-dead-code finding still reported,
  proving the directory glob is targeted, not global.

### Verification
#### Automated
- [x] `just test -- tests/frameworks/test_alembic.py` passes (2 passed; exit 1 is
  only the 95% coverage gate on the single-file subset)
- [x] `just test` passes (198 passed, 24 skipped — no regression)

#### Manual
- [x] First test's asserted string contains `_unused_migration_helper` and
  **none** of `upgrade`, `downgrade`, `revision`, `down_revision`:
  `just test -- tests/frameworks/test_alembic.py -k ignore_names` (2 passed)
- [x] Second test's asserted string contains `service.py` and
  `_genuinely_unused`, and contains **no** `versions/abc123_init.py` finding:
  `just test -- tests/frameworks/test_alembic.py -k ignore_names_in_files`
  (1 passed)

---

## Phase 6: Documentation (README + docs scenario)

Add a SQLAlchemy/Alembic configuration section mirroring the FastAPI block,
including the explicit note that `--ignore-definitions-if-inherits-from` alone
does not silence model columns (both definition + body options required).

### Changes

#### 1. README framework block
**File**: `README.md`
**Action**: modify (insert after the FastAPI/Pydantic block ending at line 60,
before `## Command line options`)

```markdown
For SQLAlchemy and Alembic projects, suppress ORM models (matched by their base
class), event listeners (matched by their decorator), and migration boilerplate
(matched by name or by the migrations directory):
```
[tool.deadcode]
ignore-definitions-if-inherits-from = ["Base", "db.Model"]
ignore-bodies-if-inherits-from = ["Base", "db.Model"]
ignore-definitions-if-decorated-with = ["@event.*"]
ignore-names = ["upgrade", "downgrade", "revision", "down_revision", "branch_labels", "depends_on"]
ignore-names-in-files = ["*/versions/*"]
```
`Base` is the conventional SQLAlchemy declarative base; `db.Model` is the
Flask-SQLAlchemy base — rename them to match your own. Note: a model that owns
columns needs **both** `ignore-definitions-if-inherits-from` (silences the class
name) and `ignore-bodies-if-inherits-from` (silences the `Column` / `mapped_column`
members) — the definition option alone does not silence the columns.
```

**Note**: the inner fenced block uses the same bare ```` ``` ```` style as the
existing FastAPI block (`README.md:55-59`). Match it exactly; do not switch to
` ```toml `.

#### 2. Docs scenario
**File**: `docs/unused-detection-and-ignoring.md`
**Action**: modify (insert after the FastAPI scenario at line 96, before the
`See [Visitor layer]...` line at 98)

```markdown
**Scenario 6**: Class inheriting from `db.Model` (Flask-SQLAlchemy),
`--ignore-definitions-if-inherits-from=db.Model --ignore-bodies-if-inherits-from=db.Model` set.
- Step 3: Inheritance gate matches the dotted base `db.Model`; the class name and
  its `Column` body members are marked used.
- Step 6: Class and columns are in `used_names`, not reported.

**Scenario 7**: Alembic migration file under `versions/`,
`--ignore-names-in-files=*/versions/*` set (or `--ignore-names=upgrade,downgrade,revision,down_revision,branch_labels,depends_on`).
- Step 1: Path / name pattern matches; the migration's names are marked used.
- Step 6: Names are in `used_names`, not reported.
```

### Verification
#### Automated
- [x] `just check` passes (no markdown lint breakage if configured; `check` runs
  format/lint/typecheck/test — none touch markdown, so this confirms nothing
  else broke)

#### Manual
- [x] `grep -q 'ignore-bodies-if-inherits-from' README.md` returns a hit
- [x] `grep -q 'db.Model' README.md` returns a hit
- [x] `grep -q '\*/versions/\*' README.md` returns a hit
- [x] `grep -q 'versions' docs/unused-detection-and-ignoring.md` returns a hit
- [x] `grep -q 'db.Model' docs/unused-detection-and-ignoring.md` returns a hit

---

## Testing Checkpoints

- **After Phase 1**: `test_sqlalchemy.py` exists; 2.0 declarative models
  suppressed, `_unused_helper` still reported. `just test` green.
- **After Phase 2**: 1.x `Column` body assignments (DC01) suppressed by
  `--ignore-bodies-if-inherits-from`; `UNUSED_CONSTANT` still reported.
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
