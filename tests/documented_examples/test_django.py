import re
import shutil

from pathlib import Path

from deadcode.cli import main, print_main

FIXTURE_DIRECTORY = Path(__file__).resolve().parents[1] / 'files' / 'django'

CONFIGURATION = """[tool.deadcode]
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
"""

COMMAND_LINE_OPTIONS = [
    '--ignore-names-if-decorated-with=@admin.*',
    '--ignore-names-if-decorated-with=@receiver',
    '--ignore-names-if-decorated-with=@register.*',
    '--ignore-names-if-decorated-with=@login_required',
    '--ignore-names-if-decorated-with=@permission_required',
    '--ignore-names-if-decorated-with=@require_http_methods',
    '--ignore-names-if-decorated-with=@require_POST',
    '--ignore-names-if-decorated-with=@method_decorator',
    '--ignore-bodies-if-inherits-from=models.Model',
    '--ignore-bodies-if-inherits-from=ModelAdmin',
    '--ignore-bodies-if-inherits-from=forms.Form',
    '--ignore-bodies-if-inherits-from=forms.ModelForm',
    '--ignore-bodies-if-inherits-from=View',
    '--ignore-bodies-if-inherits-from=BaseCommand',
    '--ignore-bodies-if-inherits-from=Migration',
    '--ignore-bodies-if-inherits-from=AppConfig',
    '--ignore-bodies-if-inherits-from=MiddlewareMixin',
    '--ignore-names-in-files=*/settings.py',
    '--ignore-names-in-files=*/urls.py',
    '--ignore-names-in-files=*/migrations/*',
    '--ignore-definitions=*Config',
    '--ignore-definitions=*Middleware',
    '--ignore-definitions=Command',
    '--ignore-names=setUpTestData',
    '--ignore-names=_pre_setup',
    '--ignore-names=_post_teardown',
    '--ignore-names=_fixture_setup',
    '--ignore-names=_fixture_teardown',
]

FINDING_PATTERN = re.compile(r'^(?P<path>.+):\d+:\d+: (?P<code>DC\d+) \w+ `(?P<name>[^`]+)` is never used$')

