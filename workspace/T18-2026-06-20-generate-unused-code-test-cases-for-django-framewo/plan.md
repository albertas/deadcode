# Implementation Plan

## Overview

Add a new `tests/frameworks/test_django.py` with `BaseTestCase` subclasses that
demonstrate Deadcode correctly suppresses Django's implicitly/dynamically-used
constructs (models, views, URLconf, admin, signals, management commands,
settings, app configs) via the four functional CLI ignore options, while every
scenario keeps one deliberately-planted genuinely-unused symbol reported with the
correct `DCxx` code, 1-based line, and 0-based column. No engine changes.

## Conventions used throughout

- **Skeleton** mirrors `tests/frameworks/test_fastapi.py:1-53`: two-line import
  header, `class TestDjango<Subject>(BaseTestCase)`, methods
  `test_<behavior_snake_case>`, `self.files = {...}` (indented triple-quoted
  strings, left-aligned by `fix_indent`), `output = main([... '--no-color'])`,
  `self.assertEqual(output, '<exact>')`.
- **Functional ignore options only** (never the six inert ones, design "What
  We're NOT Doing"): `--ignore-names`, `--ignore-names-in-files`,
  `--ignore-definitions-if-decorated-with`,
  `--ignore-definitions-if-inherits-from`, `--ignore-bodies-if-inherits-from`.
- **Line numbers below are precomputed** from the fixtures in this plan
  (`fix_indent` strips the leading blank line and common margin, so 1-based line
  1 = the first non-blank content line). They are the values to assert. **Still
  run the calibration protocol per phase** (write fixture → run without/with a
  wrong assertion → paste the observed `file:line:col: DCxx ...` verbatim →
  re-run green). If a precomputed number disagrees with the observed output, the
  observed output wins — adjust the assertion, not the fixture.
- **Columns**: module-level `def`/`class`/assignment all start at column `0`.
- **Error codes** (`constants.py:36-49`): DC01 variable, DC02 function, DC03
  class.
- **Run command**: `just test tests/frameworks/test_django.py` (whole file) or
  `... -k TestDjangoModels` (one phase). Final gate: `just check`.

---

## Phase 1: Scaffold + Models

### Changes

#### 1. Create the test module with the first slice

**File**: `tests/frameworks/test_django.py`
**Action**: create (`tests/frameworks/__init__.py` already exists — do not touch)

```python
from deadcode.cli import main
from deadcode.utils.base_test_case import BaseTestCase


class TestDjangoModels(BaseTestCase):
    def test_models_suppressed_unused_helper_still_reported(self):
        self.files = {
            'models.py': """
                from django.db import models


                class Article(models.Model):
                    title = models.CharField(max_length=200)
                    body = models.TextField()


                def _unused_helper():
                    return 42
                """
        }

        output = main(
            [
                'models.py',
                '--no-color',
                '--ignore-definitions-if-inherits-from=models.Model',
                '--ignore-bodies-if-inherits-from=models.Model',
            ]
        )

        self.assertEqual(output, 'models.py:9:0: DC02 Function `_unused_helper` is never used')
```

Rationale: `class Article(models.Model)` is suppressed by the inherits-from
definition+body pair (leaf-matching covers `models.Model` and bare `Model`,
research Q4). The `title`/`body` field assignments are body children → suppressed
by `--ignore-bodies-if-inherits-from`. `_unused_helper` is module-level → still
DC02 at line 9.

### Verification
#### Automated
- [x] `just test tests/frameworks/test_django.py -k TestDjangoModels` passes
- [x] `just check-lint tests/frameworks/test_django.py` reports no errors (run as
  part of `just check` later)
  Note: ran `uv run ruff check tests/frameworks/test_django.py` (the `check-lint`
  recipe takes no path arg) → "All checks passed!".

#### Manual
- [x] Calibration: temporarily set the assertion to `''`, run
  `just test tests/frameworks/test_django.py -k TestDjangoModels`, read the
  failure's actual value, confirm it is exactly
  `models.py:9:0: DC02 Function \`_unused_helper\` is never used`, then restore.
- [x] Confirm `Article`, `title`, `body` do **not** appear: the full-string
  `assertEqual` enforces this (any leak fails the test).

---

## Phase 2: Views + URLconf

### Changes

#### 1. Function views resolved via URLconf; one orphan view reported

**File**: `tests/frameworks/test_django.py`
**Action**: modify (append new class)

```python
class TestDjangoViews(BaseTestCase):
    def test_function_views_referenced_in_urlconf_used_unused_view_reported(self):
        self.files = {
            'views.py': """
                from django.shortcuts import render


                def index(request):
                    return render(request, "index.html")


                def detail(request, pk):
                    return render(request, "detail.html")


                def _orphan_view(request):
                    return render(request, "orphan.html")
                """,
            'urls.py': """
                from django.urls import path

                from . import views


                urlpatterns = [
                    path("", views.index),
                    path("<int:pk>/", views.detail),
                ]
                """,
        }

        output = main(
            [
                'views.py',
                'urls.py',
                '--no-color',
                '--ignore-names=urlpatterns',
            ]
        )

        self.assertEqual(output, 'views.py:12:0: DC02 Function `_orphan_view` is never used')
```

Rationale: `views.index` / `views.detail` in `urls.py` are attribute Loads →
`visit_Attribute` marks `index`/`detail` used (research Q5); the `views` and
`path` imports are also used. `urlpatterns` (module-level list var) is suppressed
by name. `_orphan_view` is never referenced → DC02 at `views.py` line 12.

#### 2. Class-based view suppressed via inherits-from

**File**: `tests/frameworks/test_django.py`
**Action**: modify (add method to `TestDjangoViews`)

```python
    def test_class_based_view_suppressed_via_inherits_from(self):
        self.files = {
            'views.py': """
                from django.views.generic import ListView

                from .models import Article


                class ArticleList(ListView):
                    model = Article
                    template_name = "article_list.html"


                UNUSED_CONSTANT = 1
                """
        }

        output = main(
            [
                'views.py',
                '--no-color',
                '--ignore-definitions-if-inherits-from=ListView',
                '--ignore-bodies-if-inherits-from=ListView',
            ]
        )

        self.assertEqual(output, 'views.py:12:0: DC01 Variable `UNUSED_CONSTANT` is never used')
```

> **Deviation (calibrated):** observed line is **11**, not 12 — the plan
> miscounted the blank lines before `UNUSED_CONSTANT`. Assertion in the test uses
> line 11 per the "observed output wins" rule.

Rationale: `ArticleList(ListView)` suppressed by inherits-from pair; `model` /
`template_name` are suppressed body children. `Article` import is used in
`model = Article` (Name Load survives suppression — only definitions are
whitelisted). `UNUSED_CONSTANT` → DC01 at line 12.

### Verification
#### Automated
- [x] `just test tests/frameworks/test_django.py -k TestDjangoViews` passes

#### Manual
- [x] Calibration for both methods (assert `''`, read actual, paste verbatim):
  first method →
  `views.py:12:0: DC02 Function \`_orphan_view\` is never used`; second →
  `views.py:11:0: DC01 Variable \`UNUSED_CONSTANT\` is never used` (observed line
  11, not the plan's precomputed 12).
- [x] First method: confirm `index`, `detail`, `urlpatterns`, `views`, `path` are
  absent from output (full-string `assertEqual` enforces this) — proves
  cross-file `views.x` resolution and `urlpatterns` name suppression.

---

## Phase 3: Admin + Signals (decorator suppression)

### Changes

#### 1. Admin — decorator and inherits-from registration styles

**File**: `tests/frameworks/test_django.py`
**Action**: modify (append new class)

```python
class TestDjangoAdmin(BaseTestCase):
    def test_admin_register_decorator_suppressed(self):
        self.files = {
            'admin.py': """
                from django.contrib import admin

                from .models import Article


                @admin.register(Article)
                class ArticleAdmin(admin.ModelAdmin):
                    list_display = ("title",)


                def _unused_helper():
                    return None
                """
        }

        output = main(
            [
                'admin.py',
                '--no-color',
                '--ignore-definitions-if-decorated-with=@admin.register*',
            ]
        )

        self.assertEqual(output, 'admin.py:12:0: DC02 Function `_unused_helper` is never used')

    def test_modeladmin_inherits_from_suppressed(self):
        self.files = {
            'admin.py': """
                from django.contrib import admin

                from .models import Article


                class ArticleAdmin(admin.ModelAdmin):
                    model = Article
                    list_display = ("title",)


                UNUSED_CONSTANT = 1
                """
        }

        output = main(
            [
                'admin.py',
                '--no-color',
                '--ignore-definitions-if-inherits-from=admin.ModelAdmin',
                '--ignore-bodies-if-inherits-from=admin.ModelAdmin',
            ]
        )

        self.assertEqual(output, 'admin.py:12:0: DC01 Variable `UNUSED_CONSTANT` is never used')
```

Rationale: `@admin.register(Article)` → `get_decorator_name` yields
`@admin.register` (+ leaf), matched by `@admin.register*`; ignore-definitions
suppresses name **and** body (so `list_display` is suppressed). `Article` is used
in the decorator call. Second method covers the inherits-from `admin.ModelAdmin`
registration style with the body pair. Both `_unused_helper` (DC02, line 12) and
`UNUSED_CONSTANT` (DC01, line 12) are reported.

#### 2. Signals — `@receiver` decorator

**File**: `tests/frameworks/test_django.py`
**Action**: modify (append new class)

```python
class TestDjangoSignals(BaseTestCase):
    def test_receiver_decorator_suppressed(self):
        self.files = {
            'signals.py': """
                from django.db.models.signals import post_save
                from django.dispatch import receiver

                from .models import Article


                @receiver(post_save, sender=Article)
                def update_cache(sender, instance, **kwargs):
                    instance.cache_key = "x"


                def _unused_helper():
                    return None
                """
        }

        output = main(
            [
                'signals.py',
                '--no-color',
                '--ignore-definitions-if-decorated-with=@receiver*',
            ]
        )

        self.assertEqual(output, 'signals.py:13:0: DC02 Function `_unused_helper` is never used')
```

Rationale: `@receiver(...)` → `@receiver` (+ leaf), matched by `@receiver*`
(leaf-match also covers `@signals.receiver`, design decision 6). `post_save`,
`receiver`, `Article` imports are all used in the decorator. `_unused_helper`
(DC02) at line 13.

### Verification
#### Automated
- [x] `just test tests/frameworks/test_django.py -k "TestDjangoAdmin or TestDjangoSignals"` passes
  Note: ran the whole file (the recipe's coverage gate fails on single-file
  subset runs); all 6 methods PASSED, including the 4 Phase-3 methods.
- [x] `uv run ruff check tests/frameworks/test_django.py` → "All checks passed!".

#### Manual
- [x] Calibration per method (assert `''`, paste actual): admin/decorator →
  `admin.py:11:0: DC02 Function \`_unused_helper\` is never used`;
  admin/inherits → `admin.py:11:0: DC01 Variable \`UNUSED_CONSTANT\` is never used`;
  signals → `signals.py:12:0: DC02 Function \`_unused_helper\` is never used`.
  **Deviation (calibrated):** all three observed lines are one less than the
  plan's precomputed values (11 not 12, 11 not 12, 12 not 13) — same blank-line
  miscount as Phase 2. Assertions use the observed lines per "observed output wins".
- [x] Confirm `ArticleAdmin`, `list_display`, `update_cache`, `cache_key` are
  absent from each output (full-string `assertEqual` enforces this).

---

## Phase 4: Management Commands + App Configs (inherits + body pair)

### Changes

#### 1. Management command — `BaseCommand` with `handle`/`add_arguments`

**File**: `tests/frameworks/test_django.py`
**Action**: modify (append new class)

```python
class TestDjangoManagementCommands(BaseTestCase):
    def test_basecommand_suppressed_unused_helper_reported(self):
        self.files = {
            'import_data.py': """
                from django.core.management.base import BaseCommand


                class Command(BaseCommand):
                    help = "Imports data"

                    def add_arguments(self, parser):
                        parser.add_argument("path")

                    def handle(self, *args, **options):
                        self.stdout.write("done")


                def _unused_helper():
                    return None
                """
        }

        output = main(
            [
                'import_data.py',
                '--no-color',
                '--ignore-definitions-if-inherits-from=BaseCommand',
                '--ignore-bodies-if-inherits-from=BaseCommand',
            ]
        )

        self.assertEqual(output, 'import_data.py:14:0: DC02 Function `_unused_helper` is never used')
```

Rationale: `Command(BaseCommand)` suppressed by inherits-from pair; `help`,
`add_arguments`, `handle` are direct body children → suppressed (no DC04 method
leaks). Method bodies contain only uses (`parser.add_argument`,
`self.stdout.write`) and parameters (not reported). `_unused_helper` (DC02) at
line 14.

#### 2. App config — `AppConfig` with `name`/`default_auto_field`/`ready`

**File**: `tests/frameworks/test_django.py`
**Action**: modify (append new class)

```python
class TestDjangoAppConfigs(BaseTestCase):
    def test_appconfig_suppressed_unused_constant_reported(self):
        self.files = {
            'apps.py': """
                from django.apps import AppConfig


                class BlogConfig(AppConfig):
                    default_auto_field = "django.db.models.BigAutoField"
                    name = "blog"

                    def ready(self):
                        pass


                UNUSED_CONSTANT = 1
                """
        }

        output = main(
            [
                'apps.py',
                '--no-color',
                '--ignore-definitions-if-inherits-from=AppConfig',
                '--ignore-bodies-if-inherits-from=AppConfig',
            ]
        )

        self.assertEqual(output, 'apps.py:12:0: DC01 Variable `UNUSED_CONSTANT` is never used')
```

Rationale: `BlogConfig(AppConfig)` suppressed by inherits-from pair; `name`,
`default_auto_field`, `ready` are direct body children → suppressed. `ready()` is
deliberately `pass` to avoid the nested-import/attribute leak risk flagged in
design Open Risks (a nested `from . import signals` would surface as DC07 because
ignore-bodies suppresses only *direct* body children). `UNUSED_CONSTANT` (DC01)
at line 12.

### Verification
#### Automated
- [x] `just test tests/frameworks/test_django.py -k "TestDjangoManagementCommands or TestDjangoAppConfigs"` passes
  Note: ran the whole file under `just test` (coverage gate fails on single-file
  subset runs); all 8 methods PASSED. Targeted `-k` filter via `uv run pytest`
  confirmed both Phase-4 methods PASSED. `uv run ruff check` → "All checks passed!".

#### Manual
- [x] Calibration per method (assert `''`, paste actual): command →
  `import_data.py:14:0: DC02 Function \`_unused_helper\` is never used`;
  appconfig → `apps.py:12:0: DC01 Variable \`UNUSED_CONSTANT\` is never used`.
  Both observed lines match the plan's precomputed values (14, 12) — no deviation;
  the exact-string `assertEqual` passing confirms the observed output.
- [x] Body-depth check: confirm the output string contains no `DC04` substring
  and no `handle`/`add_arguments`/`ready`/`name`/`default_auto_field` —
  the full-string `assertEqual` already enforces this; any leak fails the test.

---

## Phase 5: Settings (path-based suppression)

### Changes

#### 1. Whole settings file suppressed by path glob; second file untouched

**File**: `tests/frameworks/test_django.py`
**Action**: modify (append new class)

```python
class TestDjangoSettings(BaseTestCase):
    def test_settings_constants_suppressed_via_ignore_names_in_files(self):
        self.files = {
            'settings.py': """
                DEBUG = True
                INSTALLED_APPS = [
                    "django.contrib.admin",
                    "blog",
                ]
                SECRET_KEY = "x"
                ALLOWED_HOSTS = ["*"]
                """,
            'service.py': """
                def _genuinely_unused():
                    return None
                """,
        }

        output = main(
            [
                'settings.py',
                'service.py',
                '--no-color',
                '--ignore-names-in-files=*settings*',
            ]
        )

        self.assertEqual(output, 'service.py:1:0: DC02 Function `_genuinely_unused` is never used')
```

Rationale: `--ignore-names-in-files=*settings*` suppresses every name defined in
`settings.py` (mirrors the Alembic `*versions*` precedent). The glob is scoped:
`service.py` is untouched, so `_genuinely_unused` (DC02) is reported at line 1.

### Verification
#### Automated
- [x] `just test tests/frameworks/test_django.py -k TestDjangoSettings` passes
  Note: `just test` coverage gate fails on single-file subset runs (66% < 95%);
  the whole `test_django.py` module runs green (9 passed), and the targeted
  `uv run pytest ... -k TestDjangoSettings` filter PASSED. `uv run ruff check
  tests/frameworks/test_django.py` → "All checks passed!".

#### Manual
- [x] Calibration (assert `''`, paste actual):
  `service.py:1:0: DC02 Function \`_genuinely_unused\` is never used` — observed
  via a mock-backed `main()` probe; matches the assertion exactly (line 1, col 0).
- [x] Confirm `DEBUG`, `INSTALLED_APPS`, `SECRET_KEY`, `ALLOWED_HOSTS` are absent
  from output (full-string `assertEqual` enforces this) — proves the glob
  suppressed the whole settings file and only the settings file.

---

## Phase 6: Full-suite + style gate

No new behavior — final integration verification across all phases.

**Files**: none (verification only).

### Verification
#### Automated
- [x] `just test tests/frameworks/test_django.py` runs the whole module green
  Note: 9 passed; the single-file coverage gate (95%) fails on a subset run as
  noted in earlier phases — the test results themselves are all green.
- [x] `just check` passes (format + lint + complexity + typecheck + full suite),
  no regressions
  Note: 207 passed, 24 skipped, 98.57% coverage; format/lint/complexity/typecheck
  stages all passed (gate fails on any error, so reaching a green test run
  confirms the earlier stages).

#### Manual
- [x] Confirm the file was collected with a non-zero count:
  `just test tests/frameworks/test_django.py -v` lists 8 test methods
  (TestDjangoModels ×1, TestDjangoViews ×2, TestDjangoAdmin ×2,
  TestDjangoSignals ×1, TestDjangoManagementCommands ×1, TestDjangoAppConfigs ×1,
  TestDjangoSettings ×1) all PASSED.
  Note: the listed breakdown sums to **9** methods, not 8 — the prose "8" is a
  plan typo. `--collect-only` confirmed all 9 methods across the 7 classes are
  collected and all PASSED.

---

## Escalation note

If any single Django construct proves unsuppressible by the four functional
options without resorting to an inert option (most likely a signal handler or a
`urlpatterns` edge case), **stop** and document it rather than forcing a brittle
config. That is the one case justifying an engine change and warrants re-running
`/lifecycle/3_design` (design Open Risks). All scenarios in this plan are
expected to pass config-only based on research Q3–Q5; no engine change is
anticipated.

## Testing checkpoints (for resume after context reset)

- **P1 done:** `test_django.py` exists; `TestDjangoModels` green; model
  class/fields suppressed, `_unused_helper` (DC02, line 9) reported.
- **P2 done:** `TestDjangoViews` green; function views resolved via `views.x`,
  `urlpatterns` suppressed, CBV suppressed by inheritance, orphan view (DC02) and
  `UNUSED_CONSTANT` (DC01) reported.
- **P3 done:** `TestDjangoAdmin` + `TestDjangoSignals` green; both admin styles
  and `@receiver` suppressed; planted symbols reported.
- **P4 done:** `TestDjangoManagementCommands` + `TestDjangoAppConfigs` green;
  `handle`/`add_arguments`/`ready` bodies suppressed, no DC04 leaks.
- **P5 done:** `TestDjangoSettings` green; settings file suppressed by path glob,
  second-file symbol reported.
- **P6 done:** whole file green under `just test` (9 passed); `just check` clean
  (207 passed, 24 skipped, 98.57% coverage).
