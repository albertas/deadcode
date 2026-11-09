# Django

deadcode is framework-agnostic: it parses source code and never imports it. Django registers models, views, admin classes, and signal handlers at
runtime, so much of a Django project's code is reachable only through a base class, a decorator, a settings string, or a URLconf. A static analyser
that only follows name loads sees those framework entry points as unused. This page shows the recommended configuration, documents the common Django
mechanisms, and gives a complete example application that produces no wrong detections.

## Recommended configuration

Add these options to `pyproject.toml` in the directory where you run deadcode:

```toml
[tool.deadcode]
ignore-names-if-decorated-with = [
    "@admin.*",
    "@receiver",
    "@register.*",
    "@login_required",
    "@permission_required",
    "@require_http_methods",
    "@require_POST",
    "@method_decorator",
]
ignore-bodies-if-inherits-from = [
    "models.Model",
    "ModelAdmin",
    "forms.Form",
    "forms.ModelForm",
    "View",
    "BaseCommand",
    "Migration",
    "AppConfig",
    "MiddlewareMixin",
]
ignore-names-in-files = ["*/settings.py", "*/urls.py", "*/migrations/*"]
ignore-definitions = ["*Config", "*Middleware", "Command"]
ignore-names = [
    "setUpTestData",
    "_pre_setup",
    "_post_teardown",
    "_fixture_setup",
    "_fixture_teardown",
]
```

The same options are available as command-line flags, with one occurrence per list item:

```shell
deadcode . \
    --ignore-names-if-decorated-with='@admin.*' \
    --ignore-names-if-decorated-with='@receiver' \
    --ignore-names-if-decorated-with='@register.*' \
    --ignore-names-if-decorated-with='@login_required' \
    --ignore-names-if-decorated-with='@permission_required' \
    --ignore-names-if-decorated-with='@require_http_methods' \
    --ignore-names-if-decorated-with='@require_POST' \
    --ignore-names-if-decorated-with='@method_decorator' \
    --ignore-bodies-if-inherits-from=models.Model \
    --ignore-bodies-if-inherits-from=ModelAdmin \
    --ignore-bodies-if-inherits-from=forms.Form \
    --ignore-bodies-if-inherits-from=forms.ModelForm \
    --ignore-bodies-if-inherits-from=View \
    --ignore-bodies-if-inherits-from=BaseCommand \
    --ignore-bodies-if-inherits-from=Migration \
    --ignore-bodies-if-inherits-from=AppConfig \
    --ignore-bodies-if-inherits-from=MiddlewareMixin \
    --ignore-names-in-files='*/settings.py' \
    --ignore-names-in-files='*/urls.py' \
    --ignore-names-in-files='*/migrations/*' \
    --ignore-definitions='*Config' \
    --ignore-definitions='*Middleware' \
    --ignore-definitions=Command \
    --ignore-names=setUpTestData \
    --ignore-names=_pre_setup \
    --ignore-names=_post_teardown \
    --ignore-names=_fixture_setup \
    --ignore-names=_fixture_teardown
```

deadcode reads configuration only from `./pyproject.toml` in the current working directory. It does not search parent directories and there is no
`--config` option, so run the command from the project root or pass the options on the command line.

`ignore-names-in-files` matches the reported path with `fnmatch`, where `*` also spans directory separators. The patterns therefore match both
relative (`project/settings.py`) and absolute (`/home/me/project/settings.py`) paths. See {doc}`usage` for the full option semantics and
{doc}`rules` for the rule codes.

## Common use cases

