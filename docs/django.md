# Django

deadcode is framework-agnostic: it parses source code and never imports it. Django registers models, views, admin classes, middleware, and signal
handlers at runtime, so much of a Django project's code is reachable only through a base class, a decorator, a settings string, or a URLconf. A static
analyser that only follows name loads sees those framework entry points as unused. This page shows one small configuration for Django and Django REST
Framework, documents the current middleware forms and both import forms, and gives a complete example application whose reports you can reproduce.

## Recommended configuration

Add these four option keys to `pyproject.toml` in the directory where you run deadcode:

```toml
[tool.deadcode]
ignore-definitions-if-decorated-with = [
    "@*admin.*",
    "@*register",
    "@*display",
    "@*action",
    "@*receiver",
    "@*register.*",
    "@*require_*",
    "@*login_required",
    "@*permission_required",
    "@*user_passes_test",
    "@*method_decorator",
    "@*api_view",
    "@*_classes",
    "@*schema",
]
ignore-definitions-if-inherits-from = [
    "Model",
    "ModelAdmin",
    "Form",
    "ModelForm",
    "*Inline",
    "BaseCommand",
    "Migration",
    "AppConfig",
    "MiddlewareMixin",
    "*View",
    "*ViewSet",
    "*Serializer",
    "*Permission",
    "*Authentication",
    "*Pagination",
    "*FilterBackend",
    "*Throttle",
]
ignore-names = ["*Middleware", "*middleware"]
ignore-names-in-files = ["*/settings.py", "*/urls.py"]
```

Every entry has one job. `ignore-definitions-if-inherits-from` suppresses the name and the whole body of a framework subclass, so one `Model` entry
replaces a model-name pattern, a field pattern, and a nested-`Meta` pattern. `ignore-definitions-if-decorated-with` does the same for a decorated
definition, so one `@*receiver` entry covers the handler name and its body. `ignore-names` covers the two middleware forms that have no framework base
class. `ignore-names-in-files` covers settings and URLconf modules, whose module-level names are configuration data rather than ordinary code.

The same options are available as command-line flags, with one occurrence per value:

```shell
deadcode . \
    --ignore-definitions-if-decorated-with=@*admin.* \
    --ignore-definitions-if-decorated-with=@*register \
    --ignore-definitions-if-decorated-with=@*display \
    --ignore-definitions-if-decorated-with=@*action \
    --ignore-definitions-if-decorated-with=@*receiver \
    --ignore-definitions-if-decorated-with=@*register.* \
    --ignore-definitions-if-decorated-with=@*require_* \
    --ignore-definitions-if-decorated-with=@*login_required \
    --ignore-definitions-if-decorated-with=@*permission_required \
    --ignore-definitions-if-decorated-with=@*user_passes_test \
    --ignore-definitions-if-decorated-with=@*method_decorator \
    --ignore-definitions-if-decorated-with=@*api_view \
    --ignore-definitions-if-decorated-with=@*_classes \
    --ignore-definitions-if-decorated-with=@*schema \
    --ignore-definitions-if-inherits-from=Model \
    --ignore-definitions-if-inherits-from=ModelAdmin \
    --ignore-definitions-if-inherits-from=Form \
    --ignore-definitions-if-inherits-from=ModelForm \
    --ignore-definitions-if-inherits-from='*Inline' \
    --ignore-definitions-if-inherits-from=BaseCommand \
    --ignore-definitions-if-inherits-from=Migration \
    --ignore-definitions-if-inherits-from=AppConfig \
    --ignore-definitions-if-inherits-from=MiddlewareMixin \
    --ignore-definitions-if-inherits-from='*View' \
    --ignore-definitions-if-inherits-from='*ViewSet' \
    --ignore-definitions-if-inherits-from='*Serializer' \
    --ignore-definitions-if-inherits-from='*Permission' \
    --ignore-definitions-if-inherits-from='*Authentication' \
    --ignore-definitions-if-inherits-from='*Pagination' \
    --ignore-definitions-if-inherits-from='*FilterBackend' \
    --ignore-definitions-if-inherits-from='*Throttle' \
    --ignore-names='*Middleware' \
    --ignore-names='*middleware' \
    --ignore-names-in-files='*/settings.py' \
    --ignore-names-in-files='*/urls.py'
```

