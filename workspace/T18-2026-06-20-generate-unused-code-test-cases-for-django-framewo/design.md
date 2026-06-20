# Design Discussion

## Current State

Deadcode ships scenario tests for three frameworks under `tests/frameworks/`:
`test_fastapi.py`, `test_sqlalchemy.py`, `test_alembic.py`. There is **no
Django coverage**. Each existing file is a `BaseTestCase` subclass that defines
synthetic source as an in-memory `self.files: dict[str, str]`, calls
`deadcode.cli.main([...])` with `--no-color` plus framework-appropriate ignore
flags, and asserts the exact returned string (`research.md` Q1; pattern visible
at `tests/frameworks/test_fastapi.py:5-53`).

The detection engine (`FindUnusedCodeVisitor`) builds per-type `defined_*`
lists and one flat `used_names` set; an item is unused when its bare name string
is absent from `used_names` (`ignore.py:39-42`). All suppression funnels through
`_define`'s `ignored()` closure, which whitelists a name into `used_names`
rather than filtering at report time (`find_unused_code_visitor.py:284-291`).

Four ignore options are **functional** and already exercised by the existing
framework tests (`research.md` Q3):

- `--ignore-names` — suppress by name glob (`find_unused_code_visitor.py:287`)
- `--ignore-names-in-files` — suppress all names in matching file paths (`:288`)
- `--ignore-definitions-if-decorated-with` — name+body by decorator (`:545`)
- `--ignore-definitions-if-inherits-from` — name+body of class by base (`:544`)
- `--ignore-bodies-if-inherits-from` — body only; class name still reported (`:552-558`)

Six further options (`ignore_bodies_of`, `ignore_bodies_if_decorated_with`,
`ignore_if_decorated_with`, `ignore_if_inherits_from`,
`ignore_names_if_inherits_from`, `ignore_names_if_decorated_with`) are parsed
but **never read by the visitor** — inert (`research.md` Q3,
`docs/unused-detection-and-ignoring.md:49-61`).

Reference handling is bare-name, scope-blind: `obj.foo` Load marks every defined
`foo` used (`find_unused_code_visitor.py:344-348`); only `__all__`,
`getattr`/`hasattr` literals, and `%`/`.format(**locals())` string forms are
treated as uses (`research.md` Q5). Arbitrary string literals (e.g. dotted view
paths in old-style URLconf) are **not** resolved.

## Desired End State

A new `tests/frameworks/test_django.py` (with the package already carrying an
empty `__init__.py`, `docs/testing-and-tooling.md:45`) containing `BaseTestCase`
subclasses that demonstrate Deadcode correctly distinguishes genuinely-unused
code from Django's implicitly/dynamically-used constructs across: models, views
(function + class-based), URL configs, admin, signals, management commands,
settings, and app configs.

Each scenario seeds `self.files`, runs `main([...])` with `--no-color` plus the
minimal ignore flags a real Django project would configure, and asserts the
exact output string. Every positive scenario (a genuinely unused helper *is*
reported) is the load-bearing assertion; framework constructs must be absent
from output. Verify with `just test` (and `just check` for style).

**Success criteria:** new tests pass; for each Django pattern, the framework
construct is suppressed while a deliberately-planted `_unused_helper` /
`UNUSED_CONSTANT` is still reported with the correct `DCxx` code, 1-based line,
0-based column (`research.md` Q6).

## Patterns to Follow

- **Test skeleton:** mirror `tests/frameworks/test_fastapi.py:5-53` exactly —
  class `TestDjango<Subject>(BaseTestCase)`, method
  `test_<behavior_snake_case>`, `self.files = {...}`, `main([... '--no-color']))`,
  `self.assertEqual(output, '<exact>')` (`docs/testing-and-tooling.md:41-43`).
- **Fixtures:** naturally-indented triple-quoted strings; `fix_indent` left-aligns
  them (`base_test_case.py:23-35`, `fix_indent.py:25-50`). No disk I/O.
- **Inherits-from suppression for models/CBVs/commands/app-configs:** follow the
  SQLAlchemy precedent of pairing `--ignore-definitions-if-inherits-from=<Base>`
  with `--ignore-bodies-if-inherits-from=<Base>` when both the class and its
  field/attribute body must be suppressed (`test_sqlalchemy.py:29-36`).
- **Decorator suppression for admin/signals:** follow FastAPI's
  `--ignore-definitions-if-decorated-with=@app.*` (`test_fastapi.py:48-49`);
  Django analogues are `@admin.register*` and `@receiver*`. Dotted decorators
  yield dual full+leaf entries, so `@receiver*` matches `@receiver` and
  `@signals.receiver` (`research.md` Q4).