| Django mechanism | Configuration needed |
|------------------|----------------------|
| Settings variables such as `SECRET_KEY`, `DEBUG`, `INSTALLED_APPS`, `MIDDLEWARE`, and `TEMPLATES` | Covered by `ignore-names-in-files = ["*/settings.py"]` |
| URLconf variables such as `app_name`, `urlpatterns`, and route name constants | Covered by `ignore-names-in-files = ["*/urls.py"]` |
| Migration modules, `Migration` attributes, and `operations` | Covered by `ignore-names-in-files = ["*/migrations/*"]` and `Migration` in `ignore-bodies-if-inherits-from` |
| Model fields and nested `Meta` options | Covered by `models.Model` in `ignore-bodies-if-inherits-from` |
| Model properties and methods called by templates or the framework | Covered by `models.Model` in `ignore-bodies-if-inherits-from` |
| Managers and `QuerySet` methods | Add the manager or queryset base class to `ignore-bodies-if-inherits-from`, or use `# noqa` |
| Admin options and action methods | Covered by `ModelAdmin` in `ignore-bodies-if-inherits-from` |
| `@admin.register` and other admin decorators | Covered by `@admin.*` in `ignore-names-if-decorated-with` |
| Forms and `ModelForm` fields and validation methods | Covered by `forms.Form` and `forms.ModelForm` in `ignore-bodies-if-inherits-from` |
| Class-based views and HTTP-method handlers | Covered by `View` in `ignore-bodies-if-inherits-from` |
| Middleware classes and hooks | Covered by `*Middleware` in `ignore-definitions` and `MiddlewareMixin` in `ignore-bodies-if-inherits-from` |
| `@receiver` signal handlers | Covered by `@receiver` in `ignore-names-if-decorated-with` |
| `@register.simple_tag` and `@register.filter` | Covered by `@register.*` in `ignore-names-if-decorated-with` |
| Management commands | Covered by `Command` in `ignore-definitions` and `BaseCommand` in `ignore-bodies-if-inherits-from` |
| `AppConfig` subclasses | Covered by `*Config` in `ignore-definitions` and `AppConfig` in `ignore-bodies-if-inherits-from` |
| Django test lifecycle names such as `setUpTestData` and `_pre_setup` | Covered by the explicit `ignore-names` entries |
| Context processors and other string-referenced callables | `None` in the base block; use `# noqa: DC02` or add the name to `ignore-names` |
| `@login_required` and the other security decorators | Covered by the decorator entries in `ignore-names-if-decorated-with` |

A context processor is named only as a string in the `TEMPLATES` setting, so deadcode cannot see the load. Mark the definition directly:

```python
def context_processor(request):  # noqa: DC02
    return {'site_name': 'Example'}
```

## Model layer

Models are the largest source of Django false positives. A model field or nested `Meta` option is a class-level assignment with no Python
name load, and Django calls model methods and properties at runtime. `models.Model` in `ignore-bodies-if-inherits-from` removes all findings
from the body of a model class while the class name itself is still reported when nothing uses it.

| Mechanism | Finding without configuration | Remedy |
|-----------|-------------------------------|--------|
| Model fields such as `CharField`, `ForeignKey`, and `BooleanField` | `DC06` for each field name | `models.Model` in `ignore-bodies-if-inherits-from` |
| Nested `class Meta` and its options such as `ordering` and `verbose_name_plural` | `DC03` for `Meta`, `DC06` for the options | `models.Model` in `ignore-bodies-if-inherits-from` |
| Model methods such as `__str__`, and `@property` methods called by templates | `DC04` for methods, `DC08` for properties | `models.Model` in `ignore-bodies-if-inherits-from` |
| Relations and related managers such as `category.articles` | `DC06` when the relation attribute is assigned only | `models.Model` in `ignore-bodies-if-inherits-from` |
| Custom managers and `QuerySet` methods | `DC04` for methods that only other code calls | Add the manager or queryset base class to `ignore-bodies-if-inherits-from`, or mark each method with `# noqa` |
| Migration attributes and operations | `DC06` for `initial`, `dependencies`, and `operations` | `Migration` in `ignore-bodies-if-inherits-from` |
| Migration module helpers and imports | `DC01`, `DC06`, `DC07`, or `DC12` depending on the code | `ignore-names-in-files = ["*/migrations/*"]` |

A custom manager or `QuerySet` is not covered by `models.Model`. Add its base class to `ignore-bodies-if-inherits-from` when its methods are called
only by other code, or mark the individual method with `# noqa: DC04`. The same rule applies to a model mixin that is not itself a `models.Model`
subclass.