A list flag accepts space-separated values, repeated flags, and one comma-separated value. The comma form is shorter to type:

```shell
deadcode . \
    --ignore-definitions-if-decorated-with='@*admin.*,@*register,@*display,@*action,@*receiver,@*register.*,@*require_*,@*login_required,@*permission_required,@*user_passes_test,@*method_decorator,@*api_view,@*_classes,@*schema' \
    --ignore-definitions-if-inherits-from='Model,ModelAdmin,Form,ModelForm,*Inline,BaseCommand,Migration,AppConfig,MiddlewareMixin,*View,*ViewSet,*Serializer,*Permission,*Authentication,*Pagination,*FilterBackend,*Throttle' \
    --ignore-names='*Middleware,*middleware' \
    --ignore-names-in-files='*/settings.py,*/urls.py'
```

The comma is the only separator. `|` is not a separator. A TOML array is not comma-split either: write one quoted value per line, because
`["Model,Form"]` is the single literal pattern `Model,Form`. deadcode reads `./pyproject.toml` in the current working directory; it does not search parent
directories and there is no `--config` option. See {doc}`usage` for the full option semantics and {doc}`rules` for the rule codes.

## Common use cases

| Django part | Configuration entry |
|-------------|---------------------|
| Models and migrations | `Model` and `Migration` in `ignore-definitions-if-inherits-from`, plus `*/settings.py` and `*/urls.py` in `ignore-names-in-files` |
| URLs and settings | `ignore-names-in-files = ["*/settings.py", "*/urls.py"]` |
| Function and class-based views | `@*require_*`, `@*login_required`, `@*permission_required`, `@*user_passes_test`, and `@*method_decorator`; `*View` for every generic view |
| Middleware | `ignore-names = ["*Middleware", "*middleware"]` and `MiddlewareMixin` in the inheritance list |
| Templates and template tags | `@*register` and `@*register.*` |
| Forms and model forms | `Form` and `ModelForm` in the inheritance list |
| Admin classes and actions | `@*admin.*`, `@*register`, `@*display`, and `ModelAdmin` in the inheritance list |
| App configurations | `AppConfig` in the inheritance list |
| Management commands | `BaseCommand` in the inheritance list |
| Signals | `@*receiver` |
| Tests | No entry; the Django test lifecycle names are ignored by default in test files |
| Django REST Framework | `*ViewSet`, `*Serializer`, `*Permission`, `*Authentication`, `*Pagination`, `*FilterBackend`, `*Throttle`, `@*api_view`, `@*action`, `@*_classes`, and `@*schema` |
| Auth, security, i18n, caching, GIS, and the remaining core tools | The same four keys; their ordinary function and class references need no extra entry |

## Versions

The example targets Django 5.2 LTS, latest patch release 5.2.19, and Django REST Framework 3.18.3. Django 5.2 is the newest LTS release that runs on
the project's minimum Python 3.10 and is supported until April 2028; Django REST Framework 3.18.3 requires Django 5.2 or newer. The example uses APIs that
are present in Django 5.2 through 6.1, so a project on any of those releases can copy the configuration. Django 6.1 requires Python 3.12 or newer, while
deadcode itself supports Python 3.10 and later, which is why the example pins the LTS line.

The fixture is parsed as text and never executed. Django and Django REST Framework are not dependencies of deadcode, and the tests do not import either
framework. The version statement describes the APIs in the snippets, not a runtime requirement of the analyser.

## Model layer

Models are the largest source of Django false positives. A field and a nested `Meta` option are class-level assignments with no Python name load, and
Django calls model methods and properties at runtime. `Model` in `ignore-definitions-if-inherits-from` removes the class name and every finding in the
body in one entry.

