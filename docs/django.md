# Django

deadcode parses source text and never imports the project, so it sees only Python name loads. Django reaches code through base classes, decorators,
`MIDDLEWARE` strings, settings modules, and URLconfs, and those framework entry points look unused to a static analyser. This page shows one small
configuration for Django and Django REST Framework, explains `MIDDLEWARE` registrations and both qualified import forms, and gives a complete example
application whose two reports you can reproduce.

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
    "@rest_framework.*",
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
    "rest_framework.*View",
    "rest_framework.*ViewSet",
    "rest_framework.*Serializer",
    "rest_framework.*Permission",
    "rest_framework.*Authentication",
    "rest_framework.*Pagination",
    "rest_framework.*FilterBackend",
    "rest_framework.*Throttle",
]
ignore-names-in-files = ["*/settings.py", "*/urls.py"]
```

Each entry covers one family, and no two entries match the same qualified base or decorator. One inheritance entry hides a framework subclass name and
its whole body; one decorator entry hides a decorated definition name and its body; the file patterns remove settings and URLconf configuration names.
`MIDDLEWARE` registrations need no entry because deadcode parses the setting itself. See {doc}`usage` for the command-line form of every key and
{doc}`rules` for the rule codes.

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
| Django REST Framework | `rest_framework.*View`, `rest_framework.*ViewSet`, `rest_framework.*Serializer`, and the permission, authentication, pagination, filter, and throttle families, plus `@rest_framework.*` |

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
candidate and a bare or wildcard expression such as `Model` or `*Model`, but it does not match `django.db.models.Model`. An import performed inside a
function is also outside the module-level map.

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
`CreateView`, `UpdateView`, `DeleteView`, and the archive views. `rest_framework.*View` matches `APIView` and the generic API views, and
`rest_framework.*ViewSet` matches the viewset family.

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
decorators such as `@permission_classes` and `@authentication_classes`:

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

## Example application

The acceptance fixture in `tests/files/django/` is a small multi-module Django application. It contains `settings.py`, `urls.py`, `views.py`,
`middleware.py`, `models.py`, `managers.py`, `migrations/0001_initial.py`, `templatetags/blog_tags.py`, `forms.py`, `import_forms.py`, `admin.py`,
`apps.py`, `signals.py`, `management/commands/import_data.py`, `tests.py`, and the DRF module `api.py`.

`settings.py` lists all three middleware forms in `MIDDLEWARE` and keeps one intentionally unused setting. `urls.py` defines `app_name`, `urlpatterns`,
a DRF router registration, and one intentionally unused URLconf variable. `views.py` defines function views, the three `@require_*` decorators, a
decorated helper that no URLconf loads, `ListView`, `DetailView`, and `View` subclasses, and intentionally unused definitions. `middleware.py` contains
the function factory, the current class form, the `MiddlewareMixin` form, and `UnusedMiddleware`. `models.py` defines a `Category`/`Article` pair with
fields, nested `Meta` classes, and properties. `managers.py` defines a custom `QuerySet` and manager. `migrations/0001_initial.py` is a generated-style
migration. `templatetags/blog_tags.py` registers a simple tag and a filter. `forms.py` defines a `ModelForm` with a nested `Meta` and a validation hook.
`import_forms.py` shows the dotted and directly imported model bases and the qualified and bare admin and receiver decorators. `admin.py` registers an
`ArticleAdmin` with options and an action method. `apps.py` defines a `BlogConfig` with `default_auto_field` and a `ready()` hook. `signals.py` defines a
decorated handler, a directly connected handler, and an unconnected handler. `management/commands/import_data.py` defines a `Command` with `help`,
`add_arguments()`, and `handle()`. `tests.py` defines a `TestCase` with Django's five lifecycle hooks and one unused helper. `api.py` defines a
`ModelSerializer`, a `ModelViewSet` with an `@action` method and the router-called methods, an `@api_view` function with `@permission_classes`, and
intentionally unused code.

Without configuration, the settings and URLconf variables, the legacy middleware hook, the unregistered middleware class, the class-based view handlers,
the registered template tags, the form fields and validation hooks, the admin options and action method, the application configuration, the management
command members, the decorated signal handler, the import forms, and the DRF serializer, action, and function view are reported together with the
intentionally unused code. The registered middleware names are not reported, because deadcode parses `MIDDLEWARE`. The test lifecycle hooks are also
not reported, because deadcode ignores them by default in test files:

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
project/api.py:10:4: DC03 Class `Meta` is never used
project/api.py:11:8: DC06 Name `model` is never used
project/api.py:12:8: DC06 Name `fields` is never used
project/api.py:17:4: DC06 Name `serializer_class` is never used
project/api.py:20:4: DC04 Method `publish` is never used
project/api.py:29:4: DC04 Method `retrieve` is never used
project/api.py:35:4: DC04 Method `destroy` is never used
project/api.py:41:0: DC02 Function `article_stats` is never used
project/api.py:45:0: DC02 Function `unused_api_helper` is never used
project/apps.py:4:0: DC03 Class `BlogConfig` is never used
project/apps.py:5:4: DC06 Name `default_auto_field` is never used
project/apps.py:8:4: DC04 Method `ready` is never used
project/forms.py:7:4: DC03 Class `Meta` is never used
project/forms.py:8:8: DC06 Name `model` is never used
project/forms.py:9:8: DC06 Name `fields` is never used
project/forms.py:11:4: DC04 Method `clean_title` is never used
project/forms.py:15:0: DC03 Class `UnusedForm` is never used
project/import_forms.py:14:0: DC03 Class `QualifiedModel` is never used
project/import_forms.py:18:0: DC03 Class `ImportedForm` is never used
project/import_forms.py:23:0: DC03 Class `QualifiedAdmin` is never used
project/import_forms.py:28:0: DC03 Class `BareAdmin` is never used
project/import_forms.py:33:0: DC02 Function `imported_receiver` is never used
project/management/commands/import_data.py:4:0: DC03 Class `Command` is never used
project/management/commands/import_data.py:5:4: DC06 Name `help` is never used
project/management/commands/import_data.py:7:4: DC04 Method `add_arguments` is never used
project/management/commands/import_data.py:10:4: DC04 Method `handle` is never used
project/management/commands/import_data.py:14:0: DC03 Class `UnusedCommand` is never used
project/management/commands/import_data.py:15:4: DC04 Method `handle` is never used
project/managers.py:13:4: DC04 Method `unused_manager_method` is never used
project/middleware.py:20:4: DC04 Method `process_request` is never used
project/middleware.py:24:0: DC03 Class `UnusedMiddleware` is never used
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
project/settings.py:11:0: DC01 Variable `MIDDLEWARE` is never used
project/settings.py:18:0: DC01 Variable `TEMPLATES` is never used
project/settings.py:30:0: DC01 Variable `DATABASES` is never used
project/settings.py:36:0: DC01 Variable `ROOT_URLCONF` is never used
project/settings.py:38:0: DC01 Variable `UNUSED_SETTING` is never used
project/signals.py:8:0: DC02 Function `article_saved` is never used
project/signals.py:19:0: DC02 Function `unused_signal_handler` is never used
project/templatetags/blog_tags.py:7:0: DC02 Function `greeting` is never used
project/templatetags/blog_tags.py:12:0: DC02 Function `shout` is never used
project/templatetags/blog_tags.py:16:0: DC02 Function `unused_tag` is never used
project/tests.py:26:4: DC04 Method `unused_test_helper` is never used
project/urls.py:7:0: DC01 Variable `app_name` is never used
project/urls.py:12:0: DC01 Variable `urlpatterns` is never used
project/urls.py:21:0: DC01 Variable `UNUSED_URL_NAME` is never used
project/views.py:6:0: DC01 Variable `UNUSED_VIEW_SETTING` is never used
project/views.py:13:0: DC02 Function `unused_view` is never used
project/views.py:33:0: DC02 Function `unreferenced_require_view` is never used
project/views.py:37:0: DC03 Class `ArticleListView` is never used
project/views.py:38:4: DC04 Method `get` is never used
project/views.py:42:0: DC03 Class `ArticleDetailView` is never used
project/views.py:43:4: DC04 Method `get` is never used
project/views.py:48:4: DC04 Method `get` is never used
project/views.py:52:0: DC03 Class `UnusedView` is never used
project/views.py:53:4: DC04 Method `get` is never used
```

