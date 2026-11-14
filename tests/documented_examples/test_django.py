import re
import shutil

from pathlib import Path

from deadcode.cli import main, print_main

FIXTURE_DIRECTORY = Path(__file__).resolve().parents[1] / 'files' / 'django'

DJANGO_DECORATOR_PATTERNS = [
    '@django.contrib.admin.*',
    '@django.contrib.auth.*',
    '@django.dispatch.receiver',
    '@django.utils.decorators.method_decorator',
    '@django.views.decorators.http.require_*',
    '@*register.*',
]

DJANGO_INHERITANCE_PATTERNS = [
    'django.apps.AppConfig',
    'django.contrib.admin.*',
    'django.core.management.base.BaseCommand',
    'django.db.migrations.Migration',
    'django.db.models.Model',
    'django.forms.*Form',
    'django.utils.deprecation.MiddlewareMixin',
    'django.views.*View',
]

DJANGO_REST_FRAMEWORK_DECORATOR_PATTERNS = ['@rest_framework.*']

DJANGO_REST_FRAMEWORK_INHERITANCE_PATTERNS = [
    'rest_framework.*View',
    'rest_framework.*ViewSet',
    'rest_framework.*Serializer',
    'rest_framework.*Permission',
    'rest_framework.*Authentication',
    'rest_framework.*Pagination',
    'rest_framework.*FilterBackend',
    'rest_framework.*Throttle',
]

FULL_DECORATOR_PATTERNS = DJANGO_DECORATOR_PATTERNS + DJANGO_REST_FRAMEWORK_DECORATOR_PATTERNS

FULL_INHERITANCE_PATTERNS = DJANGO_INHERITANCE_PATTERNS + DJANGO_REST_FRAMEWORK_INHERITANCE_PATTERNS

FILE_PATTERNS = ['*/settings.py', '*/urls.py']


def _configuration(decorator_patterns: list[str], inheritance_patterns: list[str]) -> str:
    return (
        '[tool.deadcode]\n'
        'ignore-definitions-if-decorated-with = [\n'
        + ''.join(f'    "{pattern}",\n' for pattern in decorator_patterns)
        + ']\n'
        'ignore-definitions-if-inherits-from = [\n'
        + ''.join(f'    "{pattern}",\n' for pattern in inheritance_patterns)
        + ']\n'
        'ignore-names-in-files = ["*/settings.py", "*/urls.py"]\n'
    )


DJANGO_CONFIGURATION = _configuration(DJANGO_DECORATOR_PATTERNS, DJANGO_INHERITANCE_PATTERNS)

DJANGO_REST_FRAMEWORK_CONFIGURATION = _configuration(FULL_DECORATOR_PATTERNS, FULL_INHERITANCE_PATTERNS)

COMMAND_LINE_OPTIONS = [
    *(f'--ignore-definitions-if-decorated-with={pattern}' for pattern in FULL_DECORATOR_PATTERNS),
    *(f'--ignore-definitions-if-inherits-from={pattern}' for pattern in FULL_INHERITANCE_PATTERNS),
    *(f'--ignore-names-in-files={pattern}' for pattern in FILE_PATTERNS),
]

COMMA_SEPARATED_COMMAND_LINE_OPTIONS = [
    f'--ignore-definitions-if-decorated-with={",".join(FULL_DECORATOR_PATTERNS)}',
    f'--ignore-definitions-if-inherits-from={",".join(FULL_INHERITANCE_PATTERNS)}',
    f'--ignore-names-in-files={",".join(FILE_PATTERNS)}',
]

FINDING_PATTERN = re.compile(r'^(?P<path>.+):\d+:\d+: (?P<code>DC\d+) \w+ `(?P<name>[^`]+)` is never used$')