```python
from django.db import models

from .managers import ArticleManager


class Category(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        verbose_name_plural = 'categories'

    def __str__(self):
        return self.name


class Article(models.Model):
    title = models.CharField(max_length=100)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='articles')
    published = models.BooleanField(default=False)

    objects = ArticleManager()

    class Meta:
        ordering = ['title']

    @property
    def display_name(self):
        return self.title


class UnusedModel(models.Model):
    value = models.IntegerField()
```

Without configuration the nested `Meta` classes are `DC03`, `verbose_name_plural`, `ordering`, and `category` are `DC06`, and `display_name` and
`published_titles` are `DC08`. With the recommended configuration none of those appear. The same `Model` entry also suppresses the `UnusedModel` class
name, which is a deliberate trade-off: the definition option hides a genuinely unused model as well as the framework fields. Use
`ignore-bodies-if-inherits-from = ["Model"]` instead when unused model names must stay visible, or mark
the definition with `# noqa: DC03`.

### Both import forms

An inheritance expression matches the dotted base and its final component. Research with the analyser shows that `models.Model` contributes both the
dotted name and `Model`, so the plain `Model` entry covers both forms without a second, overlapping entry:

```python
from django.db import models
from django.db.models import Model


class QualifiedModel(models.Model):
    title = models.CharField(max_length=100)


class ImportedModel(Model):
    title = models.CharField(max_length=100)
```

An alias is not resolved. `import django.db.models as m` followed by `class Article(m.Model)` and
`from django.db.models import Model as M` followed by `class Article(M)` do not match the `Model` entry. Use the unaliased import or add a pattern for the
alias.

Custom managers and `QuerySet` subclasses are not `Model` subclasses. `ArticleManager` and `ArticleQuerySet` are ordinary classes; a method that only
other code calls is still reported. Add the manager base to the inheritance list when its whole body should be ignored, or mark the individual method with
`# noqa: DC04`. Migrations are covered by `Migration` in the inheritance list, so `initial`, `dependencies`, and `operations` disappear without a
separate `*/migrations/*` file pattern.

## URLs and settings

Settings and URLconf modules are configuration data. `SECRET_KEY`, `DEBUG`, `INSTALLED_APPS`, `MIDDLEWARE`, `TEMPLATES`, `DATABASES`,
`ROOT_URLCONF`, `app_name`, `urlpatterns`, and route name constants are module-level names that nothing in the project loads. The file patterns remove
them:

```python
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views
from .api import ArticleViewSet

app_name = 'django_example'

router = DefaultRouter()
router.register(r'articles', ArticleViewSet, basename='article')

urlpatterns = [
    path('', views.index, name='index'),
    path('articles/', views.article_list, name='article-list'),
    path('api/', include(router.urls)),
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
through a string, a dynamic import, or code outside the analysed tree looks unused. Decorator wildcards cover the definition and its body:

| Decorator family | Entry | Notes |
|------------------|-------|-------|
| `@require_GET`, `@require_POST`, `@require_safe`, `@require_http_methods` | `@*require_*` | Django has no `require_PUT`; use `@require_http_methods(['PUT'])` for the other methods |
| `@login_required`, `@permission_required`, `@user_passes_test` | `@*login_required`, `@*permission_required`, `@*user_passes_test` | The auth decorators in bare and qualified form |
| `@method_decorator` | `@*method_decorator` | Applies a decorator to a class-based view method |
| `@admin.register`, `@register`, `@register.simple_tag`, `@register.filter` | `@*admin.*`, `@*register`, `@*register.*` | The leading `@*` covers a dotted and a directly imported name |

Class-based views are covered by inheritance. `*View` matches `View`, `TemplateView`, `RedirectView`, `DetailView`, `ListView`, `FormView`, `CreateView`,
`UpdateView`, `DeleteView`, the archive views, and DRF `APIView` descendants. `View` alone does not match `ListView` or `DetailView`, which is why the
family pattern is used:

```python
from django.http import HttpResponse
from django.views import View
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.views.generic import DetailView, ListView


@require_GET
def article_list(request):
    return HttpResponse('articles')


@require_POST
def article_create(request):
    return HttpResponse('created')


@require_http_methods(['PUT'])
def article_update(request):
    return HttpResponse('updated')


