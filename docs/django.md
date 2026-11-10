# Django

deadcode parses source text and never imports the project, so it sees only Python name loads. Django reaches code through base classes, decorators,
`MIDDLEWARE` strings, settings modules, and URLconfs, and those framework entry points look unused to a static analyser. This page shows a short Django
configuration, explains `MIDDLEWARE` registrations and both qualified import forms, and lists the entries to append for Django REST Framework.

## Recommended configuration

Add these three option keys to `pyproject.toml` in the directory where you run deadcode:

```toml
[tool.deadcode]
ignore-definitions-if-decorated-with = [
    "@django.contrib.admin.*",
    "@django.contrib.auth.*",
    "@django.dispatch.receiver",
    "@django.utils.decorators.method_decorator",
    "@django.views.decorators.http.require_*",
    "@*register.*",
]
ignore-definitions-if-inherits-from = [
    "django.apps.AppConfig",
    "django.contrib.admin.*",
    "django.core.management.base.BaseCommand",
    "django.db.migrations.Migration",
    "django.db.models.Model",
    "django.forms.*Form",
    "django.utils.deprecation.MiddlewareMixin",
    "django.views.*View",
]
ignore-names-in-files = ["*/settings.py", "*/urls.py"]
```

Each Django entry covers one family, and no two entries match the same qualified base or decorator. One inheritance entry hides a framework subclass name
and its whole body; one decorator entry hides a decorated definition name and its body; the file patterns remove settings and URLconf configuration names.
`MIDDLEWARE` registrations need no entry because deadcode parses the setting itself. Django REST Framework needs the entries in the
[Django REST Framework](#django-rest-framework) section. See {doc}`usage` for the command-line form of every key and {doc}`rules` for the rule codes.

## Common use cases

| Django part | Configuration entry |
|-------------|---------------------|
| Models | `django.db.models.Model` in `ignore-definitions-if-inherits-from` |
| Migrations | `django.db.migrations.Migration` in `ignore-definitions-if-inherits-from` |
| URLs | `*/urls.py` in `ignore-names-in-files` |
| Settings | `*/settings.py` in `ignore-names-in-files` |
| Function views | `@django.views.decorators.http.require_*`, `@django.contrib.auth.*`, and `@django.utils.decorators.method_decorator` |
| Class-based views | `django.views.*View` in `ignore-definitions-if-inherits-from` |
| Middleware | No entry; names listed in `MIDDLEWARE` are parsed as used, while an unregistered middleware class is still reported |
| Templates and template tags | `@*register.*` in `ignore-definitions-if-decorated-with` |
| Forms and model forms | `django.forms.*Form` in `ignore-definitions-if-inherits-from` |
| Admin classes and actions | `django.contrib.admin.*` in `ignore-definitions-if-inherits-from` and `@django.contrib.admin.*` in the decorator list |
| App configurations | `django.apps.AppConfig` in `ignore-definitions-if-inherits-from` |
| Management commands | `django.core.management.base.BaseCommand` in `ignore-definitions-if-inherits-from` |
| Signals | `@django.dispatch.receiver` in `ignore-definitions-if-decorated-with` |
| Tests | No entry; the Django test lifecycle names are ignored by default in test files |
| Auth and security | `@django.contrib.auth.*` for the auth decorators and `*/settings.py` for the settings |
| i18n, caching, and GIS | `*/settings.py` for the settings; ordinary calls and name loads need no entry |
| Django REST Framework | See [Django REST Framework](#django-rest-framework) for the entries to append. |

## Versions

The example targets Django 5.2 LTS, latest patch release 5.2.19, and Django REST Framework 3.18.3. Django 5.2 is the newest LTS release that runs on the
project's minimum Python 3.10 and is supported until April 2028; Django REST Framework 3.18.3 requires Django 5.2 or newer.

The snippets use APIs present in Django 5.2 through 6.1, so a project on any of those releases can copy the configuration. Django 6.1 requires Python 3.12
or newer, while deadcode itself supports Python 3.10 and later. The fixture is parsed as text and never executed: Django and Django REST Framework are
not dependencies of deadcode, and the tests do not run a project or a server.

## Model layer

A model field and a nested `Meta` option are class-level assignments, and Django calls model methods and properties at runtime. The single
`django.db.models.Model` entry removes the class name, the fields, the nested `Meta`, and the properties in one definition rule.

### Both import forms

deadcode records absolute `import` and `from ... import` statements per module and adds the resolved qualified spelling to every class base and
decorator, while keeping the source spelling. These four forms therefore all match the one `django.db.models.Model` entry:

```python
from django.db import models
from django.db.models import Model
import django.db.models as m
from django.db.models import Model as M


class A(models.Model):
    title = models.CharField(max_length=100)


class B(Model):
    title = models.CharField(max_length=100)


class C(m.Model):
    title = models.CharField(max_length=100)


class D(M):
    title = models.CharField(max_length=100)
```

Relative imports and dynamic imports are not resolved. `from .models import Model` with `class Article(Model)` keeps working through the source
candidate and a bare or wildcard expression such as `Model` or `*Model`, but it does not match `django.db.models.Model`.

Custom managers and `QuerySet` subclasses are not `Model` subclasses. A method that only other code calls is still reported; add the manager base to the
inheritance list when its whole body should be ignored, or mark the method with `# noqa: DC04`. Migrations are covered by
`django.db.migrations.Migration`, so `initial`, `dependencies`, and `operations` disappear without a separate `*/migrations/*` file pattern.

## URLs and settings

Settings and URLconf modules are configuration data. `SECRET_KEY`, `DEBUG`, `INSTALLED_APPS`, `MIDDLEWARE`, `TEMPLATES`, `DATABASES`,
`ROOT_URLCONF`, `app_name`, `urlpatterns`, and route name constants are module-level names that no project code loads. The file patterns remove them:

```python
from django.urls import include, path

from . import views

app_name = 'django_example'

urlpatterns = [
    path('', views.index, name='index'),
    path('articles/', include('project.articles.urls')),
]

UNUSED_URL_NAME = 'unused'
```

`ignore-names-in-files` matches the reported path with `fnmatch`, where `*` also spans directory separators. `*/settings.py` and `*/urls.py` therefore
match relative paths such as `project/settings.py` and absolute paths such as `/home/me/project/settings.py`. A project that splits settings into
`settings/base.py` needs a broader pattern such as `*/settings/*.py`; a URL module with another name needs its own entry.

`ROOT_URLCONF`, `WSGI_APPLICATION`, and `ASGI_APPLICATION` are strings, so the modules they name are not loaded by the analyser. A custom WSGI or ASGI
module that assigns `application` needs the file pattern or `# noqa: DC01`. Context processors named in the `TEMPLATES` setting need the same treatment.

## View layer

A URLconf loads function views through attributes such as `views.article_list`, so those functions are not reported. A view that is registered only
through a string, a dynamic import, or code outside the analysed tree looks unused. The function decorators are covered by their family entries:

| Decorator family | Entry |
|------------------|-------|
| `@require_GET`, `@require_POST`, `@require_safe`, `@require_http_methods` | `@django.views.decorators.http.require_*` |
| `@login_required`, `@permission_required`, `@user_passes_test` | `@django.contrib.auth.*` |
| `@method_decorator` | `@django.utils.decorators.method_decorator` |
| `@admin.register`, `@admin.display`, `@admin.action` | `@django.contrib.admin.*` |

Class-based views are covered by inheritance. `django.views.*View` matches `View`, `TemplateView`, `RedirectView`, `DetailView`, `ListView`, `FormView`,
`CreateView`, `UpdateView`, `DeleteView`, and the archive views. Django REST Framework views and viewsets need the entries in
[Django REST Framework](#django-rest-framework).

A project subclass such as `ArticleListView(django.views.generic.ListView)` is covered through its inherited framework base, so the class name and the
whole body are suppressed. Router-called methods (`list`, `create`, `retrieve`, `update`, `partial_update`, `destroy`) are suppressed with the class body
because no Python code loads them in a typical project.

`TemplateResponse`, `render()`, `redirect()`, `get_object_or_404()`, and the request and response objects are ordinary calls and attributes, so they need
no extra configuration. File uploads through `request.FILES`, `FileField`, and a storage backend are ordinary attribute loads; a storage class named only
as a string needs a name load or `# noqa`.

## Middleware

Django has two current middleware forms. The function factory receives `get_response` and returns a nested callable:

```python
def simple_middleware(get_response):
    def middleware(request):
        return get_response(request)

    return middleware
```

The class form stores `get_response` in `__init__` and calls it in `__call__`:

```python
class CurrentMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)
```

`MiddlewareMixin` from `django.utils.deprecation` is the pre-Django-1.10 compatibility form. Django still supports it and does not label it deprecated,
but new middleware should use one of the two forms above:

```python
from django.utils.deprecation import MiddlewareMixin


class SimpleMiddleware(MiddlewareMixin):
    def process_request(self, request):
        return None
```

deadcode parses a module-level `MIDDLEWARE` list or tuple and marks the final dotted component of every string as used. A name listed in `MIDDLEWARE` is
therefore not reported, while a middleware class that is absent from the setting is still reported. A `MiddlewareMixin` subclass's hooks are suppressed
by its inheritance entry. The example fixture contains all three forms and an unregistered `UnusedMiddleware`; that class remains in both reports.

## Template layer

The template language is data, not Python. deadcode does not parse templates, so a context variable, a `{% url %}` reference, or a filter used only in an
HTML file is invisible. Built-in tags such as `{% for %}`, `{% if %}`, and `{{ value|date }}` need no configuration. The `TEMPLATES` setting and the
backend class are covered by the settings file pattern.

Custom tags and filters are registered at import time and are covered by `@*register.*`:

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

`@register.simple_tag`, `@register.filter`, `@register.inclusion_tag`, and `@register.tag` are all covered, so `greeting` and `shout` are not reported.
The undecorated `unused_tag` is genuinely unused and remains `DC02`. A tag registered through a differently named library variable needs its own pattern,
for example `@*library.*` for `library = template.Library()`.

A context processor is named only as a string in the `TEMPLATES` setting. Mark its definition with `# noqa: DC02` or add its name to `ignore-names`; a
project-wide name entry is broader than one `# noqa` comment when several context processors are genuinely reachable.

## Forms

Django forms declare fields as class attributes, and a `ModelForm` reads its model and field list from a nested `Meta` class. Validation hooks are called
by name after the form is bound. `django.forms.*Form` removes the class name, the nested `Meta`, the field names, and the hooks in one entry:

```python
from django import forms

from .models import Article


class ArticleForm(forms.ModelForm):
    class Meta:
        model = Article
        fields = ['title', 'category']

    def clean_title(self):
        return self.cleaned_data['title'].strip()
```

The `django.forms.*Form` pattern covers `Form`, `ModelForm`, and every form subclass whose base name ends with `Form`. Formsets are created with
`formset_factory()`, and their `clean()` method is an ordinary method on the form. Custom validators are ordinary functions; a validator named only as a
string in a field definition needs a name load, `ignore-names`, or `# noqa`.

## Admin

The admin site discovers `ModelAdmin` subclasses when it imports a project's `admin` module. `@admin.register`, `@admin.display`, and `@admin.action` are
covered by `@django.contrib.admin.*`; the options and action methods are covered by `django.contrib.admin.*` in the inheritance list:

```python
from django.contrib import admin

from .forms import ArticleForm
from .models import Article


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    form = ArticleForm
    list_display = ('title', 'published')
    actions = ('mark_featured',)

    @admin.action(description='Mark selected articles as featured')
    def mark_featured(self, request, queryset):
        queryset.update(featured=True)
```

The `actions` tuple contains the action names as strings, so deadcode does not analyse `'mark_featured'`; the method is covered by the `ModelAdmin` body
rule instead. Inline classes inherit `InlineModelAdmin` rather than `ModelAdmin`, and `django.contrib.admin.*` covers `StackedInline`, `TabularInline`,
and their options.

## App configs and management commands

`AppConfig` subclasses are discovered through the dotted string in `INSTALLED_APPS`. `BaseCommand` subclasses are imported by convention from a
`management/commands` package. The two inheritance entries cover the class name and the whole body in one rule each:

```python
from django.apps import AppConfig


class BlogConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'project'

    def ready(self):
        from . import signals  # noqa: F401, PLC0415
```

```python
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Import article data from a file.'

    def add_arguments(self, parser):
        parser.add_argument('path')

    def handle(self, *args, **options: object):
        pass
```

`django.apps.AppConfig` hides `default_auto_field`, `name`, and `ready`; `django.core.management.base.BaseCommand` hides `help`, `add_arguments()`, and
`handle()`. `manage.py` and `django-admin` are ordinary scripts whose settings module is a string, so the settings file pattern covers that module.
Deployment modules that assign `application` need the file pattern or `# noqa: DC01`.

## Signals

Django signals have two registration forms. The decorator form calls `receiver` at import time; the direct form passes the handler to `connect()`:

```python
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Article


@receiver(post_save, sender=Article)
def article_saved(sender, instance, **kwargs: object):
    pass


def article_saved_direct(sender, instance, **kwargs: object):
    pass


post_save.connect(article_saved_direct, sender=Article)


def unused_signal_handler(sender, **kwargs: object):
    pass
```

The decorator form needs `@django.dispatch.receiver`; without it, `article_saved` is `DC02` because a decorator does not create a name load. The direct
`connect()` form is an ordinary name load, so `article_saved_direct` needs no entry. The unconnected `unused_signal_handler` remains `DC02` in both
reports. The database signals `pre_save`, `post_save`, `pre_delete`, and `post_delete` all use the same rule.

## Tests

Django's `TestCase` lifecycle methods are called by the framework, not by project code. deadcode ignores `setUpTestData`, `_pre_setup`, `_post_teardown`,
`_fixture_setup`, and `_fixture_teardown` by default in test files, so the recommended configuration needs no entry for them. A genuine helper whose name
is not a lifecycle name is still reported:

```python
from django.test import TestCase

from .models import Article


class ArticleTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.article = Article.objects.create(title='Example')

    def test_article(self):
        assert self.article.title == 'Example'

    def unused_test_helper(self):
        return None
```

`setUpTestData` produces no finding, while `unused_test_helper` is `DC04` and remains after the configuration. Django test helpers that the test calls
itself, such as `assertContains`, `assertNumQueries`, `settings`, and `modify_settings`, are ordinary name loads and need no configuration.
`pytest-django` fixtures and `unittest` lifecycle methods follow the same rule as ordinary Python code.

## Django REST Framework

Django REST Framework needs the class families and the policy decorators. `rest_framework.*Serializer` covers `Serializer`, `ModelSerializer`, and
`HyperlinkedModelSerializer`; `rest_framework.*Permission`, `rest_framework.*Authentication`, `rest_framework.*Pagination`, `rest_framework.*FilterBackend`,
and `rest_framework.*Throttle` cover the extension classes. `@rest_framework.*` covers `@api_view`, `@action`, `@schema`, and the `*_classes` policy
decorators such as `@permission_classes` and `@authentication_classes`.

These entries are appended to the two arrays in `## Recommended configuration`; the fragment intentionally has no `[tool.deadcode]` header and no
`ignore-names-in-files` key:

```toml
ignore-definitions-if-decorated-with = [
    "@rest_framework.*",
]
ignore-definitions-if-inherits-from = [
    "rest_framework.*View",
    "rest_framework.*ViewSet",
    "rest_framework.*Serializer",
    "rest_framework.*Permission",
    "rest_framework.*Authentication",
    "rest_framework.*Pagination",
    "rest_framework.*FilterBackend",
    "rest_framework.*Throttle",
]
```

The snippet below uses these entries:

```python
from rest_framework import serializers, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Article


class ArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Article
        fields = ['id', 'title', 'published']


class ArticleViewSet(viewsets.ModelViewSet):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        return Response({'status': 'published'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def article_stats(request):
    return Response({'articles': Article.objects.count()})
```

Routers call `list`, `create`, `retrieve`, `update`, `partial_update`, and `destroy` by name, so `rest_framework.*ViewSet` removes the body findings.
`serializer_class` and the nested serializer `Meta` disappear with the serializer and viewset entries, `@rest_framework.*` covers `publish`,
`article_stats`, and `@permission_classes`, and `rest_framework.*Permission` covers a custom permission class. An authentication, pagination, filter
backend, or throttle class is covered by the matching family pattern; a differently named base class needs its own inheritance entry. A serializer used
only through a string or a dynamic lookup needs a name load or `# noqa`.

## Remaining framework areas

The same three keys cover the rest of Django:

- **Auth and security.** `@django.contrib.auth.*` covers `login_required`, `permission_required`, `user_passes_test`, and the other auth decorators.
  `SECRET_KEY`, `ALLOWED_HOSTS`, `SECURE_*`, `CSRF_*`, and `SESSION_COOKIE_*` are settings assignments covered by `*/settings.py`.
- **i18n.** `LANGUAGES`, `LOCALE_PATHS`, and `USE_I18N` are settings; `gettext`, `gettext_lazy`, and `ngettext` are ordinary calls and name loads.
- **Caching.** `CACHES` and the `CACHE_*` settings are covered by the settings file pattern; `cache.get`, `cache.set`, and `cache.delete` are ordinary
  attribute loads. A custom cache backend named only through a string needs a name load, `ignore-names`, or `# noqa`.
- **GIS.** GeoDjango models are still `django.db.models.Model` subclasses and spatial fields are still fields, so the model entry applies. A custom
  `GeoManager` or `GeoQuerySet` follows the manager rule. `GDAL_LIBRARY_PATH` and `GEOS_LIBRARY_PATH` are settings.
- **contenttypes, sessions, and messages.** Their models inherit from `django.db.models.Model`, and their framework calls such as
  `ContentType.objects.get_for_model`, `request.session.get`, and `messages.success` are ordinary calls.
- **Static files.** `STATIC_URL`, `STATIC_ROOT`, `STATICFILES_DIRS`, and `STORAGES` are settings; `static()` and the storage classes are ordinary calls
  and name loads.
- **Email and logging.** `EMAIL_*`, `LOGGING`, and the handler classes named as strings need the settings file pattern or `# noqa`. `send_mail`,
  `EmailMessage`, and `logging.getLogger` are ordinary calls.
- **Checks, async, and deployment.** `@register` covers a custom check, `async def` views follow the same decorator and base-class rules as synchronous
  ones, and `WSGI_APPLICATION` or `ASGI_APPLICATION` is a string covered by the settings file pattern.

## Limitations

- Relative and dynamic imports are not resolved. `from .models import Model` and `from . import models` keep working through a bare or wildcard
  expression, but they do not match a module-qualified pattern such as `django.db.models.Model`. `importlib`, `getattr`, string paths, and code generation cannot be seen by a static analyser.
- `UnusedMiddleware` is intentionally reported. It is absent from `MIDDLEWARE`, so registration cannot mark it as used; the example keeps it to show that
  an unregistered middleware class is still detected.
- The fixture contains deliberately unused definitions: `unused_api_helper`, `unused_manager_method`, `unused_signal_handler`, `unused_tag`,
  `unused_test_helper`, `UNUSED_VIEW_SETTING`, and `unused_view`. They are the real dead code that keeps the configured exit status at `1`.
- Definition options hide names. `ignore-definitions-if-inherits-from` and `ignore-definitions-if-decorated-with` suppress the class or function name
  together with its body, so a genuinely unused Django subclass is not reported. Use the narrower `ignore-bodies-if-inherits-from` or
  `ignore-names-if-decorated-with` when the names must remain visible, or mark the definition with `# noqa`.
- String references other than `MIDDLEWARE` are invisible. `TEMPLATES`, `ROOT_URLCONF`, `INSTALLED_APPS`, context processors, storage backends, cache
  backends, and WSGI or ASGI application paths are strings, so the referenced code needs a name load, a file pattern, or `# noqa`.
- A different decorator or base-class spelling needs its own pattern. A custom admin decorator, a custom permission base, or a project-specific generic
  view that does not end in `View`, `ViewSet`, or `Serializer` is not covered until a pattern or a name is added.