# The baseline includes cascade findings: a definition used only by other unused
# definitions is reported in the same run (DEP 3).
BASELINE_FINDINGS = {
    ('project/admin.py', 'DC07', 'ArticleForm'),
    ('project/admin.py', 'DC03', 'ArticleAdmin'),
    ('project/admin.py', 'DC06', 'form'),
    ('project/admin.py', 'DC06', 'list_display'),
    ('project/admin.py', 'DC06', 'search_fields'),
    ('project/admin.py', 'DC06', 'list_filter'),
    ('project/admin.py', 'DC06', 'actions'),
    ('project/admin.py', 'DC04', 'mark_featured'),
    ('project/admin.py', 'DC03', 'UnusedAdmin'),
    ('project/api.py', 'DC03', 'Meta'),
    ('project/api.py', 'DC06', 'model'),
    ('project/api.py', 'DC06', 'fields'),
    ('project/api.py', 'DC06', 'serializer_class'),
    ('project/api.py', 'DC04', 'publish'),
    ('project/api.py', 'DC04', 'list'),
    ('project/api.py', 'DC06', 'queryset'),
    ('project/api.py', 'DC04', 'retrieve'),
    ('project/api.py', 'DC04', 'destroy'),
    ('project/api.py', 'DC02', 'article_stats'),
    ('project/api.py', 'DC02', 'unused_api_helper'),
    ('project/apps.py', 'DC07', 'AppConfig'),
    ('project/apps.py', 'DC03', 'BlogConfig'),
    ('project/apps.py', 'DC06', 'default_auto_field'),
    ('project/apps.py', 'DC04', 'ready'),
    ('project/forms.py', 'DC07', 'forms'),
    ('project/forms.py', 'DC07', 'Article'),
    ('project/forms.py', 'DC03', 'ArticleForm'),
    ('project/forms.py', 'DC03', 'Meta'),
    ('project/forms.py', 'DC06', 'model'),
    ('project/forms.py', 'DC06', 'fields'),
    ('project/forms.py', 'DC04', 'clean_title'),
    ('project/forms.py', 'DC03', 'UnusedForm'),
    ('project/import_forms.py', 'DC07', 'forms'),
    ('project/import_forms.py', 'DC03', 'QualifiedModel'),
    ('project/import_forms.py', 'DC03', 'ImportedForm'),
    ('project/import_forms.py', 'DC03', 'QualifiedAdmin'),
    ('project/import_forms.py', 'DC03', 'BareAdmin'),
    ('project/import_forms.py', 'DC02', 'imported_receiver'),
    ('project/management/commands/import_data.py', 'DC07', 'BaseCommand'),
    ('project/management/commands/import_data.py', 'DC03', 'Command'),
    ('project/management/commands/import_data.py', 'DC06', 'help'),
    ('project/management/commands/import_data.py', 'DC04', 'add_arguments'),
    ('project/management/commands/import_data.py', 'DC04', 'handle'),
    ('project/management/commands/import_data.py', 'DC03', 'UnusedCommand'),
    ('project/managers.py', 'DC04', 'unused_manager_method'),
    ('project/middleware.py', 'DC04', 'process_request'),
    ('project/middleware.py', 'DC03', 'UnusedMiddleware'),
    ('project/migrations/0001_initial.py', 'DC06', 'initial'),
    ('project/migrations/0001_initial.py', 'DC06', 'dependencies'),
    ('project/migrations/0001_initial.py', 'DC06', 'operations'),
    ('project/models.py', 'DC03', 'Meta'),
    ('project/models.py', 'DC06', 'verbose_name_plural'),
    ('project/models.py', 'DC06', 'category'),
    ('project/models.py', 'DC06', 'ordering'),
    ('project/models.py', 'DC08', 'display_name'),
    ('project/models.py', 'DC08', 'published_titles'),
    ('project/models.py', 'DC03', 'UnusedModel'),
    ('project/models.py', 'DC06', 'value'),
    ('project/settings.py', 'DC01', 'SECRET_KEY'),
    ('project/settings.py', 'DC01', 'DEBUG'),
    ('project/settings.py', 'DC01', 'INSTALLED_APPS'),
    ('project/settings.py', 'DC01', 'MIDDLEWARE'),
    ('project/settings.py', 'DC01', 'TEMPLATES'),
    ('project/settings.py', 'DC01', 'DATABASES'),
    ('project/settings.py', 'DC01', 'ROOT_URLCONF'),
    ('project/settings.py', 'DC01', 'UNUSED_SETTING'),
    ('project/signals.py', 'DC02', 'article_saved'),
    ('project/signals.py', 'DC02', 'unused_signal_handler'),
    ('project/templatetags/blog_tags.py', 'DC02', 'greeting'),
    ('project/templatetags/blog_tags.py', 'DC02', 'shout'),
    ('project/templatetags/blog_tags.py', 'DC02', 'unused_tag'),
    ('project/tests.py', 'DC04', 'unused_test_helper'),
    ('project/urls.py', 'DC01', 'app_name'),
    ('project/urls.py', 'DC01', 'urlpatterns'),
    ('project/urls.py', 'DC01', 'UNUSED_URL_NAME'),
    ('project/views.py', 'DC07', 'DetailView'),
    ('project/views.py', 'DC07', 'ListView'),
    ('project/views.py', 'DC01', 'UNUSED_VIEW_SETTING'),
    ('project/views.py', 'DC02', 'unused_view'),
    ('project/views.py', 'DC02', 'unreferenced_require_view'),
    ('project/views.py', 'DC03', 'ArticleListView'),
    ('project/views.py', 'DC04', 'get'),
    ('project/views.py', 'DC03', 'ArticleDetailView'),
    ('project/views.py', 'DC03', 'UnusedView'),
}