Migrations need both options. `Migration` in `ignore-bodies-if-inherits-from` removes the body attributes, and the file pattern for
`*/migrations/*` removes module-level findings and keeps generated migration code out of the report. Raw SQL through `connection.cursor()`,
transactions through `atomic()` and `transaction.on_commit()`, and aggregation through `annotate()` and `aggregate()` are ordinary function and
method calls, so they need no additional configuration beyond the base block.

## View layer

A URLconf names views as attributes and strings, so deadcode sees only part of the wiring. `urls.py` uses `path()`, `re_path()`, and `include()`, and
the module-level `urlpatterns` list is assigned without a name load. `ignore-names-in-files = ["*/urls.py"]` removes the URLconf variables; a project
that keeps URLs outside a file named `urls.py` needs its own pattern. Views referenced through `include()` or a dotted string keep their class and
function definitions reachable only by name, so a view class that nothing imports is reported as `DC03`.

| Mechanism | Finding without configuration | Remedy |
|-----------|-------------------------------|--------|
| URLconf variables such as `app_name`, `urlpatterns`, and route name constants | `DC01` for each variable | `ignore-names-in-files = ["*/urls.py"]` |
| Function views and decorators such as `@login_required` and `@require_POST` | `DC02` for the decorated function, `DC04` when only the framework calls it | `@login_required`, `@permission_required`, `@require_http_methods`, `@require_POST`, and `@method_decorator` in `ignore-names-if-decorated-with` |
| Class-based views referenced only by a string or `include()` | `DC03` for the class | A name load, or `# noqa: DC03` when the class is genuinely used |
| HTTP-method handlers such as `get`, `post`, and `dispatch` | `DC04` for each handler | `View` in `ignore-bodies-if-inherits-from` |
| Middleware classes named only in `MIDDLEWARE` | `DC03` for the class, `DC04` for hooks such as `process_request` | `*Middleware` in `ignore-definitions` and `MiddlewareMixin` in `ignore-bodies-if-inherits-from` |

Function views are ordinary functions. Deadcode follows their name loads, so `path('', views.index)` keeps `index` alive and a decorator that it does not
know would otherwise make the function look unused. The decorator entries in the recommended configuration cover the Django decorators that wrap a
view at definition time.

Class-based views inherit their handlers from `View`, `TemplateView`, `DetailView`, `ListView`, `FormView`, or another generic base class. Django calls
`dispatch()` and then the matching `get()` or `post()` method by name, and no Python code loads them. `View` in `ignore-bodies-if-inherits-from`
removes those findings from every class-based view while the class name itself is still reported when nothing references it:

```python
from django.views import View
from django.views.generic import ListView

from .models import Article


class ArticleView(View):
    def get(self, request):
        return HttpResponse('articles')


class ArticleListView(ListView):
    model = Article
    template_name = 'blog/article_list.html'
```

`TemplateResponse`, `render()`, `redirect()`, and the request and response objects are ordinary calls and attributes, so they need no extra
configuration. File uploads through `request.FILES`, `FileField`, and a storage backend are likewise ordinary attribute loads; the model-field rule
covers the field and the storage class needs a name load or `# noqa` when it is configured only as a string.

The same rule applies to middleware. `MIDDLEWARE` lists classes as dotted strings, and Django calls `process_request`, `process_response`, and the other
hooks at runtime. `*Middleware` in `ignore-definitions` removes the class-name finding, and `MiddlewareMixin` in `ignore-bodies-if-inherits-from` removes
the hook and option findings:

```python
from django.utils.deprecation import MiddlewareMixin


class SimpleMiddleware(MiddlewareMixin):
    def process_request(self, request):
        return None
```

A middleware class that does not inherit `MiddlewareMixin` needs its hooks covered by a base class in `ignore-bodies-if-inherits-from` or by
`# noqa: DC04`. A view or middleware helper that is genuinely dead is still reported when the configuration is applied to a different base class.

## Template layer

The template language is data, not Python: deadcode does not parse templates, so a context variable, a `{% url %}` reference, or a filter used only in a
`.html` file is invisible. The `TEMPLATES` setting in `settings.py` is covered by the settings file pattern, and the template backend is named as a
string. Built-in tags and filters such as `{% for %}`, `{% if %}`, `{{ value|date }}`, and `{{ value|default }}` need no configuration because
deadcode never sees the template.