BASELINE_FINDINGS = {
    ('project/settings.py', 'DC01', 'SECRET_KEY'),
    ('project/settings.py', 'DC01', 'DEBUG'),
    ('project/settings.py', 'DC01', 'INSTALLED_APPS'),
    ('project/settings.py', 'DC01', 'MIDDLEWARE'),
    ('project/settings.py', 'DC01', 'TEMPLATES'),
    ('project/settings.py', 'DC01', 'DATABASES'),
    ('project/settings.py', 'DC01', 'ROOT_URLCONF'),
    ('project/settings.py', 'DC01', 'UNUSED_SETTING'),
    ('project/urls.py', 'DC01', 'app_name'),
    ('project/urls.py', 'DC01', 'urlpatterns'),
    ('project/urls.py', 'DC01', 'UNUSED_URL_NAME'),
    ('project/apps.py', 'DC03', 'BlogConfig'),
    ('project/apps.py', 'DC06', 'default_auto_field'),
    ('project/apps.py', 'DC04', 'ready'),
    ('project/management/commands/import_data.py', 'DC03', 'Command'),
    ('project/management/commands/import_data.py', 'DC06', 'help'),
    ('project/management/commands/import_data.py', 'DC04', 'add_arguments'),
    ('project/management/commands/import_data.py', 'DC04', 'handle'),
    ('project/management/commands/import_data.py', 'DC03', 'UnusedCommand'),
    ('project/management/commands/import_data.py', 'DC04', 'handle'),
    ('project/signals.py', 'DC02', 'article_saved'),
    ('project/signals.py', 'DC02', 'unused_signal_handler'),
    ('project/tests.py', 'DC04', 'setUpTestData'),
    ('project/tests.py', 'DC04', '_pre_setup'),
    ('project/tests.py', 'DC04', '_post_teardown'),
    ('project/tests.py', 'DC04', '_fixture_setup'),
    ('project/tests.py', 'DC04', '_fixture_teardown'),
    ('project/tests.py', 'DC04', 'unused_test_helper'),
    ('project/admin.py', 'DC03', 'ArticleAdmin'),
    ('project/admin.py', 'DC03', 'UnusedAdmin'),
    ('project/admin.py', 'DC04', 'mark_featured'),
    ('project/admin.py', 'DC06', 'actions'),
    ('project/admin.py', 'DC06', 'form'),
    ('project/admin.py', 'DC06', 'list_display'),
    ('project/admin.py', 'DC06', 'list_filter'),
    ('project/admin.py', 'DC06', 'search_fields'),
    ('project/forms.py', 'DC03', 'Meta'),
    ('project/forms.py', 'DC03', 'UnusedForm'),
    ('project/forms.py', 'DC04', 'clean_title'),
    ('project/forms.py', 'DC06', 'fields'),
    ('project/forms.py', 'DC06', 'model'),
    ('project/views.py', 'DC01', 'UNUSED_VIEW_SETTING'),
    ('project/views.py', 'DC02', 'unused_view'),
    ('project/views.py', 'DC03', 'UnusedView'),
    ('project/views.py', 'DC04', 'get'),
    ('project/middleware.py', 'DC03', 'SimpleMiddleware'),
    ('project/middleware.py', 'DC04', 'process_request'),
    ('project/templatetags/blog_tags.py', 'DC02', 'greeting'),
    ('project/templatetags/blog_tags.py', 'DC02', 'shout'),
    ('project/templatetags/blog_tags.py', 'DC02', 'unused_tag'),
    ('project/managers.py', 'DC04', 'unused_manager_method'),
    ('project/models.py', 'DC03', 'Meta'),
    ('project/models.py', 'DC03', 'UnusedModel'),
    ('project/models.py', 'DC06', 'category'),
    ('project/models.py', 'DC06', 'ordering'),
    ('project/models.py', 'DC06', 'verbose_name_plural'),
    ('project/models.py', 'DC08', 'display_name'),
    ('project/models.py', 'DC08', 'published_titles'),
    ('project/migrations/0001_initial.py', 'DC06', 'dependencies'),
    ('project/migrations/0001_initial.py', 'DC06', 'initial'),
    ('project/migrations/0001_initial.py', 'DC06', 'operations'),
}

CONFIGURED_FINDINGS = {
    ('project/admin.py', 'DC03', 'UnusedAdmin'),
    ('project/forms.py', 'DC03', 'UnusedForm'),
    ('project/views.py', 'DC01', 'UNUSED_VIEW_SETTING'),
    ('project/views.py', 'DC02', 'unused_view'),
    ('project/views.py', 'DC03', 'UnusedView'),
    ('project/templatetags/blog_tags.py', 'DC02', 'unused_tag'),
    ('project/models.py', 'DC03', 'UnusedModel'),
    ('project/managers.py', 'DC04', 'unused_manager_method'),
    ('project/management/commands/import_data.py', 'DC03', 'UnusedCommand'),
    ('project/signals.py', 'DC02', 'unused_signal_handler'),
    ('project/tests.py', 'DC04', 'unused_test_helper'),
}

MODEL_LAYER_FINDINGS = CONFIGURED_FINDINGS


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
    (project_directory / 'pyproject.toml').write_text(CONFIGURATION)

    # When
    output = main(['project', '--no-color'])

    # Then
    _assert_no_parse_warning(output)
    assert _findings(output) == CONFIGURED_FINDINGS
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


def test_model_layer_false_positives_with_documented_configuration(project_directory: Path) -> None:
    # Having
    _copy_fixture(project_directory)
    (project_directory / 'pyproject.toml').write_text(CONFIGURATION)

    # When
    output = main(['project', '--no-color'])

    # Then
    _assert_no_parse_warning(output)
    findings = _findings(output)
    assert findings == MODEL_LAYER_FINDINGS
    assert ('project/models.py', 'DC03', 'UnusedModel') in findings
    assert ('project/managers.py', 'DC04', 'unused_manager_method') in findings
    assert not any(path == 'project/models.py' and code == 'DC06' for path, code, _ in findings)
    assert not any(name == 'Meta' for _, _, name in findings)
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