CONFIGURED_FINDINGS = {
    ('project/api.py', 'DC02', 'unused_api_helper'),
    ('project/middleware.py', 'DC03', 'UnusedMiddleware'),
    ('project/managers.py', 'DC04', 'unused_manager_method'),
    ('project/signals.py', 'DC02', 'unused_signal_handler'),
    ('project/templatetags/blog_tags.py', 'DC02', 'unused_tag'),
    ('project/tests.py', 'DC04', 'unused_test_helper'),
    ('project/views.py', 'DC01', 'UNUSED_VIEW_SETTING'),
    ('project/views.py', 'DC02', 'unused_view'),
}

DJANGO_CONFIGURED_FINDINGS = CONFIGURED_FINDINGS | {
    ('project/api.py', 'DC03', 'Meta'),
    ('project/api.py', 'DC06', 'model'),
    ('project/api.py', 'DC06', 'fields'),
    ('project/api.py', 'DC06', 'serializer_class'),
    ('project/api.py', 'DC04', 'publish'),
    ('project/api.py', 'DC04', 'retrieve'),
    ('project/api.py', 'DC04', 'destroy'),
    ('project/api.py', 'DC02', 'article_stats'),
}


def _copy_fixture(tmp_path: Path) -> None:
    shutil.copytree(FIXTURE_DIRECTORY, tmp_path / 'project')


def _findings(output: str | None) -> set[tuple[str, str, str]]:
    assert output is not None
    findings = set()
    for line in output.splitlines():
        match = FINDING_PATTERN.match(line)
        assert match is not None, line
        findings.add((match.group('path'), match.group('code'), match.group('name')))
    return findings


def _assert_no_parse_warning(output: str | None) -> None:
    assert output is not None
    assert 'could not parse' not in output


def _configured_findings(tmp_path: Path) -> set[tuple[str, str, str]]:
    (tmp_path / 'pyproject.toml').write_text(DJANGO_CONFIGURATION)
    output = main(['project', '--no-color'])
    _assert_no_parse_warning(output)
    return _findings(output)


def _rest_framework_configured_findings(tmp_path: Path) -> set[tuple[str, str, str]]:
    (tmp_path / 'pyproject.toml').write_text(DJANGO_REST_FRAMEWORK_CONFIGURATION)
    output = main(['project', '--no-color'])
    _assert_no_parse_warning(output)
    return _findings(output)


def test_django_fixture_without_configuration(project_directory: Path) -> None:
    # Having
    _copy_fixture(project_directory)

    # When
    output = main(['project', '--no-color'])

    # Then
    _assert_no_parse_warning(output)
    assert _findings(output) == BASELINE_FINDINGS
    assert print_main(['project', '--no-color']) == 1


def test_django_fixture_with_documented_configuration(project_directory: Path) -> None:
    # Having
    _copy_fixture(project_directory)

    # When
    findings = _configured_findings(project_directory)

    # Then
    assert findings == DJANGO_CONFIGURED_FINDINGS
    assert print_main(['project', '--no-color']) == 1


def test_django_fixture_with_documented_command_line_options(project_directory: Path) -> None:
    # Having
    _copy_fixture(project_directory)

    # When
    output = main(['project', '--no-color', *COMMAND_LINE_OPTIONS])

    # Then
    _assert_no_parse_warning(output)
    assert _findings(output) == CONFIGURED_FINDINGS
    assert print_main(['project', '--no-color', *COMMAND_LINE_OPTIONS]) == 1