The template API in Python is ordinary code. `loader.get_template()`, `render_to_string()`, `Template`, `Context`, and `TemplateResponse` are normal
function and class calls. The interesting findings come from custom tags and filters, which are registered at import time:

```python
from django import template

register = template.Library()


@register.simple_tag
def greeting(name):
    return f'Hello {name}'


@register.filter
def shout(value):
    return value.upper()


def unused_tag(value):
    return value
```

`@register.simple_tag`, `@register.filter`, `@register.inclusion_tag`, and `@register.tag` are all covered by `@register.*` in
`ignore-names-if-decorated-with`, so `greeting` and `shout` are not reported. The undecorated `unused_tag` is genuinely unused and still reported as
`DC02`. A tag registered with a different library decorator needs its own pattern or a name load.

A context processor is named only as a string in the `TEMPLATES` setting, so deadcode cannot see the call:

```python
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'project.context_processors.site_name',
            ],
        },
    },
]
```

Mark the definition directly with `# noqa: DC02` or add its name to `ignore-names`. The `# noqa` form keeps the suppression next to the function, which
is clearer than a project-wide name entry when a project has several context processors:

```python
def site_name(request):  # noqa: DC02
    return {'site_name': 'Example'}
```

A template backend configured through a dotted path is a string reference too. The built-in Django backend needs no configuration because deadcode does
not analyse Django itself; a custom backend class in the project needs a name load or `# noqa`.

## Forms

Django forms declare fields as class attributes, and a `ModelForm` reads its model and field list from a nested `Meta` class. Deadcode reports each
field as `DC06`, the nested `Meta` class as `DC03`, and validation hooks such as `clean_title()` and `clean()` as `DC04` because Django calls them by
name after the form is bound.

| Mechanism | Finding without configuration | Remedy |
|-----------|-------------------------------|--------|
| Form fields and widgets such as `CharField` and `Select` | `DC06` for each field name | `forms.Form` and `forms.ModelForm` in `ignore-bodies-if-inherits-from` |
| Nested `class Meta` and its `model` and `fields` options | `DC03` for `Meta`, `DC06` for the options | `forms.Form` and `forms.ModelForm` in `ignore-bodies-if-inherits-from` |
| Validation hooks such as `clean_title()` and `clean()` | `DC04` for each method | `forms.Form` and `forms.ModelForm` in `ignore-bodies-if-inherits-from` |
| Formsets, `media` definitions, and custom validators | None when the code is called directly | Add a name load, or `# noqa` for a callable referenced only by a string |

`forms.Form` and `forms.ModelForm` in `ignore-bodies-if-inherits-from` remove every finding from the form body, while the class name itself is still
reported as `DC03` when nothing references it. A form that inherits a project mixin instead of `forms.Form` needs that mixin's base class added to the
same list, or each validation method marked with `# noqa: DC04`. A form set is created with `formset_factory()`, and its `clean()` method is an ordinary
method on the form; neither needs extra configuration when the call site loads the class. Custom validators are ordinary functions, so a validator named
only as a string in a field definition needs a name load, `ignore-names`, or `# noqa`.

## Admin

The admin site discovers `ModelAdmin` subclasses when it imports a project's `admin` module. `@admin.register` registers the class and, because it is a
decorator, is covered by `@admin.*` in `ignore-names-if-decorated-with`. A class registered without the decorator is referenced only by the admin site
and is reported as `DC03` unless it has a name load.

| Mechanism | Finding without configuration | Remedy |
|-----------|-------------------------------|--------|
| `@admin.register` and other admin decorators | `DC03` for the decorated class | `@admin.*` in `ignore-names-if-decorated-with` |
| Options such as `list_display`, `search_fields`, `list_filter`, and `actions` | `DC06` for each option | `ModelAdmin` in `ignore-bodies-if-inherits-from` |
| Admin action methods named in `actions` | `DC04` for each action method | `ModelAdmin` in `ignore-bodies-if-inherits-from` |
| Inline classes such as `StackedInline` and `TabularInline` | `DC03` for the class, `DC06` for its options | Add the inline base class to `ignore-bodies-if-inherits-from`, or use `# noqa` |