class ArticleListView(ListView):
    def get(self, request):
        return HttpResponse('articles')


class ArticleDetailView(DetailView):
    def get(self, request):
        return HttpResponse('article')


class ArticleView(View):
    def get(self, request):
        return HttpResponse('article')
```

Without configuration the handlers are `DC04`, `ArticleListView` and `ArticleDetailView` are `DC03`, and a decorated function that no URLconf loads is
`DC02`. With the configuration every one of those findings disappears. The `View`/`ListView`/`DetailView` class name is suppressed too, because the
definition option hides the whole definition.

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

Both are current in Django 5.2 through 6.1. `__init__` and `__call__` are dunder methods, which the analyser ignores already. The two middleware
names have no framework base class, which is why `ignore-names = ["*Middleware", "*middleware"]` removes `simple_middleware` and
`CurrentMiddleware`. The function name itself is the settings string, so the name pattern is the only way to keep it while `MIDDLEWARE` names it as text.

`MiddlewareMixin` from `django.utils.deprecation` is the pre-Django-1.10 compatibility form. Django still supports it and does not warn about it, so it
is not deprecated, but new middleware should use one of the two forms above. When an existing project uses it, the inheritance entry covers the
`process_request` and `process_response` hooks:

```python
from django.utils.deprecation import MiddlewareMixin


class SimpleMiddleware(MiddlewareMixin):
    def process_request(self, request):
        return None
```

`MiddlewareMixin` in `ignore-definitions-if-inherits-from` removes the class name and `process_request` together. Without configuration the example
reports `simple_middleware`, `CurrentMiddleware`, `SimpleMiddleware`, and `process_request`; with the configuration none of them appear.

## Template layer

The template language is data, not Python. deadcode does not parse templates, so a context variable, a `{% url %}` reference, or a filter used only in an
HTML file is invisible. Built-in tags such as `{% for %}`, `{% if %}`, and `{{ value|date }}` need no configuration because deadcode never sees them.
The `TEMPLATES` setting and the backend class are covered by the settings file pattern.

Custom tags and filters are registered at import time and are covered by the `@*register` and `@*register.*` entries:

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

A context processor is named only as a string in the `TEMPLATES` setting. Mark its definition with `# noqa: DC02` or add its name to `ignore-names`;
a project-wide name entry is broader than one `# noqa` comment when several context processors are genuinely reachable.

## Forms

Django forms declare fields as class attributes, and a `ModelForm` reads its model and field list from a nested `Meta` class. Validation hooks are called
by name after the form is bound. `Form` and `ModelForm` in `ignore-definitions-if-inherits-from` remove the class name, the nested `Meta`, the field
names, and the hooks in one entry:

```python
from django import forms

from .models import Article


class ArticleForm(forms.ModelForm):
    class Meta:
        model = Article
        fields = ['title', 'category']

    def clean_title(self):
        return self.cleaned_data['title'].strip()


class UnusedForm(forms.Form):
    name = forms.CharField(max_length=100)
```

Without configuration the example reports `Meta`, `model`, `fields`, and `clean_title`, and `UnusedForm` is `DC03`; with the configuration none of them
appear. The same `Model` and `Form` matching rules apply to the dotted and directly imported base, so `forms.Form` and a bare `Form` both match.

Formsets are created with `formset_factory()`, and their `clean()` method is an ordinary method on the form. Custom validators are ordinary functions;
a validator named only as a string in a field definition needs a name load, `ignore-names`, or `# noqa`.

## Admin

The admin site discovers `ModelAdmin` subclasses when it imports a project's `admin` module. `@admin.register`, `@register`, and `@admin.display` are
covered by the decorator entries; the options and action methods are covered by `ModelAdmin` in the inheritance list:

```python
from django.contrib import admin

from .forms import ArticleForm
from .models import Article


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    form = ArticleForm
    list_display = ('title', 'published')
    search_fields = ('title',)
    list_filter = ('published',)
    actions = ('mark_featured',)

    def mark_featured(self, request, queryset):
        queryset.update(featured=True)


class UnusedAdmin(admin.ModelAdmin):
    list_display = ('title',)
```