def test_django_fixture_with_comma_separated_command_line_options(project_directory: Path) -> None:
    # Having
    _copy_fixture(project_directory)

    # When
    output = main(['project', '--no-color', *COMMA_SEPARATED_COMMAND_LINE_OPTIONS])

    # Then
    _assert_no_parse_warning(output)
    assert _findings(output) == CONFIGURED_FINDINGS


def test_middleware_forms_without_configuration(project_directory: Path) -> None:
    # Having
    _copy_fixture(project_directory)

    # When
    output = main(['project', '--no-color'])

    # Then
    _assert_no_parse_warning(output)
    findings = _findings(output)
    assert {
        ('project/middleware.py', 'DC04', 'process_request'),
        ('project/middleware.py', 'DC03', 'UnusedMiddleware'),
    } <= findings
    assert (
        not {
            ('project/middleware.py', 'DC02', 'simple_middleware'),
            ('project/middleware.py', 'DC03', 'CurrentMiddleware'),
            ('project/middleware.py', 'DC03', 'SimpleMiddleware'),
        }
        & findings
    )


def test_middleware_forms_with_documented_configuration(project_directory: Path) -> None:
    # Having
    _copy_fixture(project_directory)

    # When
    findings = _configured_findings(project_directory)

    # Then
    middleware_findings = {finding for finding in findings if finding[0] == 'project/middleware.py'}
    assert middleware_findings == {('project/middleware.py', 'DC03', 'UnusedMiddleware')}


def test_class_based_view_families_without_configuration(project_directory: Path) -> None:
    # Having
    _copy_fixture(project_directory)

    # When
    output = main(['project', '--no-color'])

    # Then
    _assert_no_parse_warning(output)
    findings = _findings(output)
    assert {
        ('project/views.py', 'DC03', 'ArticleListView'),
        ('project/views.py', 'DC03', 'ArticleDetailView'),
        ('project/views.py', 'DC03', 'UnusedView'),
        ('project/views.py', 'DC04', 'get'),
    } <= findings
    assert any(path == 'project/views.py' and code == 'DC04' and name == 'get' for path, code, name in findings)


def test_class_based_view_families_with_documented_configuration(project_directory: Path) -> None:
    # Having
    _copy_fixture(project_directory)

    # When
    findings = _configured_findings(project_directory)

    # Then
    view_findings = {finding for finding in findings if finding[0] == 'project/views.py'}
    assert view_findings == {
        ('project/views.py', 'DC01', 'UNUSED_VIEW_SETTING'),
        ('project/views.py', 'DC02', 'unused_view'),
    }


def test_decorator_wildcards_without_configuration(project_directory: Path) -> None:
    # Having
    _copy_fixture(project_directory)

    # When
    output = main(['project', '--no-color'])

    # Then
    _assert_no_parse_warning(output)
    findings = _findings(output)
    assert {
        ('project/views.py', 'DC02', 'unreferenced_require_view'),
        ('project/import_forms.py', 'DC02', 'imported_receiver'),
        ('project/import_forms.py', 'DC03', 'QualifiedAdmin'),
        ('project/import_forms.py', 'DC03', 'BareAdmin'),
        ('project/api.py', 'DC02', 'article_stats'),
        ('project/api.py', 'DC04', 'publish'),
    } <= findings


def test_decorator_wildcards_with_documented_configuration(project_directory: Path) -> None:
    # Having
    _copy_fixture(project_directory)

    # When
    findings = _rest_framework_configured_findings(project_directory)

    # Then
    names = {name for _, _, name in findings}
    assert 'unreferenced_require_view' not in names
    assert 'imported_receiver' not in names
    assert 'QualifiedAdmin' not in names
    assert 'BareAdmin' not in names
    assert 'article_stats' not in names
    assert 'publish' not in names
    assert 'article_update' not in names


def test_require_put_uses_require_http_methods(project_directory: Path) -> None:
    # Having
    fixture_sources = {path.name: path.read_text() for path in FIXTURE_DIRECTORY.glob('*.py')}

    # Then
    assert 'require_PUT' not in ''.join(fixture_sources.values())
    assert "@require_http_methods(['PUT'])" in fixture_sources['views.py']


def test_import_forms_without_configuration(project_directory: Path) -> None:
    # Having
    _copy_fixture(project_directory)

    # When
    output = main(['project', '--no-color'])

    # Then
    _assert_no_parse_warning(output)
    findings = _findings(output)
    assert {
        ('project/import_forms.py', 'DC03', 'QualifiedModel'),
        ('project/import_forms.py', 'DC03', 'ImportedForm'),
        ('project/import_forms.py', 'DC03', 'QualifiedAdmin'),
        ('project/import_forms.py', 'DC03', 'BareAdmin'),
        ('project/import_forms.py', 'DC02', 'imported_receiver'),
    } <= findings
    assert ('project/import_forms.py', 'DC03', 'ImportedModel') not in findings