The options and the action method are attributes of the `ModelAdmin` body, so `ModelAdmin` in `ignore-bodies-if-inherits-from` removes them together. The
`actions` tuple contains the action names as strings, such as `'mark_featured'`, and deadcode does not analyse string contents; the method itself
is covered by the base-class rule, not by a name load. An inline class inherits `InlineModelAdmin` rather than `ModelAdmin` in a typical project, so check
its base class and add the missing entry when its body is reported. The admin site's documentation generator is an ordinary command and needs no
configuration beyond the base block.

## Development process

A Django settings module is a sequence of module-level assignments that nothing in the project imports by name. The settings file pattern in the
recommended configuration removes those findings. Projects that split settings into a package, such as `settings/base.py` and `settings/production.py`,
need a broader pattern such as `*/settings/*.py`; a differently named environment module needs its own entry. `manage.py` and `django-admin` are ordinary
scripts, and the settings module and application entry points they name are strings, so deadcode never sees those loads.

`AppConfig` subclasses are discovered through `INSTALLED_APPS`, which names them as dotted strings. `*Config` in `ignore-definitions` covers the class
name, and `AppConfig` in `ignore-bodies-if-inherits-from` covers `default_auto_field`, `name`, and the `ready()` hook. A project with a differently named
application configuration class needs an additional definition pattern or a name load.

Custom management commands are classes named `Command` in a `management/commands` package. The `Command` entry in `ignore-definitions` covers the class
name, and `BaseCommand` in `ignore-bodies-if-inherits-from` covers `help`, `add_arguments()`, and `handle()`. `django-admin` imports the module and
constructs the command by convention, so there is no name load to follow. A helper command class with another name is still reported unless it has a name
load; the example application keeps one intentionally unused command to show that difference.