def test_view_layer_false_positives_with_documented_configuration(project_directory: Path) -> None:
    # Having
    _copy_fixture(project_directory)
    (project_directory / 'pyproject.toml').write_text(CONFIGURATION)

    # When
    output = main(['project', '--no-color'])

    # Then
    _assert_no_parse_warning(output)
    findings = _findings(output)
    names = {name for _, _, name in findings}
    assert 'ArticleListView' not in names
    assert 'get' not in names
    assert 'process_request' not in names
    assert 'SimpleMiddleware' not in names
    assert ('project/views.py', 'DC03', 'UnusedView') in findings
    assert not any(
        code == 'DC04' and path in {'project/views.py', 'project/middleware.py'} for path, code, _ in findings
    )


def test_template_layer_false_positives_with_documented_configuration(project_directory: Path) -> None:
    # Having
    _copy_fixture(project_directory)
    (project_directory / 'pyproject.toml').write_text(CONFIGURATION)

    # When
    output = main(['project', '--no-color'])

    # Then
    _assert_no_parse_warning(output)
    findings = _findings(output)
    assert not any(name == 'greeting' for _, _, name in findings)
    assert not any(name == 'shout' for _, _, name in findings)
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
    assert {'SimpleMiddleware', 'process_request', 'get', 'greeting', 'shout', 'unused_tag'} <= names
    assert ('project/views.py', 'DC03', 'UnusedView') in findings


def test_forms_false_positives_with_documented_configuration(project_directory: Path) -> None:
    # Having
    _copy_fixture(project_directory)
    (project_directory / 'pyproject.toml').write_text(CONFIGURATION)

    # When
    output = main(['project', '--no-color'])

    # Then
    _assert_no_parse_warning(output)
    findings = _findings(output)
    names = {name for _, _, name in findings}
    assert 'Meta' not in names
    assert 'model' not in names
    assert 'fields' not in names
    assert 'clean_title' not in names
    assert 'ArticleForm' not in names
    assert ('project/forms.py', 'DC03', 'UnusedForm') in findings


def test_admin_false_positives_with_documented_configuration(project_directory: Path) -> None:
    # Having
    _copy_fixture(project_directory)
    (project_directory / 'pyproject.toml').write_text(CONFIGURATION)

    # When
    output = main(['project', '--no-color'])

    # Then
    _assert_no_parse_warning(output)
    findings = _findings(output)
    names = {name for _, _, name in findings}
    assert 'list_display' not in names
    assert 'search_fields' not in names
    assert 'list_filter' not in names
    assert 'actions' not in names
    assert 'mark_featured' not in names
    assert 'ArticleAdmin' not in names
    assert ('project/admin.py', 'DC03', 'UnusedAdmin') in findings


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
    (project_directory / 'pyproject.toml').write_text(CONFIGURATION)

    # When
    output = main(['project', '--no-color'])

    # Then
    _assert_no_parse_warning(output)
    findings = _findings(output)
    assert not any(path == 'project/apps.py' for path, _, _ in findings)
    assert not any(name in {'Command', 'help', 'add_arguments', 'handle', 'article_saved'} for _, _, name in findings)
    assert not any(
        path == 'project/tests.py'
        and name in {'setUpTestData', '_pre_setup', '_post_teardown', '_fixture_setup', '_fixture_teardown'}
        for path, _, name in findings
    )
    assert ('project/signals.py', 'DC02', 'unused_signal_handler') in findings
    assert ('project/management/commands/import_data.py', 'DC03', 'UnusedCommand') in findings
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
    assert {'setUpTestData', '_pre_setup', '_post_teardown', '_fixture_setup', '_fixture_teardown'} <= names