def test_import_forms_with_documented_configuration(project_directory: Path) -> None:
    # Having
    _copy_fixture(project_directory)

    # When
    findings = _configured_findings(project_directory)

    # Then
    assert not any(path == 'project/import_forms.py' for path, _, _ in findings)


def test_signal_forms_without_configuration(project_directory: Path) -> None:
    # Having
    _copy_fixture(project_directory)

    # When
    output = main(['project', '--no-color'])

    # Then
    _assert_no_parse_warning(output)
    findings = _findings(output)
    assert {
        ('project/signals.py', 'DC02', 'article_saved'),
        ('project/signals.py', 'DC02', 'unused_signal_handler'),
        ('project/import_forms.py', 'DC02', 'imported_receiver'),
    } <= findings
    assert ('project/signals.py', 'DC02', 'article_saved_direct') not in findings


def test_signal_forms_with_documented_configuration(project_directory: Path) -> None:
    # Having
    _copy_fixture(project_directory)

    # When
    findings = _configured_findings(project_directory)

    # Then
    signal_findings = [finding for finding in findings if finding[0] == 'project/signals.py']
    assert signal_findings == [('project/signals.py', 'DC02', 'unused_signal_handler')]


def test_django_rest_framework_without_configuration(project_directory: Path) -> None:
    # Having
    _copy_fixture(project_directory)

    # When
    output = main(['project', '--no-color'])

    # Then
    _assert_no_parse_warning(output)
    findings = _findings(output)
    assert {
        ('project/api.py', 'DC03', 'Meta'),
        ('project/api.py', 'DC06', 'serializer_class'),
        ('project/api.py', 'DC04', 'publish'),
        ('project/api.py', 'DC02', 'article_stats'),
        ('project/api.py', 'DC02', 'unused_api_helper'),
    } <= findings
    assert ('project/api.py', 'DC03', 'ArticleViewSet') not in findings
    assert ('project/api.py', 'DC03', 'ArticleSerializer') not in findings


def test_django_rest_framework_with_documented_configuration(project_directory: Path) -> None:
    # Having
    _copy_fixture(project_directory)

    # When
    findings = _rest_framework_configured_findings(project_directory)

    # Then
    api_findings = [finding for finding in findings if finding[0] == 'project/api.py']
    assert api_findings == [('project/api.py', 'DC02', 'unused_api_helper')]


def test_django_rest_framework_reported_with_pure_django_configuration(project_directory: Path) -> None:
    # Having
    _copy_fixture(project_directory)

    # When
    findings = _configured_findings(project_directory)

    # Then
    api_findings = {finding for finding in findings if finding[0] == 'project/api.py'}
    assert api_findings == {
        ('project/api.py', 'DC03', 'Meta'),
        ('project/api.py', 'DC06', 'model'),
        ('project/api.py', 'DC06', 'fields'),
        ('project/api.py', 'DC06', 'serializer_class'),
        ('project/api.py', 'DC04', 'publish'),
        ('project/api.py', 'DC04', 'retrieve'),
        ('project/api.py', 'DC04', 'destroy'),
        ('project/api.py', 'DC02', 'article_stats'),
        ('project/api.py', 'DC02', 'unused_api_helper'),
    }


def test_model_layer_false_positives_with_documented_configuration(project_directory: Path) -> None:
    # Having
    _copy_fixture(project_directory)

    # When
    findings = _configured_findings(project_directory)

    # Then
    assert not any(path == 'project/models.py' for path, _, _ in findings)
    assert not any(path == 'project/managers.py' and code != 'DC04' for path, code, _ in findings)
    assert not any(name == 'Meta' for path, _, name in findings if path != 'project/api.py')
    assert not any(name == 'display_name' for _, _, name in findings)
    assert not any(path.startswith('project/migrations/') for path, _, _ in findings)