Django's `TestCase` lifecycle methods are called by the framework, not by project code. The recommended configuration adds `setUpTestData`, `_pre_setup`,
`_post_teardown`, `_fixture_setup`, and `_fixture_teardown` to `ignore-names`. The local base commit does not suppress those names, so all five are
reported in a test file without the entries. Releases containing the Django lifecycle suppression upstream (PR #104) already ignore these names in test
files, which makes the entries redundant there. A genuine helper that is not a lifecycle name and is not called is still reported.

Deployment modules have the same string-reference problem as settings. A WSGI or ASGI module assigns `application` without loading it, so add the module
pattern to `ignore-names-in-files` or mark the assignment with `# noqa: DC01`. Static files are collected through the `staticfiles` application and
settings, and error reporting is configured through `ADMINS`, `SERVER_EMAIL`, and logging settings; all of those are string or module assignments
covered by the settings pattern. A custom handler class named only as a string needs a name load, `# noqa`, or an entry in `ignore-names`.

## Security

Most Django security configuration is settings: `SECRET_KEY`, `ALLOWED_HOSTS`, `SECURE_*`, `CSRF_*`, `SESSION_COOKIE_*`, and the password hashers are
module-level assignments covered by the settings file pattern. CSRF tokens, clickjacking protection, and cryptographic signing are ordinary template
tags, middleware, and function calls such as `signing.dumps()` and `signing.loads()`, so they need no additional configuration.

The security decorators on views and helpers are covered by `ignore-names-if-decorated-with`. The recommended entries include `@csrf_exempt`,
`@login_required`, `@permission_required`, `@require_http_methods`, `@require_POST`, and `@method_decorator`. An undecorated function that is genuinely
unused is still reported, and a custom security decorator needs its own pattern.

## Internationalization and localization

`gettext`, `gettext_lazy`, `ngettext`, and their aliases are ordinary function calls, so a wrapped literal and a translated name are normal name loads.
The `LANGUAGES`, `LOCALE_PATHS`, and `USE_I18N` settings are covered by the settings file pattern, and locale directories contain data files rather
than Python modules. Per-site and per-user time zone settings are also settings assignments; code that calls `timezone.localtime()` or
`activate()` needs no extra configuration beyond the base block.

## Performance and optimization

Caching through `cache.get()`, `cache.set()`, `cache_page`, and a configured cache backend is ordinary code and settings. `select_related()` and
`prefetch_related()` are ordinary queryset method calls, and `django-debug-toolbar`-style tooling is a third-party package that deadcode parses like
any other dependency. No special configuration is needed beyond the base block; a custom cache backend named only through a string setting needs a name
load, `ignore-names`, or `# noqa`.

## Geographic framework

GeoDjango models are still `models.Model` subclasses and spatial fields are still `Field` subclasses, so the model base rule applies and the class name
is reported only when nothing references it. `GeoManager` and `GeoQuerySet` follow the manager rule: add the base class to
`ignore-bodies-if-inherits-from` when their methods are called only by the framework. GDAL and GEOS are optional and are imported by Django at runtime;
deadcode never imports the project, so a missing native library does not affect the report.

## Common web application tools

| Tool | Configuration needed |
|------|----------------------|
| Authentication and passwords | `None`; ordinary views, models, and settings |
| Caching | `None` beyond the base block; string backend settings use the settings pattern |
| Logging | `None`; `LOGGING` is a settings assignment covered by the settings pattern |
| Email | `None`; message classes and settings are ordinary code |
| Syndication feeds | `None`; feed classes are ordinary classes and views |
| Pagination | `None`; `Paginator` and `Page` are ordinary classes |
| Messages | `None`; the messages framework is middleware and ordinary calls |
| Serialization | `None`; serializers are ordinary functions and classes |
| Sessions | `None`; session backends are configured through settings strings |
| Sitemaps | `None`; sitemap classes are ordinary classes |
| Static files | `None` beyond the base block; `STATICFILES_*` settings use the settings pattern |
| Data validation | `None`; validators are ordinary callables |

## Other core functionality

Conditional content processing through `{% if %}`, content types and generic relations through `ContentType` and `GenericForeignKey`, flatpages,
redirects, system checks, and the sites framework are ordinary models, functions, and settings. Their class-level attributes follow the model rule,
and their configuration strings follow the settings pattern.

Signals have their own rule. A handler decorated with `@receiver` is covered by `@receiver` in `ignore-names-if-decorated-with`. A handler connected
with `post_save.connect(article_saved)` has an ordinary name load and is not reported. A handler that has no decorator and no call is reported as
`DC02` and needs an explicit `ignore-names` entry or `# noqa`; the example application keeps one such handler to show the intentional finding. Unicode
handling and the remaining utility helpers are ordinary Python code with no Django-specific configuration.

## Example application

The acceptance fixture in `tests/files/django` is a small multi-module Django project. It uses `tests/files/django/settings.py`,
`tests/files/django/urls.py`, `tests/files/django/views.py`, `tests/files/django/middleware.py`, `tests/files/django/models.py`,
`tests/files/django/managers.py`, `tests/files/django/migrations/0001_initial.py`, `tests/files/django/templatetags/blog_tags.py`,
`tests/files/django/forms.py`, `tests/files/django/admin.py`, `tests/files/django/apps.py`, `tests/files/django/signals.py`,
`tests/files/django/management/commands/import_data.py`, and `tests/files/django/tests.py`.

`settings.py` defines the usual module-level settings plus one intentionally unused setting, and it names the application configuration in
`INSTALLED_APPS`. `urls.py` defines `app_name`, `urlpatterns`, and one intentionally unused URLconf variable. `views.py` defines a function view loaded
by the URLconf, a class-based view loaded through `.as_view()`, one intentionally unused setting, one intentionally unused function view, and one
intentionally unused class-based view. `middleware.py` defines a `MiddlewareMixin` subclass referenced only by the `MIDDLEWARE` string. `models.py`
defines a `Category`/`Article` pair with fields, nested `Meta` classes, and properties, plus one intentionally unused model. `managers.py` defines a
custom `QuerySet` and manager with one intentionally unused manager method. `migrations/0001_initial.py` is a generated-style migration.
`templatetags/blog_tags.py` registers a simple tag and a filter and leaves one intentionally unused function. `forms.py` defines a `ModelForm` with a
nested `Meta` and a validation hook, plus one intentionally unused form. `admin.py` registers an `ArticleAdmin` with options and an action method,
plus one intentionally unused admin class. `apps.py` defines a `BlogConfig` with `default_auto_field` and a `ready()` hook, and `signals.py` defines a
`@receiver` handler plus one intentionally unused signal handler. `management/commands/import_data.py` defines a `Command` with `help`,
`add_arguments()`, and `handle()`, plus one intentionally unused command. `tests.py` defines a `TestCase` with Django's five lifecycle hooks, a real
test, and one intentionally unused helper.

Without configuration, the settings and URLconf variables, the middleware and its hook, the class-based view handlers, the registered template tags,
the form fields and validation hooks, the admin options and action method, the application configuration, the management command members, the
decorated signal handler, and the test lifecycle hooks are reported together with the intentionally unused code:

```text
project/admin.py:8:0: DC03 Class `ArticleAdmin` is never used
project/admin.py:9:4: DC06 Name `form` is never used
project/admin.py:10:4: DC06 Name `list_display` is never used
project/admin.py:11:4: DC06 Name `search_fields` is never used
project/admin.py:12:4: DC06 Name `list_filter` is never used
project/admin.py:13:4: DC06 Name `actions` is never used
project/admin.py:15:4: DC04 Method `mark_featured` is never used
project/admin.py:19:0: DC03 Class `UnusedAdmin` is never used
project/admin.py:20:4: DC06 Name `list_display` is never used
project/apps.py:4:0: DC03 Class `BlogConfig` is never used
project/apps.py:5:4: DC06 Name `default_auto_field` is never used
project/apps.py:8:4: DC04 Method `ready` is never used
project/forms.py:7:4: DC03 Class `Meta` is never used
project/forms.py:8:8: DC06 Name `model` is never used
project/forms.py:9:8: DC06 Name `fields` is never used
project/forms.py:11:4: DC04 Method `clean_title` is never used
project/forms.py:15:0: DC03 Class `UnusedForm` is never used
project/management/commands/import_data.py:4:0: DC03 Class `Command` is never used
project/management/commands/import_data.py:5:4: DC06 Name `help` is never used
project/management/commands/import_data.py:7:4: DC04 Method `add_arguments` is never used
project/management/commands/import_data.py:10:4: DC04 Method `handle` is never used
project/management/commands/import_data.py:14:0: DC03 Class `UnusedCommand` is never used
project/management/commands/import_data.py:15:4: DC04 Method `handle` is never used
project/managers.py:13:4: DC04 Method `unused_manager_method` is never used
project/middleware.py:4:0: DC03 Class `SimpleMiddleware` is never used
project/middleware.py:5:4: DC04 Method `process_request` is never used
project/migrations/0001_initial.py:5:4: DC06 Name `initial` is never used
project/migrations/0001_initial.py:7:4: DC06 Name `dependencies` is never used
project/migrations/0001_initial.py:9:4: DC06 Name `operations` is never used
project/models.py:9:4: DC03 Class `Meta` is never used
project/models.py:10:8: DC06 Name `verbose_name_plural` is never used
project/models.py:18:4: DC06 Name `category` is never used
project/models.py:23:4: DC03 Class `Meta` is never used
project/models.py:24:8: DC06 Name `ordering` is never used
project/models.py:27:4: DC08 Property `display_name` is never used
project/models.py:31:4: DC08 Property `published_titles` is never used
project/models.py:35:0: DC03 Class `UnusedModel` is never used
project/settings.py:1:0: DC01 Variable `SECRET_KEY` is never used
project/settings.py:2:0: DC01 Variable `DEBUG` is never used
project/settings.py:4:0: DC01 Variable `INSTALLED_APPS` is never used
project/settings.py:10:0: DC01 Variable `MIDDLEWARE` is never used
project/settings.py:15:0: DC01 Variable `TEMPLATES` is never used
project/settings.py:27:0: DC01 Variable `DATABASES` is never used
project/settings.py:33:0: DC01 Variable `ROOT_URLCONF` is never used
project/settings.py:35:0: DC01 Variable `UNUSED_SETTING` is never used
project/signals.py:8:0: DC02 Function `article_saved` is never used
project/signals.py:12:0: DC02 Function `unused_signal_handler` is never used
project/templatetags/blog_tags.py:7:0: DC02 Function `greeting` is never used
project/templatetags/blog_tags.py:12:0: DC02 Function `shout` is never used
project/templatetags/blog_tags.py:16:0: DC02 Function `unused_tag` is never used
project/tests.py:8:4: DC04 Method `setUpTestData` is never used
project/tests.py:11:4: DC04 Method `_pre_setup` is never used
project/tests.py:14:4: DC04 Method `_post_teardown` is never used
project/tests.py:17:4: DC04 Method `_fixture_setup` is never used
project/tests.py:20:4: DC04 Method `_fixture_teardown` is never used
project/tests.py:26:4: DC04 Method `unused_test_helper` is never used
project/urls.py:5:0: DC01 Variable `app_name` is never used
project/urls.py:7:0: DC01 Variable `urlpatterns` is never used
project/urls.py:12:0: DC01 Variable `UNUSED_URL_NAME` is never used
project/views.py:4:0: DC01 Variable `UNUSED_VIEW_SETTING` is never used
project/views.py:11:0: DC02 Function `unused_view` is never used
project/views.py:16:4: DC04 Method `get` is never used
project/views.py:20:0: DC03 Class `UnusedView` is never used
project/views.py:21:4: DC04 Method `get` is never used
```

With the recommended configuration, only the intentionally unused code in `views.py`, `models.py`, `managers.py`, `forms.py`, `admin.py`,
`templatetags/blog_tags.py`, `signals.py`, `management/commands/import_data.py`, and `tests.py` remains. The settings, URLconf, model-field,
nested-`Meta`, property, migration, middleware-hook, `@register.*`, form, admin, application-configuration, management-command, receiver, and
lifecycle findings disappear because the base-class, decorator, definition, and file options cover them. The final report is:

```text
project/admin.py:19:0: DC03 Class `UnusedAdmin` is never used
project/forms.py:15:0: DC03 Class `UnusedForm` is never used
project/management/commands/import_data.py:14:0: DC03 Class `UnusedCommand` is never used
project/managers.py:13:4: DC04 Method `unused_manager_method` is never used
project/models.py:35:0: DC03 Class `UnusedModel` is never used
project/signals.py:12:0: DC02 Function `unused_signal_handler` is never used
project/templatetags/blog_tags.py:16:0: DC02 Function `unused_tag` is never used
project/tests.py:26:4: DC04 Method `unused_test_helper` is never used
project/views.py:4:0: DC01 Variable `UNUSED_VIEW_SETTING` is never used
project/views.py:11:0: DC02 Function `unused_view` is never used
project/views.py:20:0: DC03 Class `UnusedView` is never used
```

## Verifying the recommended configuration

Copy the configuration into `pyproject.toml`, then run:

```shell
deadcode . --no-color
```

The command exits with status `0` when there are no findings, `1` when findings remain, and `2` for argument errors. See {doc}`usage` for the exit
status details and the other command-line options. If a framework entry point is still reported, compare its decorator, base class, or file path
with the patterns above and add the missing pattern.

## Limitations

- deadcode does not detect Django automatically. Configuration is explicit and applies to any framework that uses decorators, base classes, and
  file conventions.
- String references are invisible. Settings such as `MIDDLEWARE`, `TEMPLATES`, and `ROOT_URLCONF` name callables and modules as strings, so the
  referenced code needs a name load, a file pattern, or `# noqa`.
- Base-class overrides are not resolved. A method that Django calls but that no Python code loads needs its base class in
  `ignore-bodies-if-inherits-from` or an explicit `# noqa`.
- Dynamic registration through `getattr`, `importlib`, string paths, or code generation cannot be seen by a static analyser.
- A different decorator or base-class spelling needs its own pattern. For example, a custom admin decorator or an aliased `ModelAdmin` import does
  not match the entries above until the pattern or the imported name is added.
