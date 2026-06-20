# Structure Outline

## Approach

Author a single new `tests/frameworks/test_django.py` containing one
`BaseTestCase` subclass per Django subject area. Each subclass seeds an in-memory
`self.files` fixture, runs `main([...])` with `--no-color` plus the minimal
**functional** ignore flags a real Django project would set (the four active
options only — never the six inert ones), and asserts the exact output string.
Every test pairs a suppressed framework construct with one deliberately-planted
genuinely-unused symbol (`_unused_helper` / `UNUSED_CONSTANT`) that *must* still
be reported with the correct `DCxx` code, 1-based line, 0-based column. No engine
changes unless a pattern proves unsuppressible (escalate per design Open Risks).

**Each phase is a vertical slice**: it owns its fixture (source layer), its CLI
ignore flags (config/API layer), and its exact-string assertion (verification
layer). A phase = a self-contained `Test...` class that passes on its own.

**Calibration protocol (applies to every phase):** write the fixture, run the
phase once *without* the final assertion string (or with a deliberately wrong
one), read the observed `file:line:col: DCxx ...` from the failure, paste it
verbatim into `assertEqual`. Columns are 0-based from `ast.col_offset`; lines are
1-based. Re-run to confirm green. This neutralizes the line/column-exactness risk.

**Common run command:** `just test tests/frameworks/test_django.py` (whole file)
or `just test tests/frameworks/test_django.py -k TestDjangoModels` (one phase).
Final gate: `just check`.

---

## Phase 1: Scaffold + Models

Create the test module with the standard two-line import header and the first
working slice: Django models suppressed via the inherits-from option pair, with a
module-level unused helper still reported. Establishes the file all later phases
extend.

**Files**: `tests/frameworks/test_django.py` (new). `tests/frameworks/__init__.py`
already exists.

**Key changes**:
- `from deadcode.cli import main`, `from deadcode.utils.base_test_case import BaseTestCase`
- `class TestDjangoModels(BaseTestCase)` — new
- `def test_models_suppressed_unused_helper_still_reported(self)` — fixture
  `models.py` with `class Article(models.Model)` (fields `title`, `body`) plus a
  module-level `def _unused_helper()`.
- Flags: `--ignore-definitions-if-inherits-from=models.Model`,
  `--ignore-bodies-if-inherits-from=models.Model` (leaf-match also covers bare
  `Model`).

**Verify**: `just test tests/frameworks/test_django.py -k TestDjangoModels`
passes; assertion is the single line
`models.py:<L>:0: DC02 Function \`_unused_helper\` is never used` (exact `<L>`
from calibration run) and the model class/fields are absent from output.

---

## Phase 2: Views + URLconf

Demonstrate real cross-file reference resolution: function views referenced as
`views.x` in a `urls.py` are marked used (no flag needed); a class-based view is
suppressed via inherits-from; `urlpatterns` is suppressed by name; one genuinely
unused view function is still reported.

**Files**: `tests/frameworks/test_django.py` (extend).

**Key changes**:
- `class TestDjangoViews(BaseTestCase)` — new
- `def test_function_views_referenced_in_urlconf_used_unused_view_reported(self)`
  — two-file fixture: `views.py` (defines `index`, `detail`, and unused
  `_orphan_view`) + `urls.py` (`urlpatterns = [path("", views.index), ...]`).
  Flag: `--ignore-names=urlpatterns`. Asserts only `_orphan_view` (DC02) reported.
- `def test_class_based_view_suppressed_via_inherits_from(self)` — fixture with
  `class ArticleList(ListView)` (body `model`, `template_name`) + a planted
  `UNUSED_CONSTANT`. Flags:
  `--ignore-definitions-if-inherits-from=ListView`,
  `--ignore-bodies-if-inherits-from=ListView`. Asserts `UNUSED_CONSTANT` (DC01).

**Verify**: `just test tests/frameworks/test_django.py -k TestDjangoViews`
passes; first test's output is exactly the `_orphan_view` DC02 line (proving
`views.index`/`views.detail` were resolved as uses and `urlpatterns` suppressed);
second test's output is exactly the `UNUSED_CONSTANT` DC01 line.

---

## Phase 3: Admin + Signals (decorator suppression)

Cover the two decorator-driven Django registration styles. Admin via
`@admin.register(...)` decorator and via `admin.ModelAdmin` inheritance; signals
via `@receiver(...)`. Each keeps one planted unused helper reported.

**Files**: `tests/frameworks/test_django.py` (extend).

**Key changes**:
- `class TestDjangoAdmin(BaseTestCase)` — new
  - `def test_admin_register_decorator_suppressed(self)` — `@admin.register(Article)`
    on `class ArticleAdmin` + unused helper. Flag:
    `--ignore-definitions-if-decorated-with=@admin.register*`.
  - `def test_modeladmin_inherits_from_suppressed(self)` —
    `class ArticleAdmin(admin.ModelAdmin)` + planted unused. Flags:
    `--ignore-definitions-if-inherits-from=admin.ModelAdmin`,
    `--ignore-bodies-if-inherits-from=admin.ModelAdmin`.