- **Name/path suppression for settings + urlpatterns:** follow Alembic's
  `--ignore-names=` (per-name) and `--ignore-names-in-files=*versions*` glob
  (`test_alembic.py:32-43`, `:74-80`); Django analogue
  `--ignore-names-in-files=*settings*`.
- **Negative pairing:** every suppression test keeps one genuinely unused symbol
  reported, proving suppression is scoped not blanket (`docs/testing-and-tooling.md:80`).

**Patterns to NOT follow:** do **not** use any of the six inert ignore options
(`research.md` Q3) — they parse but do nothing, so a test "passing" with them
would be misleading. Do not rely on string-literal view references (old-style
`path("", "app.views.v")`) being resolved — they are not (`research.md` Q5).

## Design Decisions

1. **Config-only first, code changes only if forced** — Mirror the three
   existing framework suites: prefer demonstrating correct behaviour via the four
   functional CLI ignore options. Only propose visitor changes if a core Django
   pattern is genuinely unsuppressible by any functional option. *Assumption:*
   the FastAPI/SQLAlchemy/Alembic precedent (no engine changes) is the intended
   bar, and the task's "extend/adjust" clause is contingent, not mandatory.
2. **Models → inherits-from `models.Model`** — `--ignore-definitions-if-inherits-from=models.Model`
   + `--ignore-bodies-if-inherits-from=models.Model`; leaf-matching makes
   `models.Model` and bare `Model` both match (`research.md` Q4). Planted unused:
   a module-level `_unused_helper` outside the model → still DC02.
3. **Class-based views → inherits-from the Django base** (`View`, `ListView`,
   `TemplateView`). Same option pair. `as_view()`/URLconf attribute references
   already mark function views used via `visit_Attribute` leaf matching.
4. **Function views → no special flag** — referenced by `views.my_view` in the
   URLconf file marks them used (`visit_Attribute`, `:344-348`); a truly unused
   view function should still be reported. Demonstrates real detection working.
5. **Admin → decorator `@admin.register*`** and/or inherits-from
   `admin.ModelAdmin`. Provide one decorator-based and one inherits-based test to
   cover both registration styles.
6. **Signals → decorator `@receiver*`** (`--ignore-definitions-if-decorated-with`).
7. **Management commands → inherits-from `BaseCommand`** with the body pair so
   `handle`/`add_arguments` methods are suppressed while a planted unused helper
   in the same file is reported.
8. **Settings → `--ignore-names-in-files=*settings*`** — settings modules are
   walls of UPPERCASE module-level constants Django reads dynamically; per-file
   path suppression matches the Alembic `*versions*` precedent and avoids listing
   each constant by name.
9. **URL configs → `--ignore-names=urlpatterns`** — `urlpatterns` is a
   module-level list Django imports by name; suppress it explicitly. The `path()`
   call references inside it still mark referenced views used.
10. **App configs → inherits-from `AppConfig`** + body pair so `ready()` and
    `name`/`default_auto_field` attributes are suppressed.
11. **One class per Django subject area** (`TestDjangoModels`, `TestDjangoViews`,
    `TestDjangoAdmin`, …) grouping positive+negative methods, matching the
    one-class-per-concern shape of the existing suites.

## What We're NOT Doing

- Not adding or wiring up any of the six inert ignore options, and not making
  them functional (out of scope; that is engine work, not test authoring).
- Not implementing receiver-type-aware / string-annotation resolution
  (`tests/test_accurate_usage_detection.py` is `@skip`ped by design,
  `research.md` Q5).
- Not testing old-style string-path URLconf references (unsupported; would
  require new `visit_Constant` logic).
- Not running Deadcode against a real Django install or real Django source — all
  fixtures are synthetic, minimal, in-memory (consistent with existing suites).
- Not adding a Django dependency to the project.
- Not modifying `BaseTestCase`, `parse_arguments`, or the visitor unless a
  pattern proves unsuppressible (see Open Risks).

## Open Risks

- **Column/line exactness:** assertions hardcode `line:col`; fixture edits shift
  them. Mitigate by writing fixtures first, running once, and pasting observed
  output (columns are 0-based from `ast.col_offset`, `research.md` Q6).
- **Leaf-vs-dotted base matching:** if a fixture writes `from django.db import models`
  then `class M(models.Model)`, the base resolves to both `models.Model` and
  `Model`; confirm the chosen glob matches the form emitted by `get_base_name`
  (`utils.py:64-77`).
- **Method suppression depth:** `--ignore-bodies-if-inherits-from` suppresses only
  direct body child definitions; nested defs or attributes assigned in `ready()`
  may still surface — verify per scenario.
- **A pattern may genuinely need engine work:** if e.g. `urlpatterns` or a signal
  handler cannot be cleanly suppressed without an inert/missing option, escalate
  per the task's "extend/adjust detection" clause and document it rather than
  forcing a brittle config. This is the one place a code change might be justified.