With the recommended configuration, only deliberately unused code and the unregistered middleware remain:

```text
project/api.py:45:0: DC02 Function `unused_api_helper` is never used
project/managers.py:13:4: DC04 Method `unused_manager_method` is never used
project/middleware.py:24:0: DC03 Class `UnusedMiddleware` is never used
project/signals.py:19:0: DC02 Function `unused_signal_handler` is never used
project/templatetags/blog_tags.py:16:0: DC02 Function `unused_tag` is never used
project/tests.py:26:4: DC04 Method `unused_test_helper` is never used
project/views.py:6:0: DC01 Variable `UNUSED_VIEW_SETTING` is never used
project/views.py:13:0: DC02 Function `unused_view` is never used
```

The intentionally unused classes `UnusedModel`, `UnusedAdmin`, `UnusedForm`, `UnusedCommand`, and `UnusedView` are not in the second report, because the
definition options hide a matching class name together with its body. `UnusedMiddleware` remains because it is not registered in `MIDDLEWARE`. The
registered middleware names and the class-based view handlers disappear, as do the settings and URLconf variables, the template tags, the form and admin
definitions, the app configuration, the management command, the decorated signal handler, the import forms, and the DRF definitions.

## Verifying the recommended configuration

To reproduce the reports, copy the fixture, write the recommended block, and run deadcode:

```shell
rm -rf /tmp/deadcode-django-example
mkdir -p /tmp/deadcode-django-example
cp -r tests/files/django /tmp/deadcode-django-example/project
cat > /tmp/deadcode-django-example/pyproject.toml <<'EOF'
[tool.deadcode]
ignore-definitions-if-decorated-with = [
    "@django.contrib.admin.*",
    "@django.contrib.auth.*",
    "@django.dispatch.receiver",
    "@django.utils.decorators.method_decorator",
    "@django.views.decorators.http.require_*",
    "@rest_framework.*",
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
    "rest_framework.*View",
    "rest_framework.*ViewSet",
    "rest_framework.*Serializer",
    "rest_framework.*Permission",
    "rest_framework.*Authentication",
    "rest_framework.*Pagination",
    "rest_framework.*FilterBackend",
    "rest_framework.*Throttle",
]
ignore-names-in-files = ["*/settings.py", "*/urls.py"]
EOF
cd /tmp/deadcode-django-example
deadcode project --no-color
```

The unconfigured run reports the first block and exits with status `1`. Removing `pyproject.toml` restores that output. With the file in place, the
command reports only the second block and still exits with status `1`, because real dead code remains in the example. A project with no findings exits
with status `0`.

If a framework entry point is still reported, compare its decorator, base class, or file path with the patterns above. Use the table in this page to find
the missing family, add the narrowest matching pattern, and run the command again.

## Limitations

- Relative and dynamic imports are not resolved. `from .models import Model` and `from . import models` keep working through a bare or wildcard
  expression, but they do not match a module-qualified pattern such as `django.db.models.Model`. An import inside a function is outside the module-level
  map, and `importlib`, `getattr`, string paths, and code generation cannot be seen by a static analyser.
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