def test_model_layer_false_positives_without_configuration(project_directory: Path) -> None:
    # Having
    _copy_fixture(project_directory)

    # When
    output = main(['project', '--no-color'])

    # Then
    _assert_no_parse_warning(output)
    findings = _findings(output)
    assert any(name == 'Meta' for _, _, name in findings)
    assert any(name == 'category' for _, _, name in findings)
    assert any(name == 'display_name' for _, _, name in findings)
    assert any(path.startswith('project/migrations/') for path, _, _ in findings)


def test_template_layer_false_positives_with_documented_configuration(project_directory: Path) -> None:
    # Having
    _copy_fixture(project_directory)

    # When
    findings = _configured_findings(project_directory)

    # Then
    names = {name for _, _, name in findings}
    assert 'greeting' not in names
    assert 'shout' not in names
    tag_findings = [finding for finding in findings if finding[0] == 'project/templatetags/blog_tags.py']
    assert tag_findings == [('project/templatetags/blog_tags.py', 'DC02', 'unused_tag')]


def test_view_and_template_layers_without_configuration(project_directory: Path) -> None:
    # Having
    _copy_fixture(project_directory)

    # When
    output = main(['project', '--no-color'])

    # Then
    _assert_no_parse_warning(output)
    findings = _findings(output)
    names = {name for _, _, name in findings}
    assert {'process_request', 'UnusedMiddleware', 'get', 'greeting', 'shout', 'unused_tag'} <= names
    assert ('project/views.py', 'DC03', 'UnusedView') in findings


def test_forms_false_positives_with_documented_configuration(project_directory: Path) -> None:
    # Having
    _copy_fixture(project_directory)

    # When
    findings = _configured_findings(project_directory)

    # Then
    names = {name for path, _, name in findings if path != 'project/api.py'}
    assert 'Meta' not in names
    assert 'model' not in names
    assert 'fields' not in names
    assert 'clean_title' not in names
    assert not any(path == 'project/forms.py' for path, _, _ in findings)


def test_admin_false_positives_with_documented_configuration(project_directory: Path) -> None:
    # Having
    _copy_fixture(project_directory)

    # When
    findings = _configured_findings(project_directory)

    # Then
    names = {name for _, _, name in findings}
    assert 'list_display' not in names
    assert 'search_fields' not in names
    assert 'list_filter' not in names
    assert 'actions' not in names
    assert 'mark_featured' not in names
    assert not any(path == 'project/admin.py' for path, _, _ in findings)


def test_forms_and_admin_without_configuration(project_directory: Path) -> None:
    # Having
    _copy_fixture(project_directory)

    # When
    output = main(['project', '--no-color'])

    # Then
    _assert_no_parse_warning(output)
    findings = _findings(output)
    names = {name for _, _, name in findings}
    assert {'Meta', 'model', 'fields', 'clean_title'} <= names
    assert {'form', 'list_display', 'search_fields', 'list_filter', 'actions', 'mark_featured'} <= names
    assert ('project/admin.py', 'DC03', 'UnusedAdmin') in findings
    assert ('project/forms.py', 'DC03', 'UnusedForm') in findings


def test_development_process_false_positives_with_documented_configuration(project_directory: Path) -> None:
    # Having
    _copy_fixture(project_directory)

    # When
    findings = _configured_findings(project_directory)

    # Then
    assert not any(path == 'project/apps.py' for path, _, _ in findings)
    assert not any(path == 'project/management/commands/import_data.py' for path, _, _ in findings)
    assert not any(name in {'Command', 'help', 'add_arguments', 'handle', 'article_saved'} for _, _, name in findings)
    assert not any(
        path == 'project/tests.py'
        and name in {'setUpTestData', '_pre_setup', '_post_teardown', '_fixture_setup', '_fixture_teardown'}
        for path, _, name in findings
    )
    assert ('project/signals.py', 'DC02', 'unused_signal_handler') in findings
    assert ('project/tests.py', 'DC04', 'unused_test_helper') in findings


def test_development_process_without_configuration(project_directory: Path) -> None:
    # Having
    _copy_fixture(project_directory)

    # When
    output = main(['project', '--no-color'])

    # Then
    _assert_no_parse_warning(output)
    findings = _findings(output)
    names = {name for _, _, name in findings}
    assert {'BlogConfig', 'default_auto_field', 'ready'} <= names
    assert {'Command', 'help', 'add_arguments', 'handle'} <= names
    assert 'article_saved' in names
    assert not {'setUpTestData', '_pre_setup', '_post_teardown', '_fixture_setup', '_fixture_teardown'} & names