The `actions` tuple contains the action names as strings, so deadcode does not analyse `'mark_featured'`; the method is covered by the
`ModelAdmin` body rule instead. Without configuration the example reports `ArticleAdmin`, `form`, `list_display`, `search_fields`, `list_filter`,
`actions`, `mark_featured`, and `UnusedAdmin` plus its `list_display`; with the configuration none of them appear. Inline classes inherit
`InlineModelAdmin` rather than `ModelAdmin`, so `*Inline` covers `StackedInline` and `TabularInline` and their options.

## App configs and management commands

`AppConfig` subclasses are discovered through the dotted string in `INSTALLED_APPS`. `BaseCommand` subclasses are imported by convention from a
`management/commands` package. `AppConfig` and `BaseCommand` in the inheritance list cover the class name, `default_auto_field`, `name`, `ready`,
`help`, `add_arguments()`, and `handle()` in one entry each:

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

No `*Config`, `*Middleware`, or `Command` name pattern is needed. The inheritance entries already hide the class name and body, so the earlier set's
`ignore-definitions = ["*Config", "*Middleware", "Command"]` was redundant and has been removed. A helper command class with another base class is still
reported unless it has a name load or its own inheritance entry.

`manage.py` and `django-admin` are ordinary scripts. The settings module and application entry points they name are strings, so deadcode never sees those
loads; the settings file pattern covers the settings module. Deployment modules that assign `application` need the file pattern or `# noqa: DC01`.

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

Without configuration the decorated `article_saved` is `DC02` because a decorator does not create a name load. The direct form needs no configuration:
`article_saved_direct` is an ordinary name load in the `post_save.connect(...)` call. The unbound `unused_signal_handler` is `DC02` and remains after the
configuration. `@*receiver` covers the decorated handler and its body, and because it starts with `@*` it matches both `@receiver` and
`@django.dispatch.receiver`. The database signals `pre_save`, `post_save`, `pre_delete`, and `post_delete` all use the same rule.

## Tests

Django's `TestCase` lifecycle methods are called by the framework, not by project code. deadcode ignores `setUpTestData`, `_pre_setup`,
`_post_teardown`, `_fixture_setup`, and `_fixture_teardown` by default in test files, so the recommended configuration needs no entry for them. A genuine
helper whose name is not a lifecycle name is still reported:

```python
from django.test import TestCase

from .models import Article


class ArticleTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.article = Article.objects.create(title='Example')

    def _pre_setup(self):
        pass

    def test_article(self):
        assert self.article.title == 'Example'

    def unused_test_helper(self):
        return None
```

`setUpTestData`, `_pre_setup`, and the other lifecycle hooks produce no finding. `unused_test_helper` is `DC04` and remains after the configuration.
Django test helpers that the test calls itself, such as `assertContains`, `assertNumQueries`, `settings`, and `modify_settings`, are ordinary name loads and
need no configuration. `pytest-django` fixtures and `unittest` lifecycle methods follow the same rule as ordinary Python code.

## Django REST Framework

Django REST Framework needs the class families and the policy decorators. `*ViewSet` covers `ViewSet`, `GenericViewSet`, `ModelViewSet`, and
`ReadOnlyModelViewSet`; `*Serializer` covers `Serializer`, `ModelSerializer`, and `HyperlinkedModelSerializer`; `*Permission`, `*Authentication`,
`*Pagination`, `*FilterBackend`, and `*Throttle` cover the extension classes. `@*api_view`, `@*action`, `@*_classes` (policy decorators such as
`@permission_classes` and `@authentication_classes`), and `@*schema` cover the decorators:

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


def unused_api_helper(request):
    return Response({})