- `class TestDjangoSignals(BaseTestCase)` — new
  - `def test_receiver_decorator_suppressed(self)` — `@receiver(post_save, ...)`
    on a handler + unused helper. Flag:
    `--ignore-definitions-if-decorated-with=@receiver*` (leaf-match also covers
    `@signals.receiver`).

**Verify**: `just test tests/frameworks/test_django.py -k "TestDjangoAdmin or TestDjangoSignals"`
passes; each test's output is exactly its planted unused symbol's DCxx line and
the admin class / signal handler are absent.

---

## Phase 4: Management Commands + App Configs (inherits + body pair)

Cover classes whose required method/attribute bodies (`handle`, `add_arguments`,
`ready`, `name`, `default_auto_field`) must be suppressed alongside the class
name. Each uses the inherits-from definition+body option pair.

**Files**: `tests/frameworks/test_django.py` (extend).

**Key changes**:
- `class TestDjangoManagementCommands(BaseTestCase)` — new
  - `def test_basecommand_suppressed_unused_helper_reported(self)` —
    `class Command(BaseCommand)` with `handle`/`add_arguments` methods + a
    module-level `def _unused_helper()`. Flags:
    `--ignore-definitions-if-inherits-from=BaseCommand`,
    `--ignore-bodies-if-inherits-from=BaseCommand`.
- `class TestDjangoAppConfigs(BaseTestCase)` — new
  - `def test_appconfig_suppressed_unused_constant_reported(self)` —
    `class BlogConfig(AppConfig)` with `name`, `default_auto_field`, `ready()` +
    a planted `UNUSED_CONSTANT`. Flags:
    `--ignore-definitions-if-inherits-from=AppConfig`,
    `--ignore-bodies-if-inherits-from=AppConfig`.

**Verify**: `just test tests/frameworks/test_django.py -k "TestDjangoManagementCommands or TestDjangoAppConfigs"`
passes; output for each is exactly the planted unused symbol's line. Manual
check on the body-depth risk: confirm no `handle`/`add_arguments`/`ready` DC04
method lines appear in the output string (assertEqual on the full string already
enforces this — any leak fails the test).

---

## Phase 5: Settings (path-based suppression)

Settings modules are walls of UPPERCASE constants Django reads dynamically;
suppress the whole file by path glob rather than per-name, mirroring Alembic's
`*versions*` precedent. Pair with a second non-settings file holding a genuinely
unused symbol to prove the glob is scoped, not blanket.

**Files**: `tests/frameworks/test_django.py` (extend).

**Key changes**:
- `class TestDjangoSettings(BaseTestCase)` — new
  - `def test_settings_constants_suppressed_via_ignore_names_in_files(self)` —
    two-file fixture: `settings.py` (`DEBUG`, `INSTALLED_APPS`, `SECRET_KEY`, ...)
    + `service.py` (`def _genuinely_unused()`). Flag:
    `--ignore-names-in-files=*settings*`. Asserts only the `service.py`
    `_genuinely_unused` DC02 line.

**Verify**: `just test tests/frameworks/test_django.py -k TestDjangoSettings`
passes; output is exactly `service.py:<L>:0: DC02 Function \`_genuinely_unused\``
— confirming every `settings.py` constant was suppressed and the other file was
untouched.

---

## Phase 6: Full-suite + style gate

No new behavior — final integration verification across all phases.

**Files**: none (verification only).

**Verify**: `just test tests/frameworks/test_django.py` runs the entire new
module green; then `just check` (format + lint + complexity + typecheck + full
test suite) passes with no regressions. Confirm `test_django.py` was collected by
checking the test runner reports a non-zero count for the file.

---

## Testing Checkpoints

After each phase the following should hold (useful for resume after context
reset):

- **P1 done:** `test_django.py` exists; `TestDjangoModels` green; model fields
  suppressed, `_unused_helper` (DC02) reported.
- **P2 done:** `TestDjangoViews` green; function views resolved via `views.x` in
  `urls.py`, `urlpatterns` suppressed by name, CBV suppressed by inheritance, one
  orphan view + one constant still reported.
- **P3 done:** `TestDjangoAdmin` + `TestDjangoSignals` green; both admin
  registration styles and `@receiver` handlers suppressed; planted unused symbols
  reported.
- **P4 done:** `TestDjangoManagementCommands` + `TestDjangoAppConfigs` green;
  `handle`/`add_arguments`/`ready` bodies suppressed with no DC04 method leaks.
- **P5 done:** `TestDjangoSettings` green; whole settings file suppressed by path
  glob, second-file unused symbol still reported.
- **P6 done:** whole file green under `just test`; `just check` clean.

**Escalation note:** if any single Django construct (most likely a signal handler
or `urlpatterns` edge case) proves unsuppressible by the four functional options
without resorting to an inert option, stop and document it rather than forcing a
brittle config — that is the one case justifying an engine change, and warrants
re-running `/lifecycle/3_design`.