```

Routers call `list`, `create`, `retrieve`, `update`, `partial_update`, and `destroy` by name, and no Python code loads those methods in a typical
project; `*ViewSet` removes the body findings. `serializer_class`, the nested serializer `Meta`, `model`, and `fields` disappear with `*Serializer` and
`*ViewSet`. `@*action` covers `publish`, `@*api_view` covers `article_stats`, and `@*_classes` covers `@permission_classes`. `unused_api_helper` is
genuinely unused and remains `DC02`.

The `IsAuthenticated` class is loaded by the decorator argument, so permissions do not need a name entry. A custom permission, authentication,
pagination, filter backend, or throttle class is covered by the matching family pattern when its name ends with the family suffix; a differently named
base class needs its own inheritance entry. A serializer used only through a string or a dynamic lookup needs a name load or `# noqa`.

## Remaining framework areas

The same four keys cover the rest of Django. Settings for auth and security (`SECRET_KEY`, `ALLOWED_HOSTS`, `SECURE_*`, `CSRF_*`, `SESSION_COOKIE_*`),
i18n (`LANGUAGES`, `LOCALE_PATHS`, `USE_I18N`), caching (`CACHES`, `CACHE_*`), and GIS (`GDAL_LIBRARY_PATH`, `GEOS_LIBRARY_PATH`) are settings
assignments covered by `*/settings.py`. The auth decorators `@login_required`, `@permission_required`, and `@user_passes_test` are covered by their
entries. `gettext`, `gettext_lazy`, `ngettext`, `cache.get`, `select_related`, `prefetch_related`, `signing.dumps`, and `timezone.localtime` are
ordinary calls and name loads.

GeoDjango models are still `Model` subclasses and spatial fields are still fields, so the model entry applies. A custom `GeoManager` or `GeoQuerySet`
follows the manager rule. A custom cache backend, storage class, template backend, or database engine named only through a string needs a name load,
`ignore-names`, or `# noqa`. Built-in Django classes and functions are never analysed because deadcode only reads the project's source tree.

## Example application

The acceptance fixture in `tests/files/django` is a small multi-module Django application. It uses `settings.py`, `urls.py`, `views.py`,
`middleware.py`, `models.py`, `managers.py`, `migrations/0001_initial.py`, `templatetags/blog_tags.py`, `forms.py`, `import_forms.py`,
`admin.py`, `apps.py`, `signals.py`, `management/commands/import_data.py`, `tests.py`, and the DRF module `api.py`.

`settings.py` defines the usual module-level settings, lists `rest_framework` and `project.apps.BlogConfig`, and names all three middleware forms in
`MIDDLEWARE`, plus one intentionally unused setting. `urls.py` defines `app_name`, `urlpatterns`, a DRF router registration, and one intentionally unused
URLconf variable. `views.py` defines function views, the three `@require_*` decorators, a decorated helper that no URLconf loads, `ListView`,
`DetailView`, and `View` subclasses, one intentionally unused setting, one intentionally unused function, and one intentionally unused class. `middleware.py`
contains the function factory, the current class form, and the `MiddlewareMixin` form. `models.py` defines a `Category`/`Article` pair with fields, nested
`Meta` classes, and properties, plus one intentionally unused model. `managers.py` defines a custom `QuerySet` and manager with one intentionally unused
manager method. `migrations/0001_initial.py` is a generated-style migration. `templatetags/blog_tags.py` registers a simple tag and a filter and leaves one
intentionally unused function. `forms.py` defines a `ModelForm` with a nested `Meta` and a validation hook, plus one intentionally unused form.
`import_forms.py` shows the dotted and directly imported model bases and the qualified and bare admin and receiver decorators. `admin.py` registers an
`ArticleAdmin` with options and an action method, plus one intentionally unused admin class. `apps.py` defines a `BlogConfig` with `default_auto_field`
and a `ready()` hook. `signals.py` defines a decorated handler, a directly connected handler, and one intentionally unused handler.
`management/commands/import_data.py` defines a `Command` with `help`, `add_arguments()`, and `handle()`, plus one intentionally unused command.
`tests.py` defines a `TestCase` with Django's five lifecycle hooks, a real test, and one intentionally unused helper. `api.py` defines a
`ModelSerializer`, a `ModelViewSet` with an `@action` method and the router-called methods, an `@api_view` function with `@permission_classes`, and one
intentionally unused helper.

Without configuration, the settings and URLconf variables, the three middleware forms and the legacy hook, the class-based view handlers, the registered
template tags, the form fields and validation hooks, the admin options and action method, the application configuration, the management command members,
the decorated signal handlers, the import forms, and the DRF serializer, action, and function view are reported together with the intentionally unused
code. The test lifecycle hooks are not reported, because deadcode ignores them by default in test files:

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
project/middleware.py:4:0: DC02 Function `simple_middleware` is never used
project/middleware.py:11:0: DC03 Class `CurrentMiddleware` is never used
project/middleware.py:19:0: DC03 Class `SimpleMiddleware` is never used
project/middleware.py:20:4: DC04 Method `process_request` is never used
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

With the recommended configuration, only deliberately unused code remains. The settings and URLconf variables, the middleware names, class-based view
names and handlers, template tags, form and admin definitions, app configuration, management command, decorated signals, import forms, and DRF
definitions disappear. The final report is:

```text
project/api.py:45:0: DC02 Function `unused_api_helper` is never used
project/managers.py:13:4: DC04 Method `unused_manager_method` is never used
project/signals.py:19:0: DC02 Function `unused_signal_handler` is never used
project/templatetags/blog_tags.py:16:0: DC02 Function `unused_tag` is never used
project/tests.py:26:4: DC04 Method `unused_test_helper` is never used
project/views.py:6:0: DC01 Variable `UNUSED_VIEW_SETTING` is never used
project/views.py:13:0: DC02 Function `unused_view` is never used
```

The intentionally unused classes `UnusedModel`, `UnusedAdmin`, `UnusedForm`, `UnusedCommand`, and `UnusedView` are not in the second report. That is the
documented behaviour of the definition options: `ignore-definitions-if-inherits-from` hides a matching class name as well as its body. The remaining
seven findings are definitions that do not inherit from a framework base and are not decorated, so the four keys do not cover them.

## Verifying the recommended configuration

Copy the configuration into `pyproject.toml`, then run:

```shell
deadcode . --no-color
```

The command exits with status `1` while real dead code remains and `0` once the application has none. If a framework entry point is still reported,
compare its decorator, base class, or file path with the patterns above. Use the category order in this page to find the missing entry, add the
narrowest matching pattern, and run the command again. To reproduce the example, copy `tests/files/django` to a temporary `project/` directory, run
`deadcode project --no-color` without a `pyproject.toml`, then write the recommended block and run the same command again; the two reports must match the
blocks in this page byte for byte.

## Limitations

- deadcode does not detect Django automatically. Configuration is explicit and applies to any framework that uses decorators, base classes, and file
  conventions.
- Alias imports are not resolved. `import django.db.models as m`, `from django.db.models import Model as M`, and an aliased decorator such as
  `from django.dispatch import receiver as r` do not match the unaliased patterns until the alias or a dedicated pattern is added.
- Definition options hide names. `ignore-definitions-if-inherits-from` and `ignore-definitions-if-decorated-with` suppress the class or function name
  together with its body, so a genuinely unused Django subclass is not reported. Use the narrower `ignore-bodies-if-inherits-from` or
  `ignore-names-if-decorated-with` when the names must remain visible, or mark the definition with `# noqa`.
- String references are invisible. `MIDDLEWARE`, `TEMPLATES`, `ROOT_URLCONF`, `INSTALLED_APPS`, context processors, storage backends, cache backends,
  and WSGI or ASGI application paths are strings, so the referenced code needs a name load, a file pattern, or `# noqa`.
- Dynamic registration through `getattr`, `importlib`, string paths, or code generation cannot be seen by a static analyser.
- A different decorator or base-class spelling needs its own pattern. A custom admin decorator, a custom permission base, or a project-specific generic
  view that does not end in `View`, `ViewSet`, or `Serializer` is not covered until the pattern or the name is added.
- The comma is the only command-line list separator. A pipe such as `@admin.*|@receiver|@register.*` is one literal pattern and matches nothing useful;
  use separate flags or a comma-separated value instead.
- The recommended set intentionally stays small rather than complete. Add an entry only for the finding in front of you, and prefer the narrowest
  decorator or base-class pattern that covers it.
